# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basis packages
import os
import sys
import time

# Miscellaneous packages
import math

import importlib.resources
import numpy as np

import pandas as pd

# Own packages
from fus_driving_systems import control_driving_system as ds
from fus_driving_systems.tus_protocol import TUSProtocol

from fus_driving_systems.igt.utils import (ExecListener, VoltageFeedbackDispatcher,
                                           VoltageFeedbackTracker)
from fus_driving_systems.igt import transducer_xyz
from fus_driving_systems.igt import unifus
from fus_driving_systems.utils import get_config_value
from fus_driving_systems.calc_utils import validate_value
from fus_driving_systems.transducer_slot import get_max_pressure

# Access the logger
from fus_driving_systems.config.logging_config import (enable_crash_detection, get_logger,
                                                       get_session_log_dir,
                                                       get_session_log_filename,
                                                       is_crash_detection_enabled)
from fus_driving_systems.config.config import config_info as config


class IGT(ds.ControlDrivingSystem):
    """
    Class for an IGT ultrasound driving system, inheriting from the abstract class DrivingSystem.

    Attributes:
        connected (bool): Indicates whether the system is connected.
        gen: Generator object.
        sent_protocols (dict): Sent protocols, keyed by buffer number.
        fus: FUSSystem object for the IGT ultrasound driving system.
        listener: ExecListener object for event listening.
        n_channels (int): Number of channels.
    """

    def __init__(self, log_dir=None):
        """
        Initializes the IGT object.
        """

        super().__init__()

        if log_dir is None:
            log_dir = get_config_value(get_logger(), config, 'Logging', 'Temporary logging path',
                                       'C:\\Temp')

        # Crash detection (GitHub issue #126) is normally enabled once, centrally, by whichever
        # of initialize_logger()/sync_logger() a script/host application calls to set up
        # logging -- both are called before any driving-system object is constructed, in every
        # documented usage (including SonoRover One, which uses sync_logger()). This is a
        # safety net for the rare case neither has run yet: falls back to enabling it here,
        # using this instance's own log_dir. is_crash_detection_enabled() keeps this a no-op
        # otherwise -- see enable_crash_detection()'s own docstring for why calling it more
        # than once in a process is safe.
        if not is_crash_detection_enabled():
            enable_crash_detection(log_dir, log_dir)

        self.sent_protocols = {}
        self.fus = None
        self.listener = None
        self.n_channels = 0

    def is_protocol_sent(self, buffer_num):
        """
        Checks whether a protocol has been sent to the given hardware buffer.

        Parameters:
            buffer_num (int): Which hardware buffer to check (starting at 0).

        Returns:
            bool: True if a protocol has been sent to that buffer, False otherwise.
        """

        return buffer_num in self.sent_protocols

    def is_connected(self):
        """
        Checks whether the driving system is currently connected -- queries the underlying
        unifus SDK directly (self.fus.isConnected()) instead of the inherited _connected flag
        (GitHub issue #79): that flag is only ever updated at connect()/disconnect() time, so a
        connection lost in between (e.g. a cable break) would otherwise still read as connected
        until the next explicit connect()/disconnect() call. IGT never sets the inherited
        _connected flag at all -- it would just be a second, redundant place to keep in sync
        with this live check, for no benefit.

        Unconditionally False when self.fus doesn't exist yet (i.e. before the first connect()
        attempt) -- with no fus object, there is nothing to be connected to.

        Returns:
            bool: True if connected, False otherwise.
        """

        if self.fus is None:
            return False

        return self.fus.isConnected()

    def register_sent_protocol(self, buffer_num, protocols, pulse_train_seq, n_pulse_train_rep,
                               pulse_train_delay, phases=None,
                               total_alternating_duration_ms=None):
        """
        Records the sent protocol under its buffer number in the sent protocol list.
            buffer_num: which hardware buffer this protocol was sent to (see
                starting at 0)
            protocols (list(TUSProtocol)): The protocol(s) actually given to send_protocol() for
                this buffer. Stored three ways, for three different reasons: _build_
                intensity_lines() snapshots it into plain, human-readable strings for reporting
                (see that method's own docstring for why a live reference wouldn't do); _build_
                protocol_fingerprints() snapshots the fuller, machine-comparable state (timing/
                ramp plus every slot's own state) that actually determines the physical pulse
                (see its own docstring), used by _assert_not_reconfigured_since_send() to detect
                drift that intensity_lines wouldn't necessarily show; and the objects themselves
                are also kept verbatim under 'source_protocols' so a later execute_protocol()/
                wait_for_trigger() call can verify (see _assert_matches_sent()) that it was
                actually given these same objects back, not some other, unrelated protocol that
                merely happens to target the same buffer_num.
            pulse_train_seq: list of pulses representing a pulse train
            n_pulse_train_rep: number of executions of one pulse train
            pulse_train_delay: pulse train delay in miliseconds
            phases: phases in degrees to reach focal depth
            total_alternating_duration_ms (float or None): The value actually given to
                send_protocol() for this buffer -- read back by _assert_duration_matches_sent()
                to verify a later execute_protocol()/wait_for_trigger() call was given the same
                value when interleaving, rather than one silently going unused (GitHub #122/
                #125).
            total_protocol_duration_ms (float): Total duration of the protocol in milliseconds.
        """

        self.sent_protocols[buffer_num] = {}
        self.sent_protocols[buffer_num]['source_protocols'] = protocols
        self.sent_protocols[buffer_num]['intensity_lines'] = self._build_intensity_lines(
            protocols, buffer_num)
        self.sent_protocols[buffer_num]['protocol_fingerprints'] = (
            self._build_protocol_fingerprints(protocols))
        self.sent_protocols[buffer_num]['total_alternating_duration_ms'] = (
            total_alternating_duration_ms)
        self.sent_protocols[buffer_num]['pulse_train_seq'] = pulse_train_seq
        self.sent_protocols[buffer_num]['n_pulse_train_rep'] = n_pulse_train_rep
        self.sent_protocols[buffer_num]['pulse_train_delay'] = pulse_train_delay
        self.sent_protocols[buffer_num]['phases'] = phases
        # Set once wait_for_trigger() actually arms this buffer -- read back by
        # wait_for_trigger_result() (see its own docstring) to confirm it's being called for a
        # buffer that's genuinely armed, not merely sent. Always False again immediately after a
        # fresh send: whatever was armed before belonged to whatever was previously on this
        # buffer, not to what's here now.
        self.sent_protocols[buffer_num]['armed'] = False

        total_protocol_duration_ms = unifus.sequenceDurationMs(pulse_train_seq, n_pulse_train_rep,
                                                               pulse_train_delay)

        wait_time_ms = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                              'Wait time before responsive [ms]', 100))
        self.sent_protocols[buffer_num]['total_protocol_duration_ms'] = (
            total_protocol_duration_ms + wait_time_ms)

        # The dict this stores also holds a few internal bookkeeping fields (source_protocols,
        # intensity_lines, protocol_fingerprints, phases) purely for later drift-detection/
        # reporting use (see this method's own docstring) -- they're not printed here, since
        # dumping them raw would just repeat what's already logged above (the validated
        # parameters, the phases from compute_phases()) or show unhelpful object reprs. Only the
        # pulse-train schedule actually derived by this call -- not visible anywhere else in the
        # log -- is reported.
        get_logger().debug(
            f'Stored protocol in buffer {buffer_num}: {len(pulse_train_seq)} x Pulse, ' +
            f'{n_pulse_train_rep} repetition(s), {pulse_train_delay} ms delay between pulse ' +
            'trains, ' +
            f'{self.sent_protocols[buffer_num]["total_protocol_duration_ms"]:.2f} ms total ' +
            'protocol duration.')

    def connect(self, connect_info, log_dir=None, log_name=None, attempt=0):
        """
        Connects to the IGT ultrasound driving system.

        Does nothing (beyond logging) if already connected, rather than tearing down and
        recreating the native unifus.FUSSystem() and re-registering a listener on an already
        live connection -- a plausible source of instability (GitHub issue #126).

        On the first attempt, also forces a disconnect on a throwaway FUSSystem() before
        actually connecting, in case a previous (possibly crashed) session left the native
        driver holding a connection this fresh process has no handle to -- an experimental
        mitigation, see the inline comment below (GitHub issue #126). A short delay (config
        'General'/'Delay before reconnecting [s]') follows every disconnect-then-reconnect
        below, giving the driver a moment to settle instead of immediately hammering it with
        another connection attempt -- also #126: an unrelated cause under the driver/OS layer
        remains the leading hypothesis, but repeatedly retrying without any pause is, on its
        own, a plausible way for our own code to make an already-fragile driver worse.

        Parameters:
            connect_info (str): Path with IGT driving system-specific configuration file.

        Returns:
            bool: True once connected (whether newly connected or already connected).
            Unrecoverable errors still exit the program (see GitHub issue #61 -- returning
            False instead is a separate, later change).
        """

        # Only checked on the initial, externally-invoked call (attempt == 0) -- an internal
        # retry recursion (attempt > 0) is already mid-reconnect and has its own explicit
        # isConnected() check further below; re-checking here too would consume that same
        # live status early and short-circuit the retry with a stale verdict.
        if attempt == 0 and self.is_connected():
            get_logger().info('Already connected, skipping reconnection.')
            return True

        get_logger().info('Connecting...')

        reconnect_delay_s = float(get_config_value(get_logger(), config, 'General',
                                                   'Delay before reconnecting [s]', 2))

        if attempt == 0:
            # Experimental mitigation for the non-deterministic kernel-death crashes
            # reported in GitHub issue #126. is_connected() (checked above and further
            # below) only reflects state tracked by *this* process/instance -- a fresh
            # process (e.g. a new Spyder console the next morning) always starts
            # disconnected, so it can never reveal whether a previous, possibly crashed
            # session left the native driver holding a connection open. Forcing a
            # disconnect on a throwaway
            # FUSSystem() here gives the driver a chance to release that stale state
            # before the real attempt below. Unverified whether this actually reduces
            # kernel deaths -- logged explicitly so frequency can be compared over time.
            try:
                get_logger().debug('Forcing a disconnect on a fresh FUSSystem before ' +
                                   'connecting, in case a previous session left a stale ' +
                                   'connection (#126).')
                stale_fus = unifus.FUSSystem()
                stale_fus.clearListeners()
                stale_fus.disconnect()
                time.sleep(reconnect_delay_s)
            except Exception as e:
                get_logger().debug('Pre-connect defensive disconnect raised (expected if ' +
                                   f'there was nothing to clean up): {e}')

        if log_dir is None:
            log_dir = get_config_value(get_logger(), config, 'Logging', 'Temporary logging path',
                                       'C:\\Temp')

        # See the matching comment in __init__: prefer the shared, timestamped session folder
        # (if initialize_logger() set one up) for the native IGT log too, so it ends up
        # alongside the FDS log and the faulthandler log instead of loose in log_dir.
        session_log_dir = get_session_log_dir()
        if session_log_dir is not None:
            log_dir = session_log_dir

        if log_name is None:
            # Prefer the FDS log's own filename (e.g. "standalone_plain"), so the native IGT log
            # is named consistently with it by default -- callers no longer need to pass the
            # same filename twice. Falls back to the config default only when
            # initialize_logger() hasn't run in this process (e.g. a host application using
            # sync_logger() instead, which doesn't track a session filename).
            log_name = get_session_log_filename()
            if log_name is None:
                log_name = get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                            'Default log filename', 'standalone_igt')

        # When no connection, it is assumed that all sent protocols aren't available (anymore)
        self.sent_protocols = {}
        max_attempts = int(get_config_value(get_logger(), config, 'General',
                                            'Maximum reconnection attempts', 5))

        try:
            # Establish connection with driving system
            get_logger().debug('Before unifus.FUSSystem....')
            self.fus = unifus.FUSSystem()
            get_logger().debug('After unifus.FUSSystem....')
        except Exception as e:
            message = f'Error initializing FUSSystem: {e}'
            get_logger().critical(message)
            sys.exit(message)

        try:
            # A prefix so the native IGT log sorts and reads alongside this package's
            # own log_info_*/log_debug_*/log_measurements_* files in the same session
            # folder, all starting with the same recognizable "log_..." pattern.
            native_log_prefix = get_config_value(get_logger(), config,
                                                 'Equipment.Manufacturer.IGT',
                                                 'Native IGT log filename prefix', 'log_igt_')
            unifus.setLogPath(log_dir, native_log_prefix + log_name)
            unifus.setLogLevel(unifus.LogLevel.Debug)

            get_logger().debug('After setting logging....')
        except Exception as e:
            message = f"Error setting up logging: {e}"
            get_logger().error(message)

        try:
            # Update the name of your configuration file
            igt_config_path = str(
                importlib.resources.files('fus_driving_systems').joinpath(connect_info))
            get_logger().debug(f'igt_config_path: {igt_config_path} found....')
            self.fus.loadConfig(igt_config_path)
            get_logger().debug('After loadConfig....')
        except Exception as e:
            message = f"Error loading configuration: {e}"
            get_logger().critical(message)
            sys.exit(message)

        try:
            # Create and register an event listener
            self.listener = ExecListener()
            self.fus.registerListener(self.listener)
            get_logger().debug('After listener....')

            self.fus.connect()
            self.listener.wait_connection()
            get_logger().debug('After wait_connection()....')
        except Exception as e:
            get_logger().error(f"Error during connection or listener registration: {e}")

            if attempt < max_attempts:
                get_logger().warning('Try to disconnect and reconnect...')
                self.disconnect()
                time.sleep(reconnect_delay_s)
                return self.connect(connect_info, log_dir, log_name, attempt=attempt+1)

            message = f'Maximum amount of {max_attempts} for reconnecting is reached. Exit.'
            get_logger().critical(message)
            sys.exit(message)

        try:
            if self.is_connected():
                self.gen = self.fus.gen()
                self.n_channels = self.gen.getParam(unifus.GenParam.ChannelCount)
                get_logger().info("Driving system is connected. Generator: %s channels",
                                  self.n_channels)
                return True

            get_logger().warning("Error: connection failed.")

            if attempt < max_attempts:
                get_logger().warning('Try to disconnect and reconnect...')
                self.disconnect()
                time.sleep(reconnect_delay_s)
                return self.connect(connect_info, log_dir, log_name, attempt=attempt+1)

            message = (f'Maximum amount of {max_attempts} for reconnecting is reached. ' +
                       'Exit.')
            get_logger().critical(message)
            sys.exit(message)

        except Exception as e:
            message = f"Error after connection check: {e}"
            get_logger().critical(message)
            sys.exit(message)

    def validate_protocol(self, protocol):
        """
        Validates if the protocol is within the expected ranges.

        Parameters:
            protocol(Object): a TUSProtocol instance containing, amongst other things:
                the timing/power/focus parameters (focus, pulse duration, pulse rep. interval
                and etcetera) and the equipment used (driving system and transducer)

        Returns:
            List: List of error messages.
        """

        error_messages = super().validate_protocol(protocol)

        min_pulse_dur = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                               'Min. pulse duration [ms]', 0.001))
        if protocol.pulse_dur < min_pulse_dur:  # [ms]:
            error_messages.append('Pulse duration is not allowed to be smaller than 1 us.')

        min_pulse_rep_int = float(get_config_value(
            get_logger(), config, 'Equipment.Manufacturer.IGT',
            'Min. pulse rep. interval [ms]', 0.170))
        if protocol.pulse_rep_int < min_pulse_rep_int:  # [ms]
            error_messages.append('Pulse repetition interval is not allowed to be smaller than' +
                                  ' 170 us.')

        min_time_between_ramps = float(
            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                             'Min. time in between ramping up and down [ms]', 0.070))

        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                     'Rectangular - no ramping')
        if protocol.pulse_ramp_dur > 0 and (protocol.pulse_ramp_shape != rect_ramp):
            if protocol.pulse_ramp_dur > protocol.pulse_dur/2 - min_time_between_ramps/2:
                error_messages.append('When applying ramping, there needs to be at least ' +
                                      '70 us between ramping up and down')
        for i, slot in enumerate(protocol.slots):
            if slot.ampl is None:
                error_messages.append(
                    f"Intensity parameter may be set incorrectly for transducer slot {i} " +
                    f"(counting from 0, i.e. protocol.slots[{i}]; {slot.transducer.serial}). " +
                    "Amplitude is None.")

        n_pulses = protocol.pulse_train_dur/protocol.pulse_rep_int
        max_n_pulses = int(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                            'Max. pulses in pulse train', 64))
        if n_pulses > max_n_pulses:
            error_messages.append(
                "The maximum amount of pulses within a pulse train is " +
                f"{max_n_pulses}. Currently, the amount is {n_pulses}. If you need more " +
                "pulses over a longer total duration, set pulse_train_dur equal to " +
                "pulse_rep_int (one pulse per train) and use pulse_train_rep_int/" +
                "pulse_train_rep_dur to repeat the train instead -- physically equivalent, " +
                "since each pulse already carries its own pulse_rep_int - pulse_dur trailing " +
                "gap, but not subject to this per-train pulse count limit.")

        return error_messages

    def _assert_ready_to_send(self, protocol):
        """
        Authoritative gate, run once per protocol right before it's actually used: at least one
        transducer slot must have been added (see TUSProtocol.add_slot()), and the combined
        elements across all of its slots must exactly match this driving system's available
        channels.

        add_slot() itself only fails fast on exceeding available_ch (see
        TUSProtocol._validate_channel_count()) -- it can't require an exact match, since a
        driving system with more than one slot is legitimately "not done yet" after just the
        first add_slot() call. This is the one place that must see the final, complete picture.

        Parameters:
            protocol (TUSProtocol): The protocol to check.
        """

        if not protocol.slots:
            message = ('No transducer slot configured on this protocol -- call ' +
                       'protocol.add_slot(...) at least once before sending it.')
            get_logger().critical(message)
            sys.exit(message)

        total_elements = sum(slot.transducer.elements for slot in protocol.slots)
        if total_elements != protocol.driving_sys.available_ch:
            message = (f'Number of available channels ({protocol.driving_sys.available_ch}) ' +
                       f'does not match the combined elements of the {len(protocol.slots)} ' +
                       f'transducer slot(s) ({total_elements}).')
            get_logger().critical(message)
            sys.exit(message)

    def _assert_duration_given_when_interleaving(self, protocols,
                                                 total_alternating_duration_ms):
        """
        total_alternating_duration_ms has no sensible default when interleaving -- unlike a
        single protocol (which gets its own repetition count from its own pulse_train_rep_dur/
        pulse_train_rep_int), the alternating group as a whole has no such value to fall back to,
        and silently treating a missing/zero duration as "0 repetitions" would be a confusing
        no-op rather than a clear error.

        Parameters:
            protocols (list(TUSProtocol)): The protocols about to be sent/waited on/executed.
            total_alternating_duration_ms (float or None): The value the caller actually gave.
        """

        if len(protocols) > 1 and (total_alternating_duration_ms is None or
                                   total_alternating_duration_ms <= 0):
            message = ('total_alternating_duration_ms is required (and must be greater than 0) ' +
                       'when interleaving more than one protocol.')
            get_logger().critical(message)
            sys.exit(message)

    def _assert_valid_buffer_num(self, driving_sys, buffer_num):
        """
        Exits with a clear message unless buffer_num is a valid buffer for driving_sys.

        Parameters:
            driving_sys (DrivingSystem): The driving system buffer_num is being validated
                against (protocols[0].driving_sys -- every protocol in a group already targets
                the same driving system by construction).
            buffer_num (int): Which hardware buffer to validate.
        """

        validate_value(buffer_num, 'Buffer number (buffer_num)', True, True, False, False)

        if buffer_num >= driving_sys.max_buffers:
            message = (f'Buffer number {buffer_num} is not valid for driving system ' +
                       f'{driving_sys.serial} -- it has {driving_sys.max_buffers} buffer(s), ' +
                       f'so buffer_num must be between 0 and {driving_sys.max_buffers - 1}.')
            get_logger().critical(message)
            sys.exit(message)

    def _assert_matches_sent(self, protocols, buffer_num):
        """
        Exits with a clear message unless `protocols` are (by identity, via the default list/
        object equality Python already gives us) the exact objects send_protocol() was last
        called with for this buffer.

        is_protocol_sent(buffer_num) alone only proves *something* was sent to this buffer, not
        that these specific objects are it -- without this additional check, execute_protocol()/
        wait_for_trigger() would happily compute exec_flags/pulse_dur thresholds/trigger config
        from a protocol that has nothing to do with what's actually on the buffer (the physical
        pulse itself is safe either way, since it was already baked in at send time and these
        methods never rebuild it -- but everything they *do* still derive from their own
        protocols argument would silently be wrong).

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) this call was actually given.
            buffer_num (int): Which hardware buffer to check against (starting at 0)
                -- caller must already have confirmed is_protocol_sent(buffer_num) is True.
        """

        sent = self.sent_protocols.get(buffer_num, {}).get('source_protocols', protocols)
        if protocols != sent:
            message = ('The protocol(s) given here are not the ones last sent to buffer ' +
                       f'{buffer_num} -- call send_protocol() again with these protocol(s) ' +
                       'first.')
            get_logger().critical(message)
            sys.exit(message)

    def _assert_not_reconfigured_since_send(self, protocols, buffer_num):
        """
        Exits with a clear message if any protocol (its timing/ramping) or any of its slots has
        been reconfigured since actually being sent to this buffer (e.g. protocol.
        configure_timing()/slot.configure()/slot.update_transducer() called again, or slot.
        oper_freq/dephasing_degree set directly, after send_protocol(), without resending).

        _assert_matches_sent() only checks that these are the *same objects* that were sent --
        it does not, and cannot, catch the same objects having since been reconfigured in place.
        Compares against _build_protocol_fingerprints() rather than the human-readable
        _build_intensity_lines() specifically because the latter only covers chosen_focus/
        chosen_power on each slot -- a change to timing/ramping, oper_freq/dephasing_degree, or
        a transducer swap that happens to derive the same chosen focus/power values, wouldn't
        necessarily show up there, but does affect what send_protocol() actually built.

        Without this check, the driving system would keep firing whatever was baked in at send
        time while a researcher who just reconfigured something reasonably believes their new
        value is what's about to run -- a real safety gap (e.g. a lower configured pressure, or
        a shorter configured pulse duration, silently firing at the old, higher/longer one), not
        merely a cosmetic logging one, and not something a log message alone reliably prevents.

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) this call was actually given.
            buffer_num (int): Which hardware buffer to check against (starting at 0)
                -- caller must already have confirmed is_protocol_sent(buffer_num) is True.
        """

        current_fingerprints = self._build_protocol_fingerprints(protocols)
        sent_fingerprints = self.sent_protocols.get(buffer_num, {}).get(
            'protocol_fingerprints', current_fingerprints)
        if current_fingerprints != sent_fingerprints:
            message = (
                f'Buffer {buffer_num} was reconfigured after being sent -- the protocol or one ' +
                'or more of its slots no longer match what was actually sent to the driving ' +
                'system. Call send_protocol() again before proceeding, so it fires what you ' +
                'now expect instead of the stale, previously sent configuration.')
            get_logger().critical(message)
            sys.exit(message)

    def _assert_duration_matches_sent(self, protocols, buffer_num, total_alternating_duration_ms):
        """
        Exits with a clear message if total_alternating_duration_ms doesn't match what this
        buffer was actually sent with, when interleaving more than one protocol.

        Without this, a caller passing a different duration here than they used at
        send_protocol() would have it silently discarded rather than honored: execute_protocol()/
        wait_for_trigger() never use their own total_alternating_duration_ms argument for
        anything physical themselves -- it's only ever used (indirectly) via what's already
        stored in sent_protocols. This check is what makes it safe for their own
        reconnect-and-resend path to simply pass this call's value straight through: a mismatch
        would already have exited here, before that path is ever reached, so there's nothing
        left for it to reconcile.

        Only checked when interleaving: a single protocol computes its own repetition count from
        its own pulse_train_rep_dur/pulse_train_rep_int, so total_alternating_duration_ms is
        genuinely unused (and safe to leave at its default) there -- see
        _assert_duration_given_when_interleaving()'s identical scoping.

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) this call was actually given.
            buffer_num (int): Which hardware buffer to check against (starting at 0)
                -- caller must already have confirmed is_protocol_sent(buffer_num) is True.
            total_alternating_duration_ms (float or None): The value this call was actually
                given.
        """

        if len(protocols) > 1:
            sent_duration = self.sent_protocols.get(buffer_num, {}).get(
                'total_alternating_duration_ms', total_alternating_duration_ms)
            if total_alternating_duration_ms != sent_duration:
                message = (
                    'total_alternating_duration_ms given here ' +
                    f'({total_alternating_duration_ms}) does not match what buffer ' +
                    f'{buffer_num} was actually sent with ({sent_duration}). Call ' +
                    'send_protocol() again with this new duration first, or pass the ' +
                    'original value here.')
                get_logger().critical(message)
                sys.exit(message)

    def _assert_ready_to_run(self, protocols, buffer_num, total_alternating_duration_ms, caller):
        """
        Authoritative gate, run once right before execute_protocol()/wait_for_trigger() actually
        does anything: this buffer must have something sent to it, the protocol(s) given here
        must be (by identity) the ones actually sent, everything that determines the physical
        pulse must still match that snapshot, and (when interleaving) the duration given here
        must match what was actually sent too -- see is_protocol_sent()/_assert_matches_sent()/
        _assert_not_reconfigured_since_send()/_assert_duration_matches_sent() for why each of
        these four is independently necessary. Mirrors _assert_ready_to_send()'s role for
        send_protocol().

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) this call was actually given.
            buffer_num (int): Which hardware buffer to check against (starting at 0).
            total_alternating_duration_ms (float or None): The value this call was actually
                given.
            caller (str): Name of the calling method, purely to name it in the "nothing sent"
                message below (e.g. "execute_protocol").
        """

        if not self.is_protocol_sent(buffer_num):
            message = (f'No protocol has been sent to buffer {buffer_num} yet -- call ' +
                       f'send_protocol() before {caller}().')
            get_logger().critical(message)
            sys.exit(message)

        self._assert_matches_sent(protocols, buffer_num)
        self._assert_not_reconfigured_since_send(protocols, buffer_num)
        self._assert_duration_matches_sent(protocols, buffer_num, total_alternating_duration_ms)

    def _build_intensity_lines(self, protocols, buffer_num):
        """
        One line per transducer slot across the given protocol(s), naming its chosen focus/power
        (TransducerSlot.intensity_summary()) -- computed once, at send_protocol() time, and
        stored verbatim in sent_protocols (see register_sent_protocol()) rather than re-read
        live from the TUSProtocol/TransducerSlot objects whenever a confirmation is logged later.
        This matters because those objects are ordinary mutable Python objects: if a caller
        reconfigures a slot (e.g. slot.configure(...)) after send_protocol() but before
        execute_protocol()/wait_for_trigger(), without resending, the live values would already
        have moved on from what _define_pulse_group() actually baked into the driving system's
        buffer at send time -- a confirmation log built from the live objects at that later
        point would then describe the *new*, not-yet-sent configuration, misrepresenting what's
        actually physically about to fire (or already fired).

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) just given to send_protocol().
            buffer_num (int): Which hardware buffer these protocols were sent to.

        Returns:
            list(str): One formatted line per transducer slot.
        """

        return [f'  Buffer {buffer_num}, slot {i}: {slot.intensity_summary()}'
                for protocol in protocols for i, slot in enumerate(protocol.slots)]

    def _build_slot_fingerprints(self, protocols):
        """
        A tuple per transducer slot capturing everything _define_pulse_group() actually reads to
        build the physical pulse -- transducer serial, oper_freq, dephasing_degree, and the
        already-derived focus_wrt_mid_bowl/ampl actually used for phases/amplitudes -- regardless
        of which chosen_focus/chosen_power option a researcher used to arrive at them. Used
        purely to detect reconfiguration since send_protocol() (see
        _assert_not_reconfigured_since_send()), not for display -- _build_intensity_lines()
        covers only the chosen-option subset of this same state, formatted for a researcher to
        read; a change to oper_freq/dephasing_degree, or a transducer swap that happens to derive
        the same chosen focus/power values, would not necessarily show up there, but does here.

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) to fingerprint.

        Returns:
            list(tuple): One tuple per transducer slot.
        """

        return [
            (i, slot.transducer.serial, slot.oper_freq,
             tuple(slot.dephasing_degree) if slot.dephasing_degree is not None else None,
             slot.focus_wrt_mid_bowl,
             tuple(slot.ampl) if slot.ampl is not None else None)
            for protocol in protocols for i, slot in enumerate(protocol.slots)]

    def _build_protocol_fingerprints(self, protocols):
        """
        A tuple per protocol capturing everything that actually gets baked into the driving
        system's buffer at send_protocol() time: the timing/ramp fields _define_pulse_train()/
        _apply_ramping() read (pulse_dur, pulse_rep_int, pulse_train_dur, pulse_train_rep_int,
        pulse_train_rep_dur, pulse_ramp_shape, pulse_ramp_dur), plus each of its slots' own
        fingerprint (see _build_slot_fingerprints()). None of these timing/ramp values are
        re-read from the live protocol objects by execute_protocol()/wait_for_trigger() for the
        actual hardware calls -- only n_pulse_train_rep/pulse_train_delay/pulse_train_seq, which
        were already computed from them once, at send time, and stored in sent_protocols -- so a
        change to any of them after send_protocol(), without resending, must be caught the same
        way a slot-level drift is (see _assert_not_reconfigured_since_send()).

        Reads the timing fields via getattr(..., None) rather than direct attribute access --
        unlike a slot's own fields (always present on a real TransducerSlot), a real TUSProtocol
        always has these too, so this changes nothing for actual production use; it only avoids
        forcing every unrelated test double throughout this file to grow five new attributes it
        has no reason to otherwise need.

        Parameters:
            protocols (list(TUSProtocol)): The protocol(s) to fingerprint.

        Returns:
            list(tuple): One tuple per protocol.
        """

        timing_fields = ('pulse_dur', 'pulse_rep_int', 'pulse_train_dur', 'pulse_train_rep_int',
                         'pulse_train_rep_dur', 'pulse_ramp_shape', 'pulse_ramp_dur')
        return [
            tuple(getattr(protocol, field, None) for field in timing_fields) +
            (tuple(self._build_slot_fingerprints([protocol])),)
            for protocol in protocols]

    def _log_intensity_summary(self, buffer_num, header):
        """
        Logs `header` at INFO level, followed by the intensity lines register_sent_protocol()
        captured for this buffer at send_protocol() time -- shared by the "about to execute/wait
        for trigger" and "confirmed executed" log points (GitHub #125/#122), so a researcher
        knows what they're waiting for before a (possibly blocking) wait, and gets the same
        information again once execution is confirmed successful. Always reflects what was
        actually sent (see _build_intensity_lines()'s own docstring for why that's not the same
        as re-reading the TUSProtocol/TransducerSlot objects live at this later point.

        Parameters:
            buffer_num (int): Which hardware buffer to report on (starting at 0).
            header (str): One-line description of the moment this is being logged at.
        """

        lines = self.sent_protocols.get(buffer_num, {}).get('intensity_lines', [])
        get_logger().info(header + '\n' + '\n'.join(lines))

    def send_protocol(self, protocols, total_alternating_duration_ms=None, buffer_num=0):
        """
        Validates and sends one or more ultrasound protocols to the IGT ultrasound driving
        system. More than one protocol means they are interleaved: sent as one alternating group,
        fired in the order given, repeating for total_alternating_duration_ms. Ramping
        (pulse_ramp_shape/pulse_ramp_dur) is applied once for the whole interleaved group, taken
        from only the first protocol given -- it's a generator-wide setting, not something each
        interleaved protocol can configure independently, so every protocol given must declare
        the same ramping (enforced below) even though only the first one's value is actually
        used.

        buffer_num applies to the whole group: one protocol, or several interleaved, is always
        sent to exactly one hardware buffer. Defaults to 0 -- the only valid value for a driving
        system with no real multi-buffer concept (max_buffers == 1).

        When interleaving, each protocol contributes exactly one pulse per round of the
        alternating group -- not a repeated pulse train of its own. pulse_dur/pulse_rep_int
        still apply per protocol (pulse_rep_int decides how much of the shared round this
        protocol's own pulse occupies, via its trailing delay), but pulse_train_dur/
        pulse_train_rep_int/pulse_train_rep_dur do not: there is currently no way for one
        interleaved protocol to internally repeat its own pulse a number of times before handing
        off to the next one. Only relevant with more than one protocol -- a single protocol still
        gets its full pulse train via _define_pulse_train().

        Parameters:
            protocols (TUSProtocol or list(TUSProtocol)): One protocol, or a list of protocols to
                interleave. Each protocol is a TUSProtocol instance containing, amongst other
                things, the timing/power/focus parameters (focus, pulse duration, pulse rep.
                interval and etcetera) and the equipment used (driving system and transducer
                slot(s)).
            total_alternating_duration_ms (float): Required (must be > 0) when interleaving more
                than one protocol -- total duration [ms] the alternating group repeats for.
                Unused, and safe to leave at its default, for a single protocol.
            buffer_num (int): Which of the driving system's hardware buffers to send to, starting
                at 0. Must be within [0, driving_sys.max_buffers].
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)
        self._assert_valid_buffer_num(protocols[0].driving_sys, buffer_num)

        for protocol in protocols:
            self._assert_ready_to_send(protocol)

        # Only protocols[0].pulse_ramp_shape/pulse_ramp_dur are ever actually applied to the
        # generator below (ramping is a whole-group setting, not something each interleaved
        # protocol configures independently -- see this method's own docstring) -- but a caller
        # giving different ramp settings across the group almost certainly means they expected
        # every protocol's own ramping to take effect, so reject it explicitly instead of
        # silently going with whichever one happens to be first.
        if len(protocols) > 1 and any(
                (protocol.pulse_ramp_shape, protocol.pulse_ramp_dur)
                != (protocols[0].pulse_ramp_shape, protocols[0].pulse_ramp_dur)
                for protocol in protocols[1:]):
            ramp_settings = [(protocol.pulse_ramp_shape, protocol.pulse_ramp_dur)
                             for protocol in protocols]
            message = ('All protocols given to interleave must use the same ramping -- got ' +
                       f'{ramp_settings}.')
            get_logger().critical(message)
            sys.exit(message)

        for protocol in protocols:
            tran_serials = ', '.join(slot.transducer.serial for slot in protocol.slots)
            get_logger().info(
                f'Validating protocol for buffer {buffer_num} '
                f'({len(protocol.slots)} slot(s): {tran_serials})...')
            get_logger().debug(
                'Protocol with the following parameters is validated before sending: \n ' +
                '%s', protocol)

            self._validate_or_exit(protocol)

        get_logger().info('Sending protocol...')
        if self.is_connected():

            pulses = [self._define_pulse_group(protocol) for protocol in protocols]
            protocol0 = protocols[0]

            if len(protocols) == 1:
                pulse, phases = pulses[0]

                # define pulse train
                pulse_train_seq, pulse_train_delay = self._define_pulse_train(protocol0, pulse)

                # Define pulse train repetition
                # number of executions of one pulse train
                n_pulse_train_rep = math.floor(
                    protocol0.pulse_train_rep_dur / protocol0.pulse_train_rep_int)
            else:
                # One pulse per protocol, not a repeated pulse train per protocol -- unlike the
                # N=1 branch above (_define_pulse_train()), each interleaved protocol's own
                # pulse_train_dur/pulse_train_rep_int/pulse_train_rep_dur have no effect here
                # (see this method's own docstring). A researcher may well have set these via
                # configure_timing() expecting them to matter (e.g. reusing a protocol that
                # already worked standalone), so this is a warning, not a debug line.
                # Theoretically possible to support, but not yet designed: would need a real
                # decision on what "interleaved pulse trains" (as opposed to interleaved single
                # pulses) should actually mean here.
                get_logger().warning(
                    f'Interleaving {len(protocols)} protocols -- each contributes one pulse '
                    'per round, not a repeated pulse train of its own. pulse_train_dur/'
                    'pulse_train_rep_int/pulse_train_rep_dur are ignored for every protocol in '
                    'this group; only pulse_dur/pulse_rep_int apply.')
                pulse_train_seq = [pulse for pulse, _ in pulses]
                phases = [protocol_phases for _, protocol_phases in pulses]
                pulse_train_delay = 0

                # One round of the alternating group takes as long as every protocol's own
                # pulse_rep_int summed -- each protocol's pulse occupies that whole time slot
                # (pulse_dur active, then its own trailing delay), not pulse_train_dur (which
                # would describe a repeated train this pulse never actually fires here).
                total_pulse_rep_int_ms = sum(protocol.pulse_rep_int for protocol in protocols)
                n_pulse_train_rep = math.floor(
                    total_alternating_duration_ms / total_pulse_rep_int_ms)

            # Apply ramping -- read from protocol0 only. Ramping is set once on the generator as
            # a whole (rising/falling PulseRamp), not per pulse train, so it's an all-or-nothing
            # property of the entire interleaved group, not something each interleaved protocol
            # can configure independently: protocol0's pulse_ramp_shape/pulse_ramp_dur decide it
            # for every protocol in this send_protocol() call (every other protocol is already
            # guaranteed to declare the same values, enforced above).
            rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                         'Rectangular - no ramping')
            if protocol0.pulse_ramp_shape != rect_ramp:
                self._apply_ramping(protocol0)
            else:
                self.gen.setPulseModulation([], 0, [], 0)  # disable any modulation
                self.gen.setPulseRamp(unifus.PulseRamp.Rising, 0)
                self.gen.setPulseRamp(unifus.PulseRamp.Falling, 0)

            # (optional) restore disabled channels
            self.gen.enableAllChannels()

            # (optional) disable HeartBeat security
            self.gen.setParam(unifus.GenParam.HeartBeatTimeout, 0)

            # (optional) only for generator with a transducer multiplexer
            # gen.setParam (unifus.GenParam.MultiplexerValue, 3);

            # Upload the protocol
            self.gen.sendSequence(buffer_num, pulse_train_seq)

            self.register_sent_protocol(buffer_num, protocols, pulse_train_seq,
                                        n_pulse_train_rep, pulse_train_delay, phases,
                                        total_alternating_duration_ms)

        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocols[0].driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms, buffer_num)

    def _define_pulse_group(self, protocol):
        """
        Defines the combined pulse for every transducer slot of one protocol, concatenating each
        slot's own fully-expanded (per-element) amplitude/frequency arrays -- uniformly, whether
        there's 1 slot or several. N is never hardcoded -- however many slots this protocol
        actually has is how many this loops over.

        Parameters:
            protocol (TUSProtocol): The protocol object containing ultrasound parameters.

        Returns:
            tuple: (unifus.Pulse, list) -- the defined pulse and its phases.
        """

        pulse = unifus.Pulse(self.n_channels, 1, 1)  # n phases, n frequencies, n amplitudes

        # duration in ms, delay in ms
        pulse.setDuration(protocol.pulse_dur,
                          round(protocol.pulse_rep_int - protocol.pulse_dur, 1))

        slots = protocol.slots

        # frequencies have to be set first before phases can be computed
        phases = []
        freqs = []
        ampls = []
        for slot in slots:
            if slot.ampl is None:
                message = "Power parameter may be set incorrectly. Amplitude is None."
                get_logger().critical(message)
                sys.exit(message)

            # Every slot's own value is expanded to its own element count before concatenating
            # -- applied uniformly, whether this protocol has 1 slot or several.
            tran_freq = [int(slot.oper_freq * 1e3)] * slot.transducer.elements
            if len(slot.ampl) == 1:
                ampls = ampls + slot.ampl * slot.transducer.elements
            else:
                ampls = ampls + slot.ampl

            freqs = freqs + tran_freq

            pulse.setFrequencies(tran_freq)
            if slot.dephasing_degree is not None and (
                    len(slot.dephasing_degree) == slot.transducer.elements):
                get_logger().info('Phases are overridden by phases set at dephasing_degree: ' +
                                  f'{slot.dephasing_degree}')
                phases = phases + slot.dephasing_degree
            else:
                computed_phases = self._set_phases(pulse, slot.focus_wrt_mid_bowl,
                                                   slot.transducer.steer_info,
                                                   slot.dephasing_degree,
                                                   slot.focus_offset_x, slot.focus_offset_y)
                phases = phases + computed_phases

        # set phase offset for all channels (angle in [0,360] degrees)
        pulse.setPhases(phases)

        # set frequency for all channels, in Hz
        pulse.setFrequencies(freqs)

        # set amplitude for all channels in percent (of max amplitude)
        pulse.setAmplitudes(ampls)

        return pulse, phases

    def _compute_exec_flags(self, protocols):
        """
        Computes the base unifus.ExecFlag for executing or arming a previously sent protocol --
        shared by wait_for_trigger() and execute_protocol(), which were previously byte-for-byte
        identical here (issue #51).

        Always adds a flag reflecting how measurable the group's pulses are (MeasureChannels/
        MeasureBoards/MeasureTimings, depending on configured thresholds) -- there used to be a
        debug_info opt-out for this, removed so the hardware measurements onPulseResult()
        receives as a result are never silently unavailable (GitHub #78/#137; see
        get_measurements_logger() for where that data actually ends up). Per unifus.ExecFlag's
        own docs, these three are a strict superset hierarchy, not independent bits --
        MeasureChannels = MeasureBoards + channel measurements = MeasureTimings + board +
        channel measurements -- so this is really "pick the most detailed mode the pulse can
        support", each tier needing a progressively longer pulse. When interleaving, that has to
        be judged against the *shortest* pulse_dur across the whole group, not an arbitrary
        protocol's: a mode chosen for a longer pulse elsewhere in the round could be more than
        the shortest one can actually support. Ramping, by contrast, genuinely is a single
        whole-group setting (see send_protocol()'s own docstring) -- so the extra ramp-transient
        time it needs is still read from protocols[0] only, the same protocol whose ramp
        settings actually took effect for the whole group.

        Parameters:
            protocols (list(TUSProtocol)): Every protocol passed to send_protocol() (a single
                protocol is still a length-1 list here).

        Returns:
            unifus.ExecFlag: The computed flags.
        """

        # Flags to disable checking the current limit
        exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                      unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

        protocol0 = protocols[0]
        min_pulse_dur = min(protocol.pulse_dur for protocol in protocols)

        ramp_transient_t = 0
        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                     'Rectangular - no ramping')
        if protocol0.pulse_ramp_dur > 0 and protocol0.pulse_ramp_shape != rect_ramp:
            ramp_transient_t = float(
                get_config_value(
                    get_logger(), config, 'Equipment.Manufacturer.IGT',
                    'Min. time in between ramping up and down [ms]', 0.070))  # [ms]

        measure_ch_level = float(
            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                             'Pulse dur. flag level MeasureChannels [ms]', 4.570))

        measure_boards_level = float(
            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                             'Pulse dur. flag level MeasureBoards [ms]', 0.035))

        measure_time_level = float(
            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                             'Pulse dur. flag level MeasureTimings [ms]', 0.001))

        if min_pulse_dur > measure_ch_level + ramp_transient_t:  # [ms]
            exec_flags |= unifus.ExecFlag.MeasureChannels

        elif min_pulse_dur >= measure_boards_level + ramp_transient_t:  # [ms]
            exec_flags |= unifus.ExecFlag.MeasureBoards

        elif min_pulse_dur >= measure_time_level + ramp_transient_t:  # [ms]:
            exec_flags |= unifus.ExecFlag.MeasureTimings  # or NONE

        return exec_flags

    @staticmethod
    def _build_transducer_channel_ranges(protocol):
        """One entry per slot in protocol.slots (see VoltageFeedbackTracker's own docstring for
        the shape), in slot order -- matching _define_pulse_group()'s own channel numbering, so
        channel N here always means the same physical channel _define_pulse_group() sent."""

        channel_start = 0
        channel_ranges = []
        for slot in protocol.slots:
            elements = slot.transducer.elements
            # slot.volt is only ever populated once a combo is active (see TransducerSlot's own
            # power setters) -- None here means there's nothing to compare measured voltage
            # against for this slot; VoltageFeedbackTracker still reports its measured average,
            # it just skips the deviation/margin/warning logic (see its own docstring). A slot's
            # own volt can be a single shared value or one per element -- either way, averaged
            # down to one representative expected value here, matching how the tracker also
            # only ever compares a transducer-wide average, never per channel.
            expected_volt = sum(slot.volt) / len(slot.volt) if slot.volt else None
            channel_ranges.append({
                'serial': slot.transducer.serial,
                'channel_start': channel_start,
                'channel_end': channel_start + elements,
                'expected_volt': expected_volt,
            })
            channel_start += elements
        return channel_ranges

    def _configure_voltage_feedback(self, protocols, sent_protocol_info):
        """
        Builds and attaches a fresh VoltageFeedbackDispatcher to self.listener for the
        execution about to start (GitHub #137) -- called right before startSequence() by both
        wait_for_trigger() and execute_protocol(). One VoltageFeedbackTracker per protocol (see
        VoltageFeedbackDispatcher's own docstring for why -- each interleaved protocol's own
        grouping/reporting must stay independent of how the others' pulses interleave with it),
        each with its own channel ranges/expected voltages (see
        _build_transducer_channel_ranges()) but otherwise identically configured: every protocol
        in the group shares the same wall-clock duration and fires exactly once per round, so
        total_pulses/num_groups/margin/consecutive_for_warning are the same for all of them.

        Parameters:
            protocols (list(TUSProtocol)): Every protocol passed to send_protocol().
            sent_protocol_info (dict): send_protocol()'s own bookkeeping for this buffer (see
                register_sent_protocol()) -- 'n_pulse_train_rep' (how many pulses *each*
                protocol in the group contributes -- one per round) and
                'total_protocol_duration_ms' size every tracker's groups identically.
        """

        total_pulses = sent_protocol_info.get('n_pulse_train_rep') or 0
        total_duration_s = (sent_protocol_info.get('total_protocol_duration_ms') or 0) / 1000.0

        config_groups = int(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Voltage feedback groups', 5))
        # At least once a minute, however few groups Voltage feedback groups asks for -- a long
        # protocol split into only config_groups groups could otherwise go many minutes between
        # updates, defeating the "researcher sees the system is doing something" goal.
        num_groups = max(config_groups, math.ceil(total_duration_s / 60)) if total_duration_s \
            else config_groups

        margin_v = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                          'Voltage feedback margin [V]', 3.0))
        consecutive_for_warning = int(get_config_value(
            get_logger(), config, 'Equipment.Manufacturer.IGT',
            'Voltage feedback consecutive groups for warning', 2))

        trackers = [
            VoltageFeedbackTracker(self._build_transducer_channel_ranges(protocol), total_pulses,
                                   num_groups, margin_v, consecutive_for_warning)
            for protocol in protocols]
        self.listener.voltage_feedback = VoltageFeedbackDispatcher(trackers)

    def get_trigger_options(self):
        """
        Returns a list of available trigger options, for wait_for_trigger()'s own trigger_option
        parameter.

        Returns:
            List[str]: Available trigger options.
        """

        return get_config_value(get_logger(), config, 'Trigger', 'Options', '').split('\n')

    def wait_for_trigger(self, protocols, trigger_option, n_triggers=None,
                         total_alternating_duration_ms=None, buffer_num=0):
        """
        Activates the listener on the IGT ultrasound driving system to wait for the trigger to
        execute the previously sent protocol(s). When interleaving, the ramp-transient timing
        this computes is taken from only the first protocol given, matching send_protocol()'s
        own "ramping is a whole-group setting, not per interleaved protocol" behavior.

        trigger_option/n_triggers/buffer_num apply to the whole group being waited on: there is
        exactly one trigger event and one hardware buffer, whether it's a single protocol or
        several interleaved ones.

        Exits with a clear message if send_protocol() hasn't been called for this buffer yet --
        unlike a dropped connection (which reconnects and resends automatically, since that's an
        external failure rather than a caller mistake), this method never sends on the caller's
        behalf.

        Parameters:
            protocols (TUSProtocol or list(TUSProtocol)): Same protocol(s) already passed to
                send_protocol().
            trigger_option (str): The chosen trigger option, e.g. one of
                                  self.get_trigger_options() -- 'TriggerOnePulseTrain' or
                                  'TriggerWholeProtocol' (the "no trigger" option makes no sense
                                  here, since calling this method at all means a trigger is
                                  wanted -- use execute_protocol() directly instead when it
                                  isn't).
            n_triggers (int): Number of times a trigger will be sent -- required when
                              trigger_option is 'TriggerOnePulseTrain' (one pulse train fires per
                              trigger, so the driving system needs to know in advance how many to
                              expect), not valid for any other trigger_option.
            total_alternating_duration_ms (float): Same value already passed to send_protocol()
                -- required (must be > 0) when interleaving more than one protocol.
            buffer_num (int): Same value already passed to send_protocol() for these protocols.
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        protocol0 = protocols[0]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)

        # Checked regardless of connection state, and before it: a protocol that was never sent
        # is a caller mistake either way (never connected at all, or connected but forgot to
        # call send_protocol()) -- not something to silently paper over here, especially since
        # doing so would rely on total_alternating_duration_ms still matching whatever the
        # caller actually intended to send, which nothing here can verify. Only once a protocol
        # is known to have been sent successfully at least once does losing the connection
        # afterward count as an external failure worth automatically recovering from (below).
        self._assert_ready_to_run(protocols, buffer_num, total_alternating_duration_ms,
                                  'wait_for_trigger')

        if self.is_connected():
            try:
                # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                # To use trigger, add one of unifus::ExecFlag::Trigger*
                exec_flags = self._compute_exec_flags(protocols)

                sent_protocol_info = self.sent_protocols.get(buffer_num, {})
                n_pulse_train_rep = sent_protocol_info.get('n_pulse_train_rep')
                pulse_train_delay = sent_protocol_info.get('pulse_train_delay')

                # Determining trigger flag.
                pulse_train_trigger = get_config_value(get_logger(), config, 'Trigger',
                                                       'Option.pulse_train',
                                                       'TriggerOnePulseTrain')
                whole_protocol_trigger = get_config_value(get_logger(), config, 'Trigger',
                                                          'Option.whole_protocol',
                                                          'TriggerWholeProtocol')
                if trigger_option == pulse_train_trigger:
                    # One pulse train fires per trigger received, so the driving system
                    # genuinely needs to know in advance how many triggers to expect -- there is
                    # no sensible default to fall back to.
                    if n_triggers is None:
                        message = ("n_triggers is required when trigger_option is " +
                                   f"'{pulse_train_trigger}' -- it tells the driving system how " +
                                   'many triggers to expect (one pulse train fires per trigger).')
                        get_logger().critical(message)
                        sys.exit(message)
                    validate_value(n_triggers, 'Number of anticipated triggers (n_triggers)',
                                   True, True, True, False)
                    exec_flags |= unifus.ExecFlag.TriggerOneSequence

                    # n_triggers overrides whatever send_protocol() already derived for this
                    # buffer (from protocol0's own pulse_train_rep_int/pulse_train_rep_dur for a
                    # single protocol, or from total_alternating_duration_ms/pulse_rep_int when
                    # interleaving) -- warn explicitly, since a researcher may well have set
                    # those expecting them to determine the actual repetition count.
                    get_logger().warning(
                        f"trigger_option '{pulse_train_trigger}' overrides the repetition "
                        f'count/delay already computed for buffer {buffer_num} '
                        f'({n_pulse_train_rep} repetition(s), {pulse_train_delay} ms delay) -- '
                        f'using n_triggers={n_triggers} instead.')
                    n_pulse_train_rep = n_triggers
                    pulse_train_delay = 0  # trigger will determine delay

                elif trigger_option == whole_protocol_trigger:
                    if n_triggers is not None:
                        message = ("n_triggers only applies when trigger_option is " +
                                   f"'{pulse_train_trigger}' -- '{whole_protocol_trigger}' " +
                                   'always fires exactly one trigger for the whole protocol.')
                        get_logger().critical(message)
                        sys.exit(message)
                    # Purely for the "Waiting for a total of N trigger(s)" log line below --
                    # never used to decide anything on the hardware side for this trigger mode.
                    n_triggers = 1
                    exec_flags |= unifus.ExecFlag.TriggerAllSequences

                else:
                    message = (
                        f'Trigger option {trigger_option} is not identical to implemented ' +
                        f'trigger options: {self.get_trigger_options()}.')
                    get_logger().critical(message)
                    sys.exit(message)

                get_logger().info(f"Waiting for a total of {n_triggers} trigger(s)...")

                # Logged before arming, so a researcher knows what will fire once the external
                # trigger comes in, before they go trigger it themselves (GitHub #125).
                self._log_intensity_summary(buffer_num, 'This will fire once triggered:')

                self._configure_voltage_feedback(protocols, sent_protocol_info)
                self.gen.prepareSequence(buffer_num, n_pulse_train_rep, pulse_train_delay,
                                         exec_flags)

                self.gen.startSequence()

                # Only set once arming has actually succeeded -- read back by
                # wait_for_trigger_result() (see its own docstring) to confirm it's being called
                # for a buffer that's genuinely armed, not merely sent.
                self.sent_protocols[buffer_num]['armed'] = True

            except Exception as why:
                message = f"Exception: {why}"
                get_logger().critical(message)
                sys.exit(message)
        else:
            # Reached only once a protocol is confirmed sent (above) -- reconnecting and
            # resending here is recovering the driving system's own state after losing the
            # connection, not guessing at values for a first-time send. Safe to just pass
            # protocols/total_alternating_duration_ms through as given: _assert_ready_to_run()
            # above already guarantees both match what this buffer was actually sent with --
            # a mismatch in either would have exited before ever reaching this branch.
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol0.driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms, buffer_num)
            self.wait_for_trigger(protocols, trigger_option, n_triggers,
                                  total_alternating_duration_ms, buffer_num)

    def wait_for_trigger_result(self, buffer_num=0, timeout_s=5.0):
        """
        Waits (blocking) for a previously armed triggered protocol to finish, and exits if the
        driving system reports its execution failed -- or if timeout_s elapses without the
        driving system ever reporting a result at all (GitHub #78), e.g. because the external
        trigger never actually arrived (a disconnected trigger cable, a researcher who forgot to
        press it). That second case is not an execution error (exec_error_code stays None --
        onSequenceResult() is simply never called), so without an explicit timeout check this
        would otherwise silently fall through to reporting success on a protocol that never
        fired at all.

        wait_for_trigger() only arms the protocol to fire on the external trigger and returns
        immediately -- it does not wait for or observe the actual execution result (see GitHub
        issue #112). Call this once the external trigger is expected to have fired (or with a
        generous timeout) to check that the driving system actually reported success.

        Exits with a clear message unless wait_for_trigger() has actually armed this buffer --
        being merely sent (send_protocol() called, but wait_for_trigger() never was, e.g. the
        caller used execute_protocol() instead) is not enough: reaching this method without a
        real arm behind it is always a caller mistake, never something to silently wait out.

        Parameters:
            buffer_num (int): Which hardware buffer to report on (starting at 0) --
                looks up what send_protocol() actually sent to it for the confirmation log below
                (GitHub #122/#125), rather than trusting a protocols argument re-supplied here,
                which would have no actual bearing on what's armed on the driving system.
            timeout_s (float): How long to wait for the triggered execution to finish, in
            seconds.
        """

        if not self.sent_protocols.get(buffer_num, {}).get('armed', False):
            message = (f'Buffer {buffer_num} has not been armed for a trigger -- nothing to ' +
                       'wait for. Call send_protocol() and wait_for_trigger() before ' +
                       'wait_for_trigger_result().')
            get_logger().critical(message)
            sys.exit(message)

        # wait_protocol() returns False specifically on timeout (see its own docstring) --
        # distinct from exec_error_code, which is only ever set once onSequenceResult() actually
        # fires. A timeout means that never happened at all, so there is nothing to check
        # exec_error_code for: the driving system never reported anything, successful or not.
        if self.listener.wait_protocol(timeout_s) is False:
            message = (f'Timed out after {timeout_s}s waiting for buffer {buffer_num}\'s ' +
                       'triggered protocol to finish -- the driving system never reported a ' +
                       'result. The external trigger may never have arrived. No confirmation ' +
                       'that anything was emitted.')
            get_logger().critical(message)
            sys.exit(message)

        if self.listener.exec_error_code is not None:
            message = ('Protocol execution failed on the driving system (error ' +
                       f'code: {self.listener.exec_error_code}). No ultrasound was ' +
                       'emitted.')
            get_logger().critical(message)
            sys.exit(message)

        self._log_intensity_summary(buffer_num, 'Triggered protocol executed successfully:')

    def has_execution_error(self):
        """
        Non-blocking check for whether the previously armed/started execution has failed.

        Unlike wait_for_trigger_result(), this returns immediately with whatever the listener
        currently knows instead of blocking -- call it repeatedly (e.g. in your own polling
        loop) while waiting for an external trigger to fire, for real-time reaction to a
        failure instead of only finding out once you call wait_for_trigger_result(). This does
        not exit on error itself: it is a getter, so the caller decides what to do (log, stop
        other equipment, exit, ...).

        Returns:
            int or None: The driving system's error code if the last (or in-progress)
            execution failed, None if it succeeded or hasn't finished yet.
        """

        return self.listener.exec_error_code

    def execute_protocol(self, protocols, total_alternating_duration_ms=None, buffer_num=0):
        """
        Executes the previously sent protocol(s) on the IGT ultrasound driving system. When
        interleaving, the ramp-transient timing this computes is taken from only the first
        protocol given, matching send_protocol()'s own "ramping is a whole-group setting, not
        per interleaved protocol" behavior.

        Exits with a clear message if the driving system reports execution failed, or if it
        never reports a result at all within the protocol's own expected duration (GitHub #78)
        -- that second case is not an execution error (exec_error_code stays None), so without
        an explicit timeout check this would otherwise silently report success on a protocol
        that never actually fired.

        Exits with a clear message if send_protocol() hasn't been called for this buffer yet --
        unlike a dropped connection (which reconnects and resends automatically, since that's an
        external failure rather than a caller mistake), this method never sends on the caller's
        behalf.

        Parameters:
            protocols (TUSProtocol or list(TUSProtocol)): Same protocol(s) already passed to
                send_protocol().
            total_alternating_duration_ms (float): Same value already passed to send_protocol()
                -- required (must be > 0) when interleaving more than one protocol.
            buffer_num (int): Same value already passed to send_protocol() for these protocols.
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        protocol0 = protocols[0]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)

        get_logger().debug(f'Maximum allowed pressure is: {get_max_pressure()} MPa')

        get_logger().info('Executing protocol...')

        # Checked regardless of connection state, and before it: a protocol that was never sent
        # is a caller mistake either way (never connected at all, or connected but forgot to
        # call send_protocol()) -- not something to silently paper over here, especially since
        # doing so would rely on total_alternating_duration_ms still matching whatever the
        # caller actually intended to send, which nothing here can verify. Only once a protocol
        # is known to have been sent successfully at least once does losing the connection
        # afterward count as an external failure worth automatically recovering from (below).
        self._assert_ready_to_run(protocols, buffer_num, total_alternating_duration_ms,
                                  'execute_protocol')

        if self.is_connected():
            try:
                # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                # To use trigger, add one of unifus::ExecFlag::Trigger*
                exec_flags = self._compute_exec_flags(protocols)

                sent_protocol_info = self.sent_protocols.get(buffer_num, {})
                self._configure_voltage_feedback(protocols, sent_protocol_info)
                self.gen.prepareSequence(buffer_num,
                                         sent_protocol_info.get('n_pulse_train_rep'),
                                         sent_protocol_info.get('pulse_train_delay'),
                                         exec_flags)

                # Logged right before the (potentially long) blocking wait below, so a
                # researcher watching the log knows what they're waiting for (GitHub #125).
                self._log_intensity_summary(buffer_num, 'About to execute:')

                self.gen.startSequence()
                # wait_protocol() returns False specifically on timeout (see its own docstring
                # and the matching check in wait_for_trigger_result(), GitHub #78) -- distinct
                # from exec_error_code, which is only ever set once onSequenceResult() actually
                # fires. A timeout here means the driving system never reported anything at all,
                # successful or not, so this must not silently fall through to reporting success.
                if self.listener.wait_protocol(
                        sent_protocol_info.get('total_protocol_duration_ms') / 1000.0) is False:
                    message = (
                        f'Timed out waiting for buffer {buffer_num}\'s protocol to ' +
                        'finish -- the driving system never reported a result. No ' +
                        'confirmation that anything was emitted.')
                    get_logger().critical(message)
                    sys.exit(message)

                if self.listener.exec_error_code is not None:
                    message = ('Protocol execution failed on the driving system (error ' +
                               f'code: {self.listener.exec_error_code}). Potentially no ' +
                               'ultrasound emitted.')
                    get_logger().critical(message)
                    sys.exit(message)

                # Confirms execution actually succeeded (GitHub #122), naming exactly what was
                # fired (GitHub #125) -- distinct from "About to execute" above even though the
                # values are identical, since the two log points confirm different things:
                # intent, and actual outcome.
                self._log_intensity_summary(buffer_num, 'Protocol executed successfully:')

            except Exception as why:
                message = f"Exception: {why}"
                get_logger().critical(message)
                sys.exit(message)

        else:
            # Reached only once a protocol is confirmed sent (above) -- reconnecting and
            # resending here is recovering the driving system's own state after losing the
            # connection, not guessing at values for a first-time send. Safe to just pass
            # protocols/total_alternating_duration_ms through as given: _assert_ready_to_run()
            # above already guarantees both match what this buffer was actually sent with --
            # a mismatch in either would have exited before ever reaching this branch.
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol0.driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms, buffer_num)
            self.execute_protocol(protocols, total_alternating_duration_ms, buffer_num)

    def disconnect(self):
        """
        Disconnects from the IGT ultrasound driving system.
        """

        get_logger().info('Disconnecting...')

        if self.gen is not None:
            # disabling any old modulation
            self.gen.stopSequence()

            time.sleep(2)

            self.gen.setPulseModulation([], 0, [], 0)  # disable any modulation

        if self.fus is not None:
            self.fus.clearListeners()
            self.fus.disconnect()

            if not self.is_connected():
                get_logger().info("Disconnected.")
            else:
                get_logger().error("Failed to disconnect")

    def _define_pulse_train(self, protocol, pulse):
        """
        Defines the pulse train for the IGT ultrasound driving system.

        Parameters:
            protocol (TUSProtocol): The protocol object containing ultrasound parameters.
            pulse (unifus.Pulse): The defined pulse.

        Returns:
            pulse_train_seq: list of pulses representing a pulse train
            pulse_train_delay: pulse train delay in miliseconds

        """

        # number of executions of one pulse train
        n_pulse_train = math.floor(protocol.pulse_train_dur / protocol.pulse_rep_int)

        # Define a complete pulse train
        pulse_train_seq = []
        pulse_train_seq += n_pulse_train * [pulse]

        # milliseconds between pulse trains
        pulse_train_delay = protocol.pulse_train_rep_int - protocol.pulse_train_dur

        return pulse_train_seq, pulse_train_delay

    def _set_phases(self, pulse, focus_wrt_mid_bowl, steer_info, dephasing_degree,
                    focus_offset_x=0.0, focus_offset_y=0.0):
        """
        Gets the phases for the IGT ultrasound driving system.

        Parameters:
            pulse (unifus.Pulse): The defined pulse.
            focus_wrt_mid_bowl (float): The focus value wrt the middle of the transducer bowl
                                        [mm].
            steer_info (str): Path to the steer information.
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases
            based on the focus are overridden.
            focus_offset_x (float): Lateral x offset [mm] of the target from the z axis, only
                                    non-zero for a 3D-steering transducer
                                    (TransducerSlot.focus_offset_x). Defaults to 0.0 (on-axis),
                                    the only value ever reached via the .xlsx steer path (below).
            focus_offset_y (float): Lateral y offset [mm] of the target from the z axis, same
                                    conditions as focus_offset_x (TransducerSlot.focus_offset_y).

        Returns:
            list: List of phases.
        """

        # transducer has been chosen where phases are calculated based on phase law
        package_name = get_config_value(get_logger(), config, 'General', 'Package name',
                                        'fus_driving_systems')
        if steer_info.endswith('.ini'):

            trans = transducer_xyz.Transducer()
            ini_path = str(importlib.resources.files(package_name).joinpath(steer_info))
            if not trans.load(ini_path):
                message = f'Error: can not load the transducer definition from {ini_path}'
                get_logger().critical(message)
                sys.exit(message)

            # Natural focus (radius of curvature) comes from the transducer's own .ini steer
            # file (trans.focalLength) -- not a separately-maintained config value -- so it can
            # never drift out of sync with the same file's element coordinates.
            # Calculate target focus with respect to natural focus: + is before natural focus,
            # - is after natural focus
            aim_wrt_natural_focus = trans.focalLength - focus_wrt_mid_bowl

            # Aim n mm away from the natural focal spot, on main axis (Z), offset laterally by
            # (focus_offset_x, focus_offset_y), both 0.0 unless this slot's transducer is
            # 3D-steering-capable (see TransducerSlot._set_focus_xyz()).
            phases = trans.compute_phases(
                pulse, (focus_offset_x, focus_offset_y, aim_wrt_natural_focus),
                focus_wrt_mid_bowl, dephasing_degree)

        elif steer_info.endswith('.xlsx'):
            # This lookup-table path has no x/y concept at all, Transducer.can_3d_steer's own
            # consistency check (transducer.py) already prevents a .xlsx-based transducer from
            # ever being configured as 3D-steering-capable, so this is unreachable via the
            # public API. Guarded explicitly anyway.
            if focus_offset_x != 0 or focus_offset_y != 0:
                message = (f'Lateral steering (x={focus_offset_x}, y={focus_offset_y}) is not ' +
                           'supported for the .xlsx steer information path.')
                get_logger().critical(message)
                sys.exit(message)

            # Import excel file containing phases per focal depth
            excel_path = str(importlib.resources.files(package_name).joinpath(steer_info))

            get_logger().debug('Extract phase information from %s', excel_path)

            if os.path.exists(excel_path):
                data = pd.read_excel(excel_path, engine='openpyxl')

                # Make sure both values have the same amount of decimals
                focus_wrt_mid_bowl = round(focus_wrt_mid_bowl, 1)
                match_row = data.loc[data['Distance'] == focus_wrt_mid_bowl]

                if match_row.empty:
                    message = (f'No focus in transducer phases file {excel_path}' +
                               f' corresponds with {focus_wrt_mid_bowl}')
                    get_logger().critical(message)
                    sys.exit(message)

                elif len(match_row) > 1:
                    message = (f'Duplicate foci {focus_wrt_mid_bowl} found in transducer ' +
                               f'phases file {excel_path}. First found entry will be used.')
                    get_logger().error(message)

                    match_row = match_row[0]

                # Retrieve phases dependent of number of channels
                phases = match_row.iloc[0].iloc[1:int(self.n_channels)+1].to_list()

                if dephasing_degree is not None:
                    phases = transducer_xyz.apply_cyclic_dephasing(phases, dephasing_degree)

                phases_str = ', '.join([format(x, '.2f') for x in phases])
                get_logger().debug(
                    f'Computed phases for set focus of {focus_wrt_mid_bowl}: {phases_str}')

            else:
                message = ("Pipeline is cancelled. The following direction cannot be found: " +
                           f"{excel_path}")
                get_logger().critical(message)
                sys.exit(message)

        else:
            message = ("Steer information is expected to be a '.ini' or '.xlsx' file, but got: " +
                       f"{steer_info}")
            get_logger().critical(message)
            sys.exit(message)

        return phases

    def _apply_ramping(self, protocol):
        """
        Applies ramping on the IGT ultrasound driving system.

        Parameters:
            protocol (TUSProtocol): The protocol object containing ultrasound parameters.
        """

        # Use best temporal resolution for pulse ramping [ms]
        min_ramp_temp_res = float(get_config_value(
            get_logger(), config, 'Equipment.Manufacturer.IGT',
            'Min. temporal ramping resolution [ms]',
            0.005))  # [ms]
        max_ramp_steps = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                                'Max. amount of ramping steps', 1023))

        ramp_n_steps = int(protocol.pulse_ramp_dur/min_ramp_temp_res)
        if ramp_n_steps > max_ramp_steps:
            min_ramp_temp_res = protocol.pulse_ramp_dur/max_ramp_steps

        # Note: ramp up and ramp down order are the other way around
        # ramp up descends, ramp down ascends
        ampl_ramp = self._get_ramping_amplitude(protocol, min_ramp_temp_res)

        # Execution with pulse modulation (automatically disable ramps if any)
        # Values are attenuation in percent of the full Pulse amplitude.
        # 0 = no attenuation = full amplitude, 100 = full attenuation = 0 amplitude.
        max_ampl = 100  # [%]
        ramp_down = ampl_ramp * max_ampl
        ramp_down = [int(pUp) for pUp in ramp_down]

        ramp_up = np.flip(ampl_ramp) * max_ampl
        ramp_up = [int(pDown) for pDown in ramp_up]

        self.gen.setPulseModulation(
            ramp_up, min_ramp_temp_res,  # beginning
            ramp_down, min_ramp_temp_res)  # end

    def _get_ramping_amplitude(self, protocol, pulse_ramp_temp_res):
        """
        Gets the ramping array that has to be applied to the amplitude for the IGT ultrasound
        driving system.

        Parameters:
            protocol (TUSProtocol): The protocol object containing ultrasound parameters.
            pulse_ramp_temp_res (float): temporal resolution for pulse ramping [ms].

        Returns:
            tuple: A tuple containing the amplitude ramping and step duration.
        """

        lin_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.lin', 'Linear')
        tuk_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.tuk', 'Tukey')
        if protocol.pulse_ramp_shape == lin_ramp:  # Linear ramping
            # amount of points where ramping is applied
            n_points = math.floor(protocol.pulse_ramp_dur/pulse_ramp_temp_res)
            ampl_ramp = np.linspace(0, 1, n_points)

        elif protocol.pulse_ramp_shape == tuk_ramp:  # Tukey ramping
            # amount of points where ramping is applied
            n_points = math.floor(protocol.pulse_ramp_dur/pulse_ramp_temp_res)
            alpha = 1
            x = np.linspace(0, alpha/2, n_points)
            ampl_ramp = np.zeros(n_points)
            for i in range(n_points):
                ampl_ramp[i] = 0.5 * (1 + math.cos((2*math.pi/alpha) * (x[i] - alpha/2)))

        return ampl_ramp
