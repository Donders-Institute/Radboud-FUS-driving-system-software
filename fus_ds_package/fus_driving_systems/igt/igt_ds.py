# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Margely Cornelissen, Stein Fekkes (Radboud University) and Erik Dumont (Image
Guided Therapy)

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

**Attribution Notice**:
If you use this kit in your research or project, please refer to the 'How to Cite' section in the
README.md file of https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
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

from fus_driving_systems.igt.utils import ExecListener
from fus_driving_systems.igt import transducer_xyz
from fus_driving_systems.igt import unifus
from fus_driving_systems.utils import get_config_value

# Access the logger
from fus_driving_systems.config.logging_config import (enable_crash_detection, get_logger,
                                                       get_session_log_dir,
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
            buffer_num (int): Which hardware buffer to check (see TUSProtocol.buffer_num).

        Returns:
            bool: True if a protocol has been sent to that buffer, False otherwise.
        """

        return buffer_num in self.sent_protocols

    def register_sent_protocol(self, buffer_num, pulse_train_seq, n_pulse_train_rep,
                               pulse_train_delay, phases=None):
        """
        Records the sent protocol under its buffer number in the sent protocol list.
            buffer_num: which hardware buffer this protocol was sent to (see
                TUSProtocol.buffer_num)
            pulse_train_seq: list of pulses representing a pulse train
            n_pulse_train_rep: number of executions of one pulse train
            pulse_train_delay: pulse train delay in miliseconds
            phases: phases in degrees to reach focal depth
            total_protocol_duration_ms (float): Total duration of the protocol in milliseconds.
        """

        self.sent_protocols[buffer_num] = {}
        self.sent_protocols[buffer_num]['pulse_train_seq'] = pulse_train_seq
        self.sent_protocols[buffer_num]['n_pulse_train_rep'] = n_pulse_train_rep
        self.sent_protocols[buffer_num]['pulse_train_delay'] = pulse_train_delay
        self.sent_protocols[buffer_num]['phases'] = phases

        total_protocol_duration_ms = unifus.sequenceDurationMs(pulse_train_seq, n_pulse_train_rep,
                                                               pulse_train_delay)

        wait_time_ms = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                              'Wait time before responsive [ms]', 100))
        self.sent_protocols[buffer_num]['total_protocol_duration_ms'] = (
            total_protocol_duration_ms + wait_time_ms)

        get_logger().debug(f"Stored protocol in buffer {buffer_num}: " +
                           f"{self.sent_protocols[buffer_num]}")

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

        if self.connected:
            get_logger().info('Already connected, skipping reconnection.')
            return True

        get_logger().info('Connecting...')

        reconnect_delay_s = float(get_config_value(get_logger(), config, 'General',
                                                   'Delay before reconnecting [s]', 2))

        if attempt == 0:
            # Experimental mitigation for the non-deterministic kernel-death crashes
            # reported in GitHub issue #126. self.connected (checked above) and
            # self.fus.isConnected() (checked further below) both only reflect state
            # tracked by *this* process/instance -- a fresh process (e.g. a new Spyder
            # console the next morning) always starts with neither, so neither check can
            # ever reveal whether a previous, possibly crashed session left the native
            # driver holding a connection open. Forcing a disconnect on a throwaway
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
            log_name = get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                        'Default log filename prefix', 'standalone_igt')

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
            suffix = get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                      'Default log filename suffix', '_igt_ds_log')
            unifus.setLogPath(log_dir, log_name + suffix)
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
            if self.fus.isConnected():
                self.connected = True
                get_logger().debug('Driving system is connected.')

                self.gen = self.fus.gen()
                self.n_channels = self.gen.getParam(unifus.GenParam.ChannelCount)
                get_logger().debug("Generator: %s channels", self.n_channels)
                return True

            self.connected = False
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
            error_messages.append("The maximum amount of pulses within a pulse train is " +
                                  f"{max_n_pulses}. Currently, the amount is {n_pulses}.")

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

    def send_protocol(self, protocols, total_alternating_duration_ms=None):
        """
        Validates and sends one or more ultrasound protocols to the IGT ultrasound driving
        system. More than one protocol means they are interleaved: sent as one alternating group,
        fired in the order given, repeating for total_alternating_duration_ms. Ramping
        (pulse_ramp_shape/pulse_ramp_dur) is applied once for the whole interleaved group, taken
        from only the first protocol given -- it's a generator-wide setting, not something each
        interleaved protocol can configure independently, so every protocol given must declare
        the same ramping (enforced below) even though only the first one's value is actually
        used.

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
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)

        for protocol in protocols:
            self._assert_ready_to_send(protocol)

        # Only protocols[0].buffer_num is ever actually read below (the whole interleaved group
        # is sent to that one buffer, not one buffer per protocol) -- but a caller giving
        # different buffer_num values across the group almost certainly means they mixed up
        # protocols that were never meant to be interleaved together, so reject it explicitly
        # instead of silently going with whichever one happens to be first.
        if len(protocols) > 1 and any(protocol.buffer_num != protocols[0].buffer_num
                                      for protocol in protocols[1:]):
            message = ('All protocols given to interleave must target the same buffer -- got ' +
                       f'{[protocol.buffer_num for protocol in protocols]}.')
            get_logger().critical(message)
            sys.exit(message)

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

        get_logger().info('Validating protocol...')

        for protocol in protocols:
            get_logger().debug(
                'Protocol with the following parameters is validated before sending: \n ' +
                '%s', protocol)

            error_messages = self.validate_protocol(protocol)

            if error_messages:
                for error in error_messages:
                    get_logger().critical(error)
                sys.exit('(Multiple) error(s) found when validating protocol, see log file.')

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
                get_logger().debug(
                    f'Interleaving {len(protocols)} protocols -- each contributes one pulse '
                    'train per round.')

                # One pulse per protocol, not a repeated pulse train per protocol -- unlike the
                # N=1 branch above (_define_pulse_train()), each interleaved protocol's own
                # pulse_train_dur/pulse_train_rep_int/pulse_train_rep_dur have no effect here
                # (see this method's own docstring). Theoretically possible to support, but not
                # yet designed: would need a real decision on what "interleaved pulse trains"
                # (as opposed to interleaved single pulses) should actually mean here.
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
            self.gen.sendSequence(protocol0.buffer_num, pulse_train_seq)

            self.register_sent_protocol(protocol0.buffer_num, pulse_train_seq, n_pulse_train_rep,
                                        pulse_train_delay, phases)

        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocols[0].driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms)

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
                                                   slot.dephasing_degree)
                phases = phases + computed_phases

        # set phase offset for all channels (angle in [0,360] degrees)
        pulse.setPhases(phases)

        # set frequency for all channels, in Hz
        pulse.setFrequencies(freqs)

        # set amplitude for all channels in percent (of max amplitude)
        pulse.setAmplitudes(ampls)

        return pulse, phases

    def _compute_exec_flags(self, protocols, debug_info):
        """
        Computes the base unifus.ExecFlag for executing or arming a previously sent protocol --
        shared by wait_for_trigger() and execute_protocol(), which were previously byte-for-byte
        identical here (issue #51).

        When debug_info, adds a flag reflecting how measurable the group's pulses are
        (MeasureChannels/MeasureBoards/MeasureTimings, depending on configured thresholds).
        Per unifus.ExecFlag's own docs, these three are a strict superset hierarchy, not
        independent bits -- MeasureChannels = MeasureBoards + channel measurements =
        MeasureTimings + board + channel measurements -- so this is really "pick the most
        detailed mode the pulse can support", each tier needing a progressively longer pulse.
        When interleaving, that has to be judged against the *shortest* pulse_dur across the
        whole group, not an arbitrary protocol's: a mode chosen for a longer pulse elsewhere in
        the round could be more than the shortest one can actually support. Ramping, by
        contrast, genuinely is a single whole-group setting (see send_protocol()'s own
        docstring) -- so the extra ramp-transient time it needs is still read from protocols[0]
        only, the same protocol whose ramp settings actually took effect for the whole group.

        Parameters:
            protocols (list(TUSProtocol)): Every protocol passed to send_protocol() (a single
                protocol is still a length-1 list here).
            debug_info (bool): Whether to compute and add the extra measurement-related flags.

        Returns:
            unifus.ExecFlag: The computed flags.
        """

        # Flags to disable checking the current limit
        exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                      unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

        if debug_info:
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

    def wait_for_trigger(self, protocols, total_alternating_duration_ms=None, debug_info=True):
        """
        Activates the listener on the IGT ultrasound driving system to wait for the trigger to
        execute the previously sent protocol(s). When interleaving, the ramp-transient timing
        this computes is taken from only the first protocol given, matching send_protocol()'s
        own "ramping is a whole-group setting, not per interleaved protocol" behavior. The same
        is true for trigger_option/n_triggers below -- every protocol given must declare the
        same trigger configuration (enforced below) even though only the first one's value is
        actually used.

        Exits with a clear message if send_protocol() hasn't been called for this buffer yet --
        unlike a dropped connection (which reconnects and resends automatically, since that's an
        external failure rather than a caller mistake), this method never sends on the caller's
        behalf.

        Parameters:
            protocols (TUSProtocol or list(TUSProtocol)): Same protocol(s) already passed to
                send_protocol().
            total_alternating_duration_ms (float): Same value already passed to send_protocol()
                -- required (must be > 0) when interleaving more than one protocol.
            debug_info (bool): Whether to compute and set additional execution flags.
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        protocol0 = protocols[0]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)

        # Only protocol0.trigger_option/n_triggers are ever actually read below -- a caller
        # giving different trigger settings across the group almost certainly expected every
        # protocol's own trigger configuration to take effect, so reject it explicitly instead
        # of silently going with whichever one happens to be first.
        if len(protocols) > 1 and any(
                (protocol.trigger_option, protocol.n_triggers)
                != (protocol0.trigger_option, protocol0.n_triggers)
                for protocol in protocols[1:]):
            trigger_settings = [(protocol.trigger_option, protocol.n_triggers)
                                for protocol in protocols]
            message = ('All protocols given to interleave must use the same trigger ' +
                       f'configuration -- got {trigger_settings}.')
            get_logger().critical(message)
            sys.exit(message)

        # Checked regardless of connection state, and before it: a protocol that was never sent
        # is a caller mistake either way (never connected at all, or connected but forgot to
        # call send_protocol()) -- not something to silently paper over here, especially since
        # doing so would rely on total_alternating_duration_ms still matching whatever the
        # caller actually intended to send, which nothing here can verify. Only once a protocol
        # is known to have been sent successfully at least once does losing the connection
        # afterward count as an external failure worth automatically recovering from (below).
        if not self.is_protocol_sent(protocol0.buffer_num):
            message = (f'No protocol has been sent to buffer {protocol0.buffer_num} yet -- ' +
                       'call send_protocol() before wait_for_trigger().')
            get_logger().critical(message)
            sys.exit(message)

        if self.is_connected():
            try:
                # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                # To use trigger, add one of unifus::ExecFlag::Trigger*
                exec_flags = self._compute_exec_flags(protocols, debug_info)

                sent_protocol_info = self.sent_protocols.get(protocol0.buffer_num, {})
                n_pulse_train_rep = sent_protocol_info.get('n_pulse_train_rep')
                pulse_train_delay = sent_protocol_info.get('pulse_train_delay')

                # Determining trigger flag
                pulse_train_trigger = get_config_value(get_logger(), config, 'Trigger',
                                                       'Option.pulse_train',
                                                       'TriggerOnePulseTrain')
                whole_protocol_trigger = get_config_value(get_logger(), config, 'Trigger',
                                                          'Option.whole_protocol',
                                                          'TriggerWholeProtocol')
                if protocol0.trigger_option == pulse_train_trigger:
                    exec_flags |= unifus.ExecFlag.TriggerOneSequence
                    n_pulse_train_rep = protocol0.n_triggers
                    pulse_train_delay = 0  # trigger will determine delay

                elif protocol0.trigger_option == whole_protocol_trigger:
                    exec_flags |= unifus.ExecFlag.TriggerAllSequences

                else:
                    message = (
                        f'Trigger option {protocol0.trigger_option} is not identical to ' +
                        f'implemented trigger options: {protocol0.get_trigger_options()}.')
                    get_logger().critical(message)
                    sys.exit(message)

                get_logger().info(
                    f"Waiting for a total of {protocol0.n_triggers} trigger(s)...")

                self.gen.prepareSequence(protocol0.buffer_num, n_pulse_train_rep,
                                         pulse_train_delay, exec_flags)

                self.gen.startSequence()

            except Exception as why:
                message = f"Exception: {why}"
                get_logger().critical(message)
                sys.exit(message)
        else:
            # Reached only once a protocol is confirmed sent (above) -- reconnecting and
            # resending here is recovering the driving system's own state after losing the
            # connection, not guessing at values for a first-time send.
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol0.driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms)
            self.wait_for_trigger(protocols, total_alternating_duration_ms, debug_info)

    def wait_for_trigger_result(self, timeout_s=5.0):
        """
        Waits (blocking) for a previously armed triggered protocol to finish, and exits if the
        driving system reports its execution failed.

        wait_for_trigger() only arms the protocol to fire on the external trigger and returns
        immediately -- it does not wait for or observe the actual execution result (see GitHub
        issue #112). Call this once the external trigger is expected to have fired (or with a
        generous timeout) to check that the driving system actually reported success.

        Parameters:
            timeout_s (float): How long to wait for the triggered execution to finish, in
            seconds.
        """

        self.listener.wait_protocol(timeout_s)

        if self.listener.exec_error_code is not None:
            message = ('Protocol execution failed on the driving system (error ' +
                       f'code: {self.listener.exec_error_code}). No ultrasound was ' +
                       'emitted.')
            get_logger().critical(message)
            sys.exit(message)

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

    def execute_protocol(self, protocols, total_alternating_duration_ms=None, debug_info=True):
        """
        Executes the previously sent protocol(s) on the IGT ultrasound driving system. When
        interleaving, the ramp-transient timing this computes is taken from only the first
        protocol given, matching send_protocol()'s own "ramping is a whole-group setting, not
        per interleaved protocol" behavior.

        Exits with a clear message if send_protocol() hasn't been called for this buffer yet --
        unlike a dropped connection (which reconnects and resends automatically, since that's an
        external failure rather than a caller mistake), this method never sends on the caller's
        behalf.

        Parameters:
            protocols (TUSProtocol or list(TUSProtocol)): Same protocol(s) already passed to
                send_protocol().
            total_alternating_duration_ms (float): Same value already passed to send_protocol()
                -- required (must be > 0) when interleaving more than one protocol.
            debug_info (bool): Whether to compute and set additional execution flags.
        """

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        protocol0 = protocols[0]

        self._assert_duration_given_when_interleaving(protocols, total_alternating_duration_ms)

        max_press = get_config_value(get_logger(), config, 'Power',
                                     'Maximum pressure allowed in free water [MPa]',
                                     'Not found')

        get_logger().debug(f'Maximum allowed pressure is: {max_press} MPa')

        get_logger().info('Executing protocol...')

        # Checked regardless of connection state, and before it: a protocol that was never sent
        # is a caller mistake either way (never connected at all, or connected but forgot to
        # call send_protocol()) -- not something to silently paper over here, especially since
        # doing so would rely on total_alternating_duration_ms still matching whatever the
        # caller actually intended to send, which nothing here can verify. Only once a protocol
        # is known to have been sent successfully at least once does losing the connection
        # afterward count as an external failure worth automatically recovering from (below).
        if not self.is_protocol_sent(protocol0.buffer_num):
            message = (f'No protocol has been sent to buffer {protocol0.buffer_num} yet -- ' +
                       'call send_protocol() before execute_protocol().')
            get_logger().critical(message)
            sys.exit(message)

        if self.is_connected():
            try:
                # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                # To use trigger, add one of unifus::ExecFlag::Trigger*
                exec_flags = self._compute_exec_flags(protocols, debug_info)

                sent_protocol_info = self.sent_protocols.get(protocol0.buffer_num, {})
                self.gen.prepareSequence(protocol0.buffer_num,
                                         sent_protocol_info.get('n_pulse_train_rep'),
                                         sent_protocol_info.get('pulse_train_delay'),
                                         exec_flags)

                self.gen.startSequence()
                self.listener.wait_protocol(
                    sent_protocol_info.get('total_protocol_duration_ms') / 1000.0)

                if self.listener.exec_error_code is not None:
                    message = ('Protocol execution failed on the driving system (error ' +
                               f'code: {self.listener.exec_error_code}). Potentially no ' +
                               'ultrasound emitted.')
                    get_logger().critical(message)
                    sys.exit(message)

            except Exception as why:
                message = f"Exception: {why}"
                get_logger().critical(message)
                sys.exit(message)

        else:
            # Reached only once a protocol is confirmed sent (above) -- reconnecting and
            # resending here is recovering the driving system's own state after losing the
            # connection, not guessing at values for a first-time send.
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol0.driving_sys.connect_info)
            self.send_protocol(protocols, total_alternating_duration_ms)
            self.execute_protocol(protocols, total_alternating_duration_ms, debug_info)

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

            if not self.fus.isConnected():
                self.connected = False
                get_logger().info("Disconnected.")
            else:
                get_logger().error("Failed to disconnect")
                self.connected = True

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

    def _set_phases(self, pulse, focus, steer_info, dephasing_degree):
        """
        Gets the phases for the IGT ultrasound driving system.

        Parameters:
            pulse (unifus.Pulse): The defined pulse.
            focus (float): The focus value wrt the middle of the transducer bowl [mm].
            steer_info (str): Path to the steer information.
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases
            based on the focus are overridden.

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
            aim_wrt_natural_focus = trans.focalLength - focus

            # Aim n mm away from the natural focal spot, on main axis (Z)
            phases = trans.compute_phases(pulse, (0, 0, aim_wrt_natural_focus), focus,
                                          dephasing_degree)

        elif steer_info.endswith('.xlsx'):
            # Import excel file containing phases per focal depth
            excel_path = str(importlib.resources.files(package_name).joinpath(steer_info))

            get_logger().debug('Extract phase information from %s', excel_path)

            if os.path.exists(excel_path):
                data = pd.read_excel(excel_path, engine='openpyxl')

                # Make sure both values have the same amount of decimals
                focus = round(focus, 1)
                match_row = data.loc[data['Distance'] == focus]

                if match_row.empty:
                    message = (f'No focus in transducer phases file {excel_path}' +
                               f' corresponds with {focus}')
                    get_logger().critical(message)
                    sys.exit(message)

                elif len(match_row) > 1:
                    message = (f'Duplicate foci {focus} found in transducer phases file ' +
                               f'{excel_path}. First found entry will be used.')
                    get_logger().error(message)

                    match_row = match_row[0]

                # Retrieve phases dependent of number of channels
                phases = match_row.iloc[0].iloc[1:int(self.n_channels)+1].to_list()

                if dephasing_degree is not None:
                    if len(dephasing_degree) > 1:
                        get_logger().warning(
                            'Too few or too many entries given at dephasing_degree.' +
                            ' Only the first one is now used for dephasing purposes.')

                    dephasing_degree = dephasing_degree[0]
                    # determine n elements to dephase in one cycle
                    nth_elem = round(360/dephasing_degree)
                    dephasing_elem = 0
                    for i, phase in enumerate(phases):
                        # Add chosen degrees to dephase signal
                        phases[i] = phase + dephasing_degree*dephasing_elem

                        dephasing_elem = dephasing_elem + 1
                        if dephasing_elem == nth_elem:
                            dephasing_elem = 0

                phases_str = ', '.join([format(x, '.2f') for x in phases])
                get_logger().debug(f'Computed phases for set focus of {focus}: {phases_str}')

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
