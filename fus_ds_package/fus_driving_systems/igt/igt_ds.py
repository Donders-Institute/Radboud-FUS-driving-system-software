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
from fus_driving_systems.sequence import Sequence

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
        sent_seq (dict): list with sent sequences
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

        self.sent_seqs = {}
        self.fus = None
        self.listener = None
        self.n_channels = 0

    def is_sequence_sent(self, seq_num):
        """
        Checks whether a sequence has been sent to the ultrasound driving system.

        Returns:
            bool: True if a sequence has been sent, False otherwise.
        """

        return seq_num in self.sent_seqs

    def register_sent_sequence(self, seq_num, seq, n_pulse_train_rep, pulse_train_delay,
                               phases=None):
        """
        Adds the sequence number of the sent sequence to the sent sequence list.
            seq: list of pulses representing a pulse train
            n_pulse_train_rep: number of executions of one pulse train
            pulse_train_delay: pulse train delay in miliseconds
            phases: phases in degrees to reach focal depth
            total_sequence_duration_ms (float): Total duration of the sequence in milliseconds.
        """

        self.sent_seqs[seq_num] = {}
        self.sent_seqs[seq_num]['seq'] = seq
        self.sent_seqs[seq_num]['n_pulse_train_rep'] = n_pulse_train_rep
        self.sent_seqs[seq_num]['pulse_train_delay'] = pulse_train_delay
        self.sent_seqs[seq_num]['phases'] = phases

        total_sequence_duration_ms = unifus.sequenceDurationMs(seq, n_pulse_train_rep,
                                                               pulse_train_delay)

        wait_time_ms = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                              'Wait time before responsive [ms]', 100))
        self.sent_seqs[seq_num]['total_sequence_duration_ms'] = (total_sequence_duration_ms +
                                                                 wait_time_ms)

        get_logger().debug(f"Stored sequence {seq_num}: {self.sent_seqs[seq_num]}")

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

        # When no connection, it is assumed that all sent sequences aren't available (anymore)
        self.sent_seqs = {}
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

    def validate_sequence(self, sequence):
        """
        Validates if the sequence is within the expected ranges.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)

        Returns:
            List: List of error messages.
        """

        error_messages = super().validate_sequence(sequence)

        min_pulse_dur = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                               'Min. pulse duration [ms]', 0.001))
        if sequence.pulse_dur < min_pulse_dur:  # [ms]:
            error_messages.append('Pulse duration is not allowed to be smaller than 1 us.')

        min_pulse_rep_int = float(get_config_value(
            get_logger(), config, 'Equipment.Manufacturer.IGT',
            'Min. pulse rep. interval [ms]', 0.170))
        if sequence.pulse_rep_int < min_pulse_rep_int:  # [ms]
            error_messages.append('Pulse repetition interval is not allowed to be smaller than' +
                                  ' 170 us.')

        min_time_between_ramps = float(
            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                             'Min. time in between ramping up and down [ms]', 0.070))

        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                     'Rectangular - no ramping')
        if sequence.pulse_ramp_dur > 0 and (sequence.pulse_ramp_shape != rect_ramp):
            if sequence.pulse_ramp_dur > sequence.pulse_dur/2 - min_time_between_ramps/2:
                error_messages.append('When applying ramping, there needs to be at least ' +
                                      '70 us between ramping up and down')
        for i, slot in enumerate(sequence.slots):
            if slot.ampl is None:
                error_messages.append(
                    f"Intensity parameter may be set incorrectly for transducer slot {i} " +
                    f"(counting from 0, i.e. sequence.slots[{i}]; {slot.transducer.serial}). " +
                    "Amplitude is None.")

        n_pulses = sequence.pulse_train_dur/sequence.pulse_rep_int
        max_n_pulses = int(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                            'Max. pulses in pulse train', 64))
        if n_pulses > max_n_pulses:
            error_messages.append("The maximum amount of pulses within a pulse train is " +
                                  f"{max_n_pulses}. Currently, the amount is {n_pulses}.")

        return error_messages

    def _assert_ready_to_send(self, sequence):
        """
        Authoritative gate, run once per sequence right before it's actually used: at least one
        transducer slot must have been added (see Sequence.add_slot()), and the combined elements
        across all of its slots must exactly match this driving system's available channels.

        add_slot() itself only fails fast on exceeding available_ch (see
        Sequence._validate_channel_count()) -- it can't require an exact match, since a driving
        system with more than one slot is legitimately "not done yet" after just the first
        add_slot() call. This is the one place that must see the final, complete picture.

        Parameters:
            sequence (Sequence): The sequence to check.
        """

        if not sequence.slots:
            message = ('No transducer slot configured on this sequence -- call ' +
                       'sequence.add_slot(...) at least once before sending it.')
            get_logger().critical(message)
            sys.exit(message)

        total_elements = sum(slot.transducer.elements for slot in sequence.slots)
        if total_elements != sequence.driving_sys.available_ch:
            message = (f'Number of available channels ({sequence.driving_sys.available_ch}) ' +
                       f'does not match the combined elements of the {len(sequence.slots)} ' +
                       f'transducer slot(s) ({total_elements}).')
            get_logger().critical(message)
            sys.exit(message)

    def send_sequence(self, sequences, duration_ms=0):
        """
        Validates and sends one or more ultrasound sequences to the IGT ultrasound driving
        system. More than one sequence means they are interleaved: sent as one alternating group,
        fired in the order given, repeating for duration_ms. Ramping (pulse_ramp_shape/
        pulse_ramp_dur) is applied once for the whole interleaved group, taken from only the
        first sequence given -- it's a generator-wide setting, not something each interleaved
        sequence can configure independently, so every other sequence's own ramp settings are
        silently ignored.

        When interleaving, each sequence contributes exactly one pulse per round of the
        alternating group -- not a repeated pulse train of its own. pulse_dur/pulse_rep_int
        still apply per sequence (pulse_rep_int decides how much of the shared round this
        sequence's own pulse occupies, via its trailing delay), but pulse_train_dur/
        pulse_train_rep_int/pulse_train_rep_dur do not: there is currently no way for one
        interleaved sequence to internally repeat its own pulse a number of times before handing
        off to the next one. Only relevant with more than one sequence -- a single sequence still
        gets its full pulse train via _define_pulse_train().

        Parameters:
            sequences (Sequence or list(Sequence)): One sequence, or a list of sequences to
                interleave. Each sequence contains, amongst other things:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer slot(s))
            duration_ms (float): Only used when interleaving (more than one sequence) -- total
                duration [ms] the alternating group repeats for.
        """

        if isinstance(sequences, Sequence):
            sequences = [sequences]

        for sequence in sequences:
            self._assert_ready_to_send(sequence)

        get_logger().info('Validating sequence...')

        for seq in sequences:
            get_logger().debug(
                'Sequence with the following parameters is validated before sending: \n ' +
                '%s', seq)

            error_messages = self.validate_sequence(seq)

            if error_messages:
                for error in error_messages:
                    get_logger().critical(error)
                sys.exit('(Multiple) error(s) found when validating sequence, see log file.')

        get_logger().info('Sending sequence...')
        if self.is_connected():

            pulses = [self._define_pulse_group(seq) for seq in sequences]
            seq0 = sequences[0]

            if len(sequences) == 1:
                pulse, phases = pulses[0]

                # define pulse train
                pulse_train_seq, pulse_train_delay = self._define_pulse_train(seq0, pulse)

                # Define pulse train repetition
                # number of executions of one pulse train
                n_pulse_train_rep = math.floor(seq0.pulse_train_rep_dur / seq0.pulse_train_rep_int)
            else:
                get_logger().debug(
                    f'{len(sequences)} sequences are sent, indicating they are interleaved.')

                # One pulse per sequence, not a repeated pulse train per sequence -- unlike the
                # N=1 branch above (_define_pulse_train()), each interleaved sequence's own
                # pulse_train_dur/pulse_train_rep_int/pulse_train_rep_dur have no effect here
                # (see this method's own docstring). Theoretically possible to support, but not
                # yet designed: would need a real decision on what "interleaved pulse trains"
                # (as opposed to interleaved single pulses) should actually mean here.
                pulse_train_seq = [pulse for pulse, _ in pulses]
                phases = [seq_phases for _, seq_phases in pulses]
                pulse_train_delay = 0

                # One round of the alternating group takes as long as every sequence's own
                # pulse_rep_int summed -- each sequence's pulse occupies that whole time slot
                # (pulse_dur active, then its own trailing delay), not pulse_train_dur (which
                # would describe a repeated train this pulse never actually fires here).
                total_pulse_rep_int_ms = sum(seq.pulse_rep_int for seq in sequences)
                n_pulse_train_rep = math.floor(duration_ms / total_pulse_rep_int_ms)

            # Apply ramping -- read from seq0 only. Ramping is set once on the generator as a
            # whole (rising/falling PulseRamp), not per pulse train, so it's an all-or-nothing
            # property of the entire interleaved group, not something each interleaved sequence
            # can configure independently: seq0's pulse_ramp_shape/pulse_ramp_dur decide it for
            # every sequence in this send_sequence() call, and any other sequence's own ramp
            # settings are silently ignored.
            rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                         'Rectangular - no ramping')
            if seq0.pulse_ramp_shape != rect_ramp:
                self._apply_ramping(seq0)
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

            # Upload the sequence
            self.gen.sendSequence(seq0.seq_num, pulse_train_seq)

            self.register_sent_sequence(seq0.seq_num, pulse_train_seq, n_pulse_train_rep,
                                        pulse_train_delay, phases)

        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(sequences[0].driving_sys.connect_info)
            self.send_sequence(sequences, duration_ms)

    def _define_pulse_group(self, sequence):
        """
        Defines the combined pulse for every transducer slot of one sequence, concatenating each
        slot's own fully-expanded (per-element) amplitude/frequency arrays -- uniformly, whether
        there's 1 slot or several. N is never hardcoded -- however many slots this sequence
        actually has is how many this loops over.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.

        Returns:
            tuple: (unifus.Pulse, list) -- the defined pulse and its phases.
        """

        pulse = unifus.Pulse(self.n_channels, 1, 1)  # n phases, n frequencies, n amplitudes

        # duration in ms, delay in ms
        pulse.setDuration(sequence.pulse_dur,
                          round(sequence.pulse_rep_int - sequence.pulse_dur, 1))

        slots = sequence.slots

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
            # -- applied uniformly, whether this sequence has 1 slot or several.
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
                                                   slot.transducer.natural_foc,
                                                   slot.dephasing_degree)
                phases = phases + computed_phases

        # set phase offset for all channels (angle in [0,360] degrees)
        pulse.setPhases(phases)

        # set frequency for all channels, in Hz
        pulse.setFrequencies(freqs)

        # set amplitude for all channels in percent (of max amplitude)
        pulse.setAmplitudes(ampls)

        return pulse, phases

    def wait_for_trigger(self, sequences, duration_ms=0, debug_info=True):
        """
        Activates the listener on the IGT ultrasound driving system to wait for the trigger to
        execute the previously sent sequence(s). When interleaving, the ramp-transient timing
        this computes is taken from only the first sequence given, matching send_sequence()'s
        own "ramping is a whole-group setting, not per interleaved sequence" behavior.

        Parameters:
            sequences (Sequence or list(Sequence)): Same sequence(s) already passed to
                send_sequence().
            duration_ms (float): Same value already passed to send_sequence().
            debug_info (bool): Whether to compute and set additional execution flags.
        """

        if isinstance(sequences, Sequence):
            sequences = [sequences]
        seq0 = sequences[0]

        if self.is_connected():
            if self.is_sequence_sent(seq0.seq_num):
                try:
                    # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                    # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                    # To use trigger, add one of unifus::ExecFlag::Trigger*
                    # Flags to disable checking the current limit
                    exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                                  unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

                    if debug_info:
                        ramp_transient_t = 0
                        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                                     'Rectangular - no ramping')
                        # seq0 only -- ramping is a whole-group setting for send_sequence(), not
                        # something each interleaved sequence configures independently (see its
                        # own docstring), so this timing must be based on the same sequence that
                        # actually decided it.
                        if seq0.pulse_ramp_dur > 0 and (seq0.pulse_ramp_shape != rect_ramp):
                            ramp_transient_t = float(
                                get_config_value(
                                    get_logger(), config, 'Equipment.Manufacturer.IGT',
                                    'Min. time in between ramping up and down [ms]',
                                    0.070))  # [ms]

                        measure_ch_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureChannels [ms]', 4.570))

                        measure_boards_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureBoards [ms]', 0.035))

                        measure_time_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureTimings [ms]', 0.001))
                        if seq0.pulse_dur > measure_ch_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureChannels

                        elif seq0.pulse_dur >= measure_boards_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureBoards

                        elif seq0.pulse_dur >= measure_time_level + ramp_transient_t:  # [ms]:
                            exec_flags |= unifus.ExecFlag.MeasureTimings  # or NONE

                    sent_seq_info = self.sent_seqs.get(seq0.seq_num, {})
                    n_pulse_train_rep = sent_seq_info.get('n_pulse_train_rep')
                    pulse_train_delay = sent_seq_info.get('pulse_train_delay')

                    # Determining trigger flag
                    seq_trigger = get_config_value(get_logger(), config, 'Trigger', 'Option.seq',
                                                   'TriggerOnePulseTrain')
                    ptr_trigger = get_config_value(get_logger(), config, 'Trigger', 'Option.ptr',
                                                   'TriggerWholeProtocol')
                    if seq0.trigger_option == seq_trigger:
                        exec_flags |= unifus.ExecFlag.TriggerOneSequence
                        n_pulse_train_rep = seq0.n_triggers
                        pulse_train_delay = 0  # trigger will determine delay

                    elif seq0.trigger_option == ptr_trigger:
                        exec_flags |= unifus.ExecFlag.TriggerAllSequences

                    else:
                        message = (f'Trigger option {seq0.trigger_option} is not identical to ' +
                                   f'implemented trigger options: {seq0.get_trigger_options()}.')
                        get_logger().critical(message)
                        sys.exit(message)

                    get_logger().info(f"Waiting for a total of {seq0.n_triggers} trigger(s)...")

                    self.gen.prepareSequence(seq0.seq_num, n_pulse_train_rep, pulse_train_delay,
                                             exec_flags)

                    self.gen.startSequence()

                except Exception as why:
                    message = f"Exception: {why}"
                    get_logger().critical(message)
                    sys.exit(message)
            else:
                get_logger().warning(
                    'The sequence has to be sent first using send_sequence() before ' +
                    'the driving system can wait for a trigger.')
                get_logger().warning('Sending sequence...')

                self.send_sequence(sequences, duration_ms)
                self.wait_for_trigger(sequences, duration_ms, debug_info)
        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(seq0.driving_sys.connect_info)
            self.send_sequence(sequences, duration_ms)
            self.wait_for_trigger(sequences, duration_ms, debug_info)

    def wait_for_trigger_result(self, timeout_s=5.0):
        """
        Waits (blocking) for a previously armed triggered sequence to finish, and exits if the
        driving system reports its execution failed.

        wait_for_trigger() only arms the sequence to fire on the external trigger and returns
        immediately -- it does not wait for or observe the actual execution result (see GitHub
        issue #112). Call this once the external trigger is expected to have fired (or with a
        generous timeout) to check that the driving system actually reported success.

        Parameters:
            timeout_s (float): How long to wait for the triggered execution to finish, in
            seconds.
        """

        self.listener.wait_sequence(timeout_s)

        if self.listener.exec_error_code is not None:
            message = ('Sequence execution failed on the driving system (error ' +
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

    def execute_sequence(self, sequences, duration_ms=0, debug_info=True):
        """
        Executes the previously sent sequence(s) on the IGT ultrasound driving system. When
        interleaving, the ramp-transient timing this computes is taken from only the first
        sequence given, matching send_sequence()'s own "ramping is a whole-group setting, not
        per interleaved sequence" behavior.

        Parameters:
            sequences (Sequence or list(Sequence)): Same sequence(s) already passed to
                send_sequence().
            duration_ms (float): Same value already passed to send_sequence().
            debug_info (bool): Whether to compute and set additional execution flags.
        """

        if isinstance(sequences, Sequence):
            sequences = [sequences]
        seq0 = sequences[0]

        max_press = get_config_value(get_logger(), config, 'Power',
                                     'Maximum pressure allowed in free water [MPa]',
                                     'Not found')

        get_logger().debug(f'Maximum allowed pressure is: {max_press} MPa')

        get_logger().info('Executing sequence...')

        if self.is_connected():
            if self.is_sequence_sent(seq0.seq_num):
                try:
                    # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                    # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                    # To use trigger, add one of unifus::ExecFlag::Trigger*
                    # Flags to disable checking the current limit
                    exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                                  unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

                    if debug_info:
                        ramp_transient_t = 0
                        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                                     'Rectangular - no ramping')
                        # seq1 only -- ramping is a whole-group setting for send_sequence(), not
                        # something each interleaved sequence configures independently (see its
                        # own docstring), so this timing must be based on the same sequence that
                        # actually decided it.
                        if seq0.pulse_ramp_dur > 0 and seq0.pulse_ramp_shape != rect_ramp:
                            ramp_transient_t = float(
                                get_config_value(
                                    get_logger(), config, 'Equipment.Manufacturer.IGT',
                                    'Min. time in between ramping up and down [ms]',
                                    0.070))  # [ms]

                        measure_ch_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureChannels [ms]', 4.570))

                        measure_boards_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureBoards [ms]', 0.035))

                        measure_time_level = float(
                            get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureTimings [ms]', 0.001))
                        if seq0.pulse_dur > measure_ch_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureChannels

                        elif seq0.pulse_dur >= measure_boards_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureBoards

                        elif seq0.pulse_dur >= measure_time_level + ramp_transient_t:  # [ms]:
                            exec_flags |= unifus.ExecFlag.MeasureTimings  # or NONE

                    sent_seq_info = self.sent_seqs.get(seq0.seq_num, {})
                    self.gen.prepareSequence(seq0.seq_num, sent_seq_info.get('n_pulse_train_rep'),
                                             sent_seq_info.get('pulse_train_delay'), exec_flags)

                    self.gen.startSequence()
                    self.listener.wait_sequence(sent_seq_info.get('total_sequence_duration_ms') /
                                                1000.0)

                    if self.listener.exec_error_code is not None:
                        message = ('Sequence execution failed on the driving system (error ' +
                                   f'code: {self.listener.exec_error_code}). Potentially no ' +
                                   'ultrasound emitted.')
                        get_logger().critical(message)
                        sys.exit(message)

                except Exception as why:
                    message = f"Exception: {why}"
                    get_logger().critical(message)
                    sys.exit(message)
            else:
                get_logger().warning(
                    'The sequence has to be sent first using send_sequence() before ' +
                    'the driving system can execute a sequence.')
                get_logger().warning('Sending sequence...')

                self.send_sequence(sequences, duration_ms)
                self.execute_sequence(sequences, duration_ms, debug_info)

        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(seq0.driving_sys.connect_info)
            self.send_sequence(sequences, duration_ms)
            self.execute_sequence(sequences, duration_ms, debug_info)

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

    def _define_pulse_train(self, sequence, pulse):
        """
        Defines the pulse train for the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
            pulse (unifus.Pulse): The defined pulse.

        Returns:
            seq: list of pulses representing a pulse train
            pulse_train_delay: pulse train delay in miliseconds

        """

        # number of executions of one pulse train
        n_pulse_train = math.floor(sequence.pulse_train_dur / sequence.pulse_rep_int)

        # Define a complete sequence
        seq = []
        seq += n_pulse_train * [pulse]

        # milliseconds between pulse trains
        pulse_train_delay = sequence.pulse_train_rep_int - sequence.pulse_train_dur

        return seq, pulse_train_delay

    def _set_phases(self, pulse, focus, steer_info, natural_foc, dephasing_degree):
        """
        Gets the phases for the IGT ultrasound driving system.

        Parameters:
            pulse (unifus.Pulse): The defined pulse.
            focus (float): The focus value wrt the middle of the transducer bowl [mm].
            steer_info (str): Path to the steer information.
            natural_foc (float): The natural focus value [mm] used to calculate target focus.
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

            # Calculate target focus with respect to natural focus: + is before natural focus,
            # - is after natural focus
            aim_wrt_natural_focus = natural_foc - focus

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

    def _apply_ramping(self, sequence):
        """
        Applies ramping on the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
        """

        # Use best temporal resolution for pulse ramping [ms]
        min_ramp_temp_res = float(get_config_value(
            get_logger(), config, 'Equipment.Manufacturer.IGT',
            'Min. temporal ramping resolution [ms]',
            0.005))  # [ms]
        max_ramp_steps = float(get_config_value(get_logger(), config, 'Equipment.Manufacturer.IGT',
                                                'Max. amount of ramping steps', 1023))

        ramp_n_steps = int(sequence.pulse_ramp_dur/min_ramp_temp_res)
        if ramp_n_steps > max_ramp_steps:
            min_ramp_temp_res = sequence.pulse_ramp_dur/max_ramp_steps

        # Note: ramp up and ramp down order are the other way around
        # ramp up descends, ramp down ascends
        ampl_ramp = self._get_ramping_amplitude(sequence, min_ramp_temp_res)

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

    def _get_ramping_amplitude(self, sequence, pulse_ramp_temp_res):
        """
        Gets the ramping array that has to be applied to the amplitude for the IGT ultrasound
        driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
            pulse_ramp_temp_res (float): temporal resolution for pulse ramping [ms].

        Returns:
            tuple: A tuple containing the amplitude ramping and step duration.
        """

        lin_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.lin', 'Linear')
        tuk_ramp = get_config_value(get_logger(), config, 'Ramp', 'Option.tuk', 'Tukey')
        if sequence.pulse_ramp_shape == lin_ramp:  # Linear ramping
            # amount of points where ramping is applied
            n_points = math.floor(sequence.pulse_ramp_dur/pulse_ramp_temp_res)
            ampl_ramp = np.linspace(0, 1, n_points)

        elif sequence.pulse_ramp_shape == tuk_ramp:  # Tukey ramping
            # amount of points where ramping is applied
            n_points = math.floor(sequence.pulse_ramp_dur/pulse_ramp_temp_res)
            alpha = 1
            x = np.linspace(0, alpha/2, n_points)
            ampl_ramp = np.zeros(n_points)
            for i in range(n_points):
                ampl_ramp[i] = 0.5 * (1 + math.cos((2*math.pi/alpha) * (x[i] - alpha/2)))

        return ampl_ramp
