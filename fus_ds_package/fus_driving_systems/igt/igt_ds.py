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
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 0.8),
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

# Access the logger
from fus_driving_systems.config.logging_config import logger


class IGT(ds.ControlDrivingSystem):
    """
    Class for an IGT ultrasound driving system, inheriting from the abstract class DrivingSystem.

    Attributes:
        connected (bool): Indicates whether the system is connected.
        gen: Generator object.
        fus: FUSSystem object for the IGT ultrasound driving system.
        listener: ExecListener object for event listening.
        n_channels (int): Number of channels.
        total_sequence_duration_ms (float): Total duration of the sequence in milliseconds.
    """

    def __init__(self):
        """
        Initializes the IGT object.
        """
        super().__init__()

        with open("C:/Temp/faulthandler_output.log", "w") as f:
            faulthandler.enable(file=f)

        self.fus = None
        self.listener = None
        self.n_channels = 0
        self.total_sequence_duration_ms = 0

        self.seq = None
        self.seq_buffer = 0
        self.n_pulse_train_rep = 0
        self.pulse_train_delay = 0

    def connect(self, connect_info, log_dir='C:\\Temp', log_name='standalone_igt'):
        """
        Connects to the IGT ultrasound driving system.

        Parameters:
            connect_info (str): Path with IGT driving system-specific configuration file.
        """

        try:
            # Establish connection with driving system
            logger.info('Before unifus.FUSSystem....')
            self.fus = unifus.FUSSystem()
            logger.info('After unifus.FUSSystem....')
        except Exception as e:
            logger.error(f'Error initializing FUSSystem: {e}')
            sys.exit()

        try:
            unifus.setLogPath(log_dir, log_name + "_igt_ds_log")
            unifus.setLogLevel(unifus.LogLevel.Debug)

            logger.info('After setting logging....')
        except Exception as e:
            logger.error(f"Error setting up logging: {e}")
            sys.exit()

        try:
            # Update the name of your configuration file
            igt_config_path = pkg_resources.resource_filename('fus_driving_systems', connect_info)
            logger.info(f'igt_config_path: {igt_config_path} found....')
            if igt_config_path != '':
                self.fus.loadConfig(igt_config_path)
                logger.info('After loadConfig....')
            else:
                logger.error("Configuration file %s doesn't exist.", igt_config_path)
                sys.exit()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            sys.exit()

        try:
            # Create and register an event listener
            self.listener = ExecListener()
            self.fus.registerListener(self.listener)
            logger.info('After listener....')

            self.fus.connect()
            self.listener.waitConnection()
            logger.info('After waitConnection()....')
        except Exception as e:
            logger.error(f"Error during connection or listener registration: {e}")
            sys.exit()

        try:
            if self.fus.isConnected():
                self.connected = True
                logger.info('Driving system is connected.')

                self.gen = self.fus.gen()
                self.n_channels = self.gen.getParam(unifus.GenParam.ChannelCount)
                logger.info("Generator: %s channels", self.n_channels)
            else:
                self.connected = False
                logger.error("Error: connection failed.")
                sys.exit()
        except Exception as e:
            logger.error(f"Error after connection check: {e}")
            sys.exit()

    def send_sequence(self, sequence):
        """
        Sends an ultrasound sequence to the IGT ultrasound driving system.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

        logger.info('Sequence with the following parameters is send to the driving system: \n '
                    + '%s', sequence)

        if self.is_connected():

            # define pulse
            pulse = self._define_pulse(sequence)

            # define pulse train
            self._define_pulse_train(sequence, pulse)

            # Define pulse train repetition
            # number of executions of one pulse train
            self.n_pulse_train_rep = math.floor(sequence.pulse_train_rep_dur /
                                                sequence.pulse_train_rep_int)

            # Apply ramping
            if sequence.pulse_ramp_shape != 'Rectangular - no ramping':
                self._apply_ramping(sequence)

            # (optional) restore disabled channels
            self.gen.enableAllChannels()

            # (optional) disable HeartBeat security
            self.gen.setParam(unifus.GenParam.HeartBeatTimeout, 0)

            # (optional) only for generator with a transducer multiplexer
            # gen.setParam (unifus.GenParam.MultiplexerValue, 3);

            # Upload the sequence
            self.gen.sendSequence(self.seq_buffer, self.seq)

            self.total_sequence_duration_ms = (100 + unifus.sequenceDurationMs(
                self.seq, self.n_pulse_train_rep, self.pulse_train_delay))

        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(sequence.driving_sys.connect_info)
            self.send_sequence(sequence)

    def wait_for_trigger(self):
        """
        Activates the listener on the IGT ultrasound driving system to wait for the trigger to
        execte the previously sent sequence.
        """

        try:
            # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the exec_flags
            # argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
            # To use trigger, add one of unifus::ExecFlag::Trigger*
            # exec_flags = unifus.ExecFlag.MeasureBoards
            # exec_flags = unifus.ExecFlag.MeasureTimings | unifus.ExecFlag.TriggerAllSequences
            exec_flags = (unifus.ExecFlag.MeasureTimings |
                          unifus.ExecFlag.MeasureChannels |
                          unifus.ExecFlag.MeasureBoards |
                          unifus.ExecFlag.DisableMonitoringChannelCombiner |
                          unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                          unifus.ExecFlag.TriggerOneSequence)
            # flags to disable checking the current limit

            self.gen.prepareSequence(self.seq_buffer, 1000000,
                                     self.pulse_train_delay, exec_flags)

            self.gen.startSequence()
            logger.info('Wait for trigger')

        except Exception as why:
            logger.error("Exception: %s", str(why))
            sys.exit()

    def execute_sequence(self):
        """
        Executes the previously sent sequence on the IGT ultrasound driving system.
        """

        try:
            # Use unifus.ExecFlag.NONE if nothing special, or simply don't pass the exec_flags
            # argument. Use '|' to combine multiple flags: flag1 | flag2 | flag3
            # To use trigger, add one of unifus::ExecFlag::Trigger*
            # exec_flags = unifus.ExecFlag.MeasureBoards
            # exec_flags = unifus.ExecFlag.MeasureTimings | unifus.ExecFlag.TriggerAllSequences
            exec_flags = (unifus.ExecFlag.MeasureTimings |
                          unifus.ExecFlag.MeasureChannels |
                          unifus.ExecFlag.MeasureBoards |
                          unifus.ExecFlag.DisableMonitoringChannelCombiner |
                          unifus.ExecFlag.DisableMonitoringChannelCurrentOut)
            # flags to disable checking the current limit

            self.gen.prepareSequence(self.seq_buffer, self.n_pulse_train_rep,
                                     self.pulse_train_delay, exec_flags)

            self.gen.startSequence()
            self.listener.waitSequence(self.total_sequence_duration_ms / 1000.0)

        except Exception as why:
            logger.error("Exception: %s", str(why))
            sys.exit()

    def disconnect(self):
        """
        Disconnects from the IGT ultrasound driving system.
        """

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
                logger.info("Disconnected")
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
            pulse.setAmplitudes([sequence.ampl])
        else:
            logger.error("Intensity parameter may be set incorrectly. Amplitude is None.")
            sys.exit()

        # set same phase offset for all channels (angle in [0,360] degrees)
        if sequence.dephasing_degree is not None and len(sequence.dephasing_degree) == sequence.transducer.elements:
                logger.info(f'Phases are overridden by phases set at dephasing_degree :{sequence.dephasing_degree}')
                pulse.setPhases(sequence.dephasing_degree)
        else:   
            pulse = self._set_phases(pulse, sequence.focus, sequence.transducer.steer_info,
                                     sequence.transducer.natural_foc, sequence.dephasing_degree)

        return pulse

    def _define_pulse_train(self, sequence, pulse):
        """
        Defines the pulse train for the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
            pulse (unifus.Pulse): The defined pulse.

        """

        # number of executions of one pulse train
        n_pulse_train = math.floor(sequence.pulse_train_dur / sequence.pulse_rep_int)

        # Define a complete sequence
        self.seq = []
        self.seq += n_pulse_train * [pulse]

        # milliseconds between pulse trains
        self.pulse_train_delay = sequence.pulse_train_rep_int - sequence.pulse_train_dur

    def _set_phases(self, pulse, focus, steer_info, natural_foc, dephasing_degree):
        """
        Gets the phases for the IGT ultrasound driving system.

        Parameters:
            pulse (unifus.Pulse): The defined pulse.
            focus (float): The focus value [mm].
            steer_info (str): Path to the steer information.
            natural_foc (float): The natural focus value [mm] used to calculate target focus.
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases based on
            the focus are overridden.

        Returns:
            list: List of phases.
        """

        # transducer has been chosen where phases are calculated based on phase law
        if steer_info.endswith('.ini'):

            trans = transducerXYZ.Transducer()
            ini_path = pkg_resources.resource_filename('fus_driving_systems', steer_info)
            if not trans.load(ini_path):
                logger.error('Error: can not load the transducer definition from %s', ini_path)
                sys.exit()

            # Calculate target focus with respect to natural focus: + is before natural focus,
            # - is after natural focus
            aim_wrt_natural_focus = natural_foc - focus

            # Aim n mm away from the natural focal spot, on main axis (Z)
            trans.computePhases(pulse, (0, 0, aim_wrt_natural_focus), focus, dephasing_degree)

        else:
            # Import excel file containing phases per focal depth
            excel_path = pkg_resources.resource_filename('fus_driving_systems', steer_info)

            logger.info('Extract phase information from %s', excel_path)

            if os.path.exists(excel_path):
                data = pd.read_excel(excel_path, engine='openpyxl')

                # Make sure both values have the same amount of decimals
                focus = round(focus, 1)
                match_row = data.loc[data['Distance'] == focus]

                if match_row.empty:
                    logger.error(f'No focus in transducer phases file {excel_path}' +
                                 f' corresponds with {focus}')
                    sys.exit()

                elif len(match_row) > 1:
                    logger.error('Duplicate foci %s found in transducer phases file %s',
                                 focus, excel_path)
                    sys.exit()

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
                logger.info(f'Computed phases for set focus of {focus}: {phases_str}')

                pulse.setPhases(phases)

            else:
                logger.error("Pipeline is cancelled. The following direction cannot be found: "
                             + "%s", excel_path)
                sys.exit()

        return pulse

    def _apply_ramping(self, sequence):
        """
        Applies ramping on the IGT ultrasound driving system.

        Parameters:
            sequence (Sequence): The sequence object containing ultrasound parameters.
        """

        # Use best temporal resolution for pulse ramping [ms]
        min_ramp_temp_res = 0.005  # [ms]
        max_ramp_steps = 1023

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

        if sequence.pulse_ramp_shape == 'Linear':  # Linear ramping
            # amount of points where ramping is applied
            n_points = math.floor(sequence.pulse_ramp_dur/pulse_ramp_temp_res)
            ampl_ramp = np.linspace(0, 1, n_points)

        elif sequence.pulse_ramp_shape == 'Tukey':  # Tukey ramping
            # amount of points where ramping is applied
            n_points = math.floor(sequence.pulse_ramp_dur/pulse_ramp_temp_res)
            alpha = 1
            x = np.linspace(0, alpha/2, n_points)
            ampl_ramp = np.zeros(n_points)
            for i in range(n_points):
                ampl_ramp[i] = 0.5 * (1 + math.cos((2*math.pi/alpha) * (x[i] - alpha/2)))

        return ampl_ramp
