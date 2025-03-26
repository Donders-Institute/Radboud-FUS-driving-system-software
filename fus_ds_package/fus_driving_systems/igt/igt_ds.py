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
If you use this kit in your research or project, please include the following attribution:
Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 1.0),
https://github.com/Donders-Institute/Radboud-FUS-measurement-kit
"""

# Basis packages
import os
import sys
import time

# Miscellaneous packages
import faulthandler
import math

import numpy as np

import pandas as pd
import pkg_resources

# Own packages
from fus_driving_systems import control_driving_system as ds

from fus_driving_systems.igt.utils import ExecListener
from fus_driving_systems.igt import transducerXYZ
from fus_driving_systems.igt import unifus
from fus_driving_systems.utils import get_config_value

# Access the logger
from fus_driving_systems.config.logging_config import logger
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
            log_dir = get_config_value(logger, config, 'Logging', 'Temporary logging path',
                                       'C:\\Temp')

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        filename = get_config_value(logger, config, 'Logging', 'Filename faulthandler',
                                    'faulthandler_output.log')

        fault_handler_path = os.path.join(log_dir, filename)

        with open(fault_handler_path, "w") as f:
            faulthandler.enable(file=f)

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

        return seq_num in self.sent_seqs.keys()

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

        wait_time_ms = float(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                              'Wait time before reponsive [ms]', 100))
        self.sent_seqs[seq_num]['total_sequence_duration_ms'] = (total_sequence_duration_ms +
                                                                 wait_time_ms)

        logger.debug(f"Stored sequence {seq_num}: {self.sent_seqs[seq_num]}")

    def connect(self, connect_info, log_dir=None, log_name=None, attempt=0):
        """
        Connects to the IGT ultrasound driving system.

        Parameters:
            connect_info (str): Path with IGT driving system-specific configuration file.
        """

        logger.info('Connecting...')

        if log_dir is None:
            log_dir = get_config_value(logger, config, 'Logging', 'Temporary logging path',
                                       'C:\\Temp')

        if log_name is None:
            log_name = get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                        'Default log filename prefix', 'standalone_igt')

        # When no connection, it is assumed that all sent sequences aren't available (anymore)
        self.sent_seqs = {}
        max_attempts = int(get_config_value(logger, config, 'General',
                                            'Maximum reconnection attempts', 5))

        try:
            # Establish connection with driving system
            logger.debug('Before unifus.FUSSystem....')
            self.fus = unifus.FUSSystem()
            logger.debug('After unifus.FUSSystem....')
        except Exception as e:
            message = f'Error initializing FUSSystem: {e}'
            logger.critical(message)
            sys.exit(message)

        try:
            suffix = get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                      'Default log filename suffix', '_igt_ds_log')
            unifus.setLogPath(log_dir, log_name + suffix)
            unifus.setLogLevel(unifus.LogLevel.Debug)

            logger.debug('After setting logging....')
        except Exception as e:
            message = f"Error setting up logging: {e}"
            logger.error(message)

        try:
            # Update the name of your configuration file
            igt_config_path = pkg_resources.resource_filename('fus_driving_systems', connect_info)
            logger.debug(f'igt_config_path: {igt_config_path} found....')
            if igt_config_path != '':
                self.fus.loadConfig(igt_config_path)
                logger.debug('After loadConfig....')
            else:
                message = f"Configuration file {igt_config_path} doesn't exist."
                logger.critical(message)
                sys.exit(message)
        except Exception as e:
            message = f"Error loading configuration: {e}"
            logger.critical(message)
            sys.exit(message)

        try:
            # Create and register an event listener
            self.listener = ExecListener()
            self.fus.registerListener(self.listener)
            logger.debug('After listener....')

            self.fus.connect()
            self.listener.waitConnection()
            logger.debug('After waitConnection()....')
        except Exception as e:
            logger.error(f"Error during connection or listener registration: {e}")

            if attempt < max_attempts:
                logger.warning('Try to disconnect and reconnect...')
                self.disconnect()
                self.connect(connect_info, log_dir, log_name, attempt=attempt+1)
            else:
                message = f'Maximum amount of {max_attempts} for reconnecting is reached. Exit.'
                logger.critical(message)
                sys.exit(message)

        try:
            if self.fus.isConnected():
                self.connected = True
                logger.debug('Driving system is connected.')

                self.gen = self.fus.gen()
                self.n_channels = self.gen.getParam(unifus.GenParam.ChannelCount)
                logger.debug("Generator: %s channels", self.n_channels)
            else:
                self.connected = False
                logger.warning("Error: connection failed.")

                if attempt < max_attempts:
                    logger.warning('Try to disconnect and reconnect...')
                    self.disconnect()
                    self.connect(connect_info, log_dir, log_name, attempt=attempt+1)
                else:
                    message = f'Maximum amount of {max_attempts} for reconnecting is reached. Exit.'
                    logger.critical(message)
                    sys.exit(message)

        except Exception as e:
            message = f"Error after connection check: {e}"
            logger.critical(message)
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

        min_pulse_dur = float(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                               'Min. pulse duration [ms]', 0.001))
        if sequence.pulse_dur < min_pulse_dur:  # [ms]:
            error_messages.append('Pulse duration is not allowed to be smaller than 1 us.')

        min_pulse_rep_int = float(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                                   'Min. pulse rep. interval [ms]', 0.170))
        if sequence.pulse_rep_int < min_pulse_rep_int:  # [ms]
            error_messages.append('Pulse repetition interval is not allowed to be smaller than' +
                                  ' 170 us.')

        min_time_between_ramps = float(
            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                             'Min. time in between ramping up and down [ms]', 0.070))

        rect_ramp = get_config_value(logger, config, 'Ramp', 'Option.rect',
                                     'Rectangular - no ramping')
        if sequence.pulse_ramp_dur > 0 and (sequence.pulse_ramp_shape != rect_ramp):
            if sequence.pulse_ramp_dur > sequence.pulse_dur/2 - min_time_between_ramps/2:
                error_messages.append('When applying ramping, there needs to be at least ' +
                                      '70 us between ramping up and down')
        if sequence.ampl is None:
            error_messages.append("Intensity parameter may be set incorrectly. Amplitude is None.")

        n_pulses = sequence.pulse_train_dur/sequence.pulse_rep_int
        max_n_pulses = int(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                            'Max. pulses in pulse train', 64))
        if n_pulses > max_n_pulses:
            error_messages.append("The maximum amount of pulses within a pulse train is " +
                                  f"{max_n_pulses}. Currently, the amount is {n_pulses}.")

        return error_messages

    def send_sequence(self, seq1, seq2=None, seq3=None, seq4=None, duration_ms=0):
        """
        Validates and sends an ultrasound sequence to the IGT ultrasound driving system.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

        logger.info('Validating sequence...')

        seqs = [seq1]
        if seq2 is not None:
            seqs = [seq1, seq2]

            if seq3 is not None and seq4 is not None:
                seqs = [seq1, seq2, seq3, seq4]

        for seq in seqs:
            logger.debug('Sequence with the following parameters is validated before sending: \n '
                         + '%s', seq)

            error_messages = self.validate_sequence(seq)

            if error_messages:
                for error in error_messages:
                    logger.critical(error)
                sys.exit('(Multiple) error(s) found when validating sequence, see log file.')

        logger.info('Sending sequence...')
        if self.is_connected():

            # define pulse
            if seq2 is None:
                pulse, phases = self._define_pulse(seq1)
            else:
                logger.info('Two sequences are sent indicating two transducers are connected.')
                logger.info('Timing parameters will be based on first sequence.')
                pulse, phases = self._define_two_tran_slots(seq1, seq2)

                if seq3 is not None and seq4 is not None:
                    pulse2, phases2 = self._define_two_tran_slots(seq3, seq4)

                    # Test if it will not break the SonoRover One code
                    phases = [phases, phases2]

            if seq3 is not None and seq4 is not None:
                pulse_train_seq = [pulse, pulse2]
                pulse_train_delay = 0

                total_pulse_rep_int_ms = seq1.pulse_train_dur + seq3.pulse_train_dur
                n_pulse_train_rep = math.floor(duration_ms / total_pulse_rep_int_ms)

            else:
                # define pulse train
                pulse_train_seq, pulse_train_delay = self._define_pulse_train(seq1, pulse)

                # Define pulse train repetition
                # number of executions of one pulse train
                n_pulse_train_rep = math.floor(seq1.pulse_train_rep_dur / seq1.pulse_train_rep_int)

            # Apply ramping
            average_ampl = sum(seq1.ampl) / len(seq1.ampl)
            rect_ramp = get_config_value(logger, config, 'Ramp', 'Option.rect',
                                         'Rectangular - no ramping')
            if seq1.pulse_ramp_shape != rect_ramp and average_ampl > 0:
                self._apply_ramping(seq1)
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
            self.gen.sendSequence(seq1.seq_num, pulse_train_seq)

            self.register_sent_sequence(seq1.seq_num, pulse_train_seq, n_pulse_train_rep,
                                        pulse_train_delay, phases)

        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(seq1.driving_sys.connect_info)
            self.send_sequence(seq1, seq2)

    def _define_two_tran_slots(self, seq1, seq2):
        """
        Validates and sends an ultrasound sequence to both transducer slots of the IGT ultrasound
        driving system.

        Parameters:
            seq1, seq2 (Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

        pulse = unifus.Pulse(self.n_channels, 1, 1)  # n phases, n frequencies, n amplitudes

        # duration in ms, delay in ms
        pulse.setDuration(seq1.pulse_dur, round(seq1.pulse_rep_int - seq1.pulse_dur, 1))

        # frequencies have to be set first before phases can be computed
        # determine  per sequence
        phases = []
        freqs = []
        ampls = []
        for seq in [seq1, seq2]:
            if len(seq.ampl) == 1:
                ampls = ampls + [seq.ampl] * seq.transducer.elements
            else:
                ampls = ampls + seq.ampl

            oper_freq_hz = int(seq.oper_freq * 1e3)
            tran_freq = [oper_freq_hz] * seq.transducer.elements
            freqs = freqs + tran_freq

            pulse.setFrequencies(tran_freq)
            if seq.dephasing_degree is not None and (len(seq.dephasing_degree) ==
                                                     seq.transducer.elements):
                logger.info('Phases are overridden by phases set at dephasing_degree: ' +
                            f'{seq.dephasing_degree}')
                phases = phases + seq.dephasing_degree
            else:
                computed_phases = self._set_phases(pulse, seq.focus_wrt_mid_bowl,
                                                   seq.transducer.steer_info,
                                                   seq.transducer.natural_foc,
                                                   seq.dephasing_degree)
                phases = phases + computed_phases

        # set phase offset for all channels (angle in [0,360] degrees)
        pulse.setPhases(phases)

        # set frequency for all channels, in Hz
        pulse.setFrequencies(freqs)

        # set amplitude for all channels in percent (of max amplitude)
        pulse.setAmplitudes(ampls)

        return pulse, phases

    def wait_for_trigger(self, seq1, seq2=None, seq3=None, seq4=None, duration_ms=0, debug_info=False):
        """
        Activates the listener on the IGT ultrasound driving system to wait for the trigger to
        execte the previously sent sequence.
        """

        logger.info('Waiting for trigger...')

        if self.is_connected():
            if self.is_sequence_sent(seq1.seq_num):
                try:
                    # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                    # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                    # To use trigger, add one of unifus::ExecFlag::Trigger*
                    # Flags to disable checking the current limit
                    exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                                  unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

                    if debug_info:
                        ramp_transient_t = 0
                        rect_ramp = get_config_value(logger, config, 'Ramp', 'Option.rect',
                                                     'Rectangular - no ramping')
                        if seq1.pulse_ramp_dur > 0 and (seq1.pulse_ramp_shape != rect_ramp):
                            ramp_transient_t = float(
                                get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                                 'Min. time in between ramping up and down [ms]',
                                                 0.070))  # [ms]

                        measure_ch_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureChannels [ms]', 4.570))

                        measure_boards_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureBoards [ms]', 0.035))

                        measure_time_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureTimings [ms]', 0.001))
                        if seq1.pulse_dur > measure_ch_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureChannels

                        elif seq1.pulse_dur >= measure_boards_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureBoards

                        elif seq1.pulse_dur >= measure_time_level + ramp_transient_t:  # [ms]:
                            exec_flags |= unifus.ExecFlag.MeasureTimings  # or NONE

                    sent_seq_info = self.sent_seqs.get(seq1.seq_num, {})
                    n_pulse_train_rep = sent_seq_info.get('n_pulse_train_rep')
                    pulse_train_delay = sent_seq_info.get('pulse_train_delay')

                    # Determining trigger flag
                    seq_trigger = get_config_value(logger, config, 'Trigger', 'Option.seq',
                                                   'TriggerSequence')
                    ptr_trigger = get_config_value(logger, config, 'Trigger', 'Option.ptr',
                                                   'TriggerOnePulseTrainRepetition')
                    if seq1.trigger_option == seq_trigger:
                        exec_flags |= unifus.ExecFlag.TriggerOneSequence
                        n_pulse_train_rep = seq1.n_triggers
                        pulse_train_delay = 0  # trigger will determine delay

                    elif seq1.trigger_option == ptr_trigger:
                        exec_flags |= unifus.ExecFlag.TriggerAllSequences

                    else:
                        message = (f'Trigger option {seq1.trigger_option} is not identical to ' +
                                   f'implemented trigger options: {seq1.get_trigger_options()}.')
                        logger.critical(message)
                        sys.exit(message)

                    self.gen.prepareSequence(seq1.seq_num, n_pulse_train_rep, pulse_train_delay,
                                             exec_flags)

                    self.gen.startSequence()

                except Exception as why:
                    message = f"Exception: {why}"
                    logger.critical(message)
                    sys.exit(message)
            else:
                logger.warning('The sequence has to be sent first using send_sequence() before ' +
                               'the driving system can wait for a trigger.')
                logger.warning('Sending sequence...')

                self.send_sequence(seq1, seq2, seq3, seq4, duration_ms)
                self.wait_for_trigger(seq1, seq2, seq3, seq4, duration_ms)
        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(seq1.driving_sys.connect_info)
            self.send_sequence(seq1, seq2, seq3, seq4, duration_ms)
            self.wait_for_trigger(seq1, seq2, seq3, seq4, duration_ms)

    def execute_sequence(self, seq1, seq2=None, seq3=None, seq4=None, duration_ms=0, debug_info=False):
        """
        Executes the previously sent sequence on the IGT ultrasound driving system.
        """

        logger.info('Executing sequence...')

        if self.is_connected():
            if self.is_sequence_sent(seq1.seq_num):
                try:
                    # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the
                    # exec_flags argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
                    # To use trigger, add one of unifus::ExecFlag::Trigger*
                    # Flags to disable checking the current limit
                    exec_flags = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                                  unifus.ExecFlag.DisableMonitoringChannelCurrentOut)

                    if debug_info:
                        ramp_transient_t = 0
                        rect_ramp = get_config_value(logger, config, 'Ramp', 'Option.rect',
                                                     'Rectangular - no ramping')
                        if seq1.pulse_ramp_dur > 0 and seq1.pulse_ramp_shape != rect_ramp:
                            ramp_transient_t = float(
                                get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                                 'Min. time in between ramping up and down [ms]',
                                                 0.070))  # [ms]

                        measure_ch_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureChannels [ms]', 4.570))

                        measure_boards_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureBoards [ms]', 0.035))

                        measure_time_level = float(
                            get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                             'Pulse dur. flag level MeasureTimings [ms]', 0.001))
                        if seq1.pulse_dur > measure_ch_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureChannels

                        elif seq1.pulse_dur >= measure_boards_level + ramp_transient_t:  # [ms]
                            exec_flags |= unifus.ExecFlag.MeasureBoards

                        elif seq1.pulse_dur >= measure_time_level + ramp_transient_t:  # [ms]:
                            exec_flags |= unifus.ExecFlag.MeasureTimings  # or NONE

                    sent_seq_info = self.sent_seqs.get(seq1.seq_num, {})
                    self.gen.prepareSequence(seq1.seq_num, sent_seq_info.get('n_pulse_train_rep'),
                                             sent_seq_info.get('pulse_train_delay'), exec_flags)

                    self.gen.startSequence()
                    self.listener.waitSequence(sent_seq_info.get('total_sequence_duration_ms') /
                                               1000.0)

                except Exception as why:
                    message = f"Exception: {why}"
                    logger.critical(message)
                    sys.exit(message)
            else:
                logger.warning('The sequence has to be sent first using send_sequence() before ' +
                               'the driving system can execute a sequence.')
                logger.warning('Sending sequence...')

                self.send_sequence(seq1, seq2, seq3, seq4, duration_ms)
                self.execute_sequence(seq1, seq2, seq3, seq4, duration_ms)

        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(seq1.driving_sys.connect_info)
            self.send_sequence(seq1, seq2, seq3, seq4, duration_ms)
            self.execute_sequence(seq1, seq2, seq3, seq4, duration_ms)

    def disconnect(self):
        """
        Disconnects from the IGT ultrasound driving system.
        """

        logger.info('Disconnecting...')

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
                logger.info("Disconnected.")
            else:
                logger.error("Failed to disconnect")
                self.connected = True

    def _define_pulse(self, sequence):
        """
        Defines the pulse for the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.

        Returns:
            unifus.Pulse: The defined pulse.
        """

        pulse = unifus.Pulse(self.n_channels, 1, 1)  # n phases, n frequencies, n amplitudes

        # duration in ms, delay in ms
        pulse.setDuration(sequence.pulse_dur, round(sequence.pulse_rep_int - sequence.pulse_dur, 1))

        # set same frequency for all channels = 250KHz, in Hz
        oper_freq_hz = int(sequence.oper_freq * 1e3)
        pulse.setFrequencies([oper_freq_hz])

        # set same amplitude for all channels in percent (of max amplitude)
        if sequence.ampl is not None:
            pulse.setAmplitudes(sequence.ampl)
        else:
            message = "Power parameter may be set incorrectly. Amplitude is None."
            logger.critical(message)
            sys.exit(message)

        # set same phase offset for all channels (angle in [0,360] degrees)
        if sequence.dephasing_degree is not None and len(sequence.dephasing_degree) == sequence.transducer.elements:
            logger.info('Phases are overridden by phases set at dephasing_degree: ' +
                        f'{sequence.dephasing_degree}')
            phases = sequence.dephasing_degree
        else:
            phases = self._set_phases(pulse, sequence.focus_wrt_mid_bowl,
                                      sequence.transducer.steer_info,
                                      sequence.transducer.natural_foc, sequence.dephasing_degree)
        pulse.setPhases(phases)

        return pulse, phases

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
            None = no dephasing. If the list is equal to the number of elements, the phases based on
            the focus are overridden.

        Returns:
            list: List of phases.
        """

        # transducer has been chosen where phases are calculated based on phase law
        package_name = get_config_value(logger, config, 'General', 'Package name',
                                        'fus_driving_systems')
        if steer_info.endswith('.ini'):

            trans = transducerXYZ.Transducer()
            ini_path = pkg_resources.resource_filename(package_name, steer_info)
            if not trans.load(ini_path):
                message = f'Error: can not load the transducer definition from {ini_path}'
                logger.critical(message)
                sys.exit(message)

            # Calculate target focus with respect to natural focus: + is before natural focus,
            # - is after natural focus
            aim_wrt_natural_focus = natural_foc - focus

            # Aim n mm away from the natural focal spot, on main axis (Z)
            phases = trans.computePhases(pulse, (0, 0, aim_wrt_natural_focus), focus,
                                         dephasing_degree)

        else:
            # Import excel file containing phases per focal depth
            excel_path = pkg_resources.resource_filename(package_name, steer_info)

            logger.debug('Extract phase information from %s', excel_path)

            if os.path.exists(excel_path):
                data = pd.read_excel(excel_path, engine='openpyxl')

                # Make sure both values have the same amount of decimals
                focus = round(focus, 1)
                match_row = data.loc[data['Distance'] == focus]

                if match_row.empty:
                    message = (f'No focus in transducer phases file {excel_path}' +
                               f' corresponds with {focus}')
                    logger.critical(message)
                    sys.exit(message)

                elif len(match_row) > 1:
                    message = (f'Duplicate foci {focus} found in transducer phases file ' +
                               f'{excel_path}. First found entry will be used.')
                    logger.error(message)

                    match_row = match_row[0]

                # Retrieve phases dependent of number of channels
                phases = [match_row.iloc[0].iloc[1:int(self.n_channels)+1]].to_list()

                if dephasing_degree is not None:
                    if len(dephasing_degree) > 1:
                        logger.warning('Too few or too many entries given at dephasing_degree.' +
                                       ' Only the first one is now used for dephasing purposes.')

                    dephasing_degree = dephasing_degree[0]
                    # determine n elements to dephase in one cycle
                    nth_elem = round(360/dephasing_degree)
                    dephasing_elem = 0
                    for i in range(len(phases)):
                        # Add chosen degrees to dephase signal
                        phases[i] = phases[i] + dephasing_degree*dephasing_elem

                        dephasing_elem = dephasing_elem + 1
                        if dephasing_elem == nth_elem:
                            dephasing_elem = 0

                phases_str = ', '.join([format(x, '.2f') for x in phases])
                logger.debug(f'Computed phases for set focus of {focus}: {phases_str}')

            else:
                message = ("Pipeline is cancelled. The following direction cannot be found: " +
                           f"{excel_path}")
                logger.critical(message)
                sys.exit(message)

        return phases

    def _apply_ramping(self, sequence):
        """
        Applies ramping on the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
        """

        # Use best temporal resolution for pulse ramping [ms]
        min_ramp_temp_res = float(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
                                                   'Min. temporal ramping resolution [ms]',
                                                   0.005))  # [ms]
        max_ramp_steps = float(get_config_value(logger, config, 'Equipment.Manufacturer.IGT',
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

        lin_ramp = get_config_value(logger, config, 'Ramp', 'Option.lin', 'Linear')
        tuk_ramp = get_config_value(logger, config, 'Ramp', 'Option.tuk', 'Tukey')
        shota_ramp = get_config_value(logger, config, 'Ramp', 'Option.shota', 'Shota')
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

        elif sequence.pulse_ramp_shape == shota_ramp:
            # amount of points where ramping is applied
            n_points = math.floor(sequence.pulse_ramp_dur/pulse_ramp_temp_res)
            pulse_ramp_dur_s = sequence.pulse_ramp_dur / 1000
            f = 1 / (2 * pulse_ramp_dur_s)   # [Hz]
            x = np.linspace(0, pulse_ramp_dur_s, n_points)
            ampl_ramp = np.zeros(n_points)
            for i in range(n_points):
                ampl_ramp[i] = 0.5 * (1 + math.sin(2*math.pi*f*x[i] - math.pi/2))

        return ampl_ramp
