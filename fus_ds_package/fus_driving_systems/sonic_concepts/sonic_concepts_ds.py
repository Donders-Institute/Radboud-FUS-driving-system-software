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
import re
import sys
import time

# Miscellaneous packages
from CTkMessagebox import CTkMessagebox

import tkinter

import serial

# Own packages
from fus_driving_systems import control_driving_system as ds
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import logger


class SonicConcepts(ds.ControlDrivingSystem):
    """
    Class for an Sonic Concepts ultrasound driving system,
    inheriting from the abstract class DrivingSystem.

    Attributes:
        connected (bool): Indicates whether the system is connected.
        gen: Generator object.
    """

    def connect(self, connect_info):
        """
        Connects to the Sonic Concepts ultrasound driving system.

        Parameters:
            connect_info (str): COM port information.
        """
        
        # When no connection, it is assumed that sent sequence isn't available (anymore)
        self.sequence_sent = False

        self.gen = serial.Serial(connect_info, 115200, timeout=1)
        startup_message = self.gen.readline().decode("ascii").strip()
        logger.info("Driving system: %s", startup_message)

        if startup_message == 'E2':
            self.connected = False
            logger.error("Error E2; connection cannot be made with driving system")
            sys.exit()
        else:
            self.connected = True
            logger.info("Connection with driving system %s is established", startup_message)

    def send_sequence(self, sequence):
        """
        Sends an ultrasound sequence to the Sonic Concepts ultrasound driving system.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

        logger.info('Sequence with the following parameters is send to the driving system: \n'
                    + ' %s', sequence)

        if self.is_connected():

            self._reset_parameters()

            self._set_operating_freq(sequence.oper_freq)
            self._set_focus(sequence.focus_wrt_exit_plane)
            self._set_global_power(sequence.global_power)
            self._set_burst_and_period(sequence.pulse_dur, sequence.pulse_rep_int)
            self._set_timer(sequence.pulse_train_dur)
            self._set_ramping(sequence.pulse_ramp_shape, sequence.pulse_ramp_dur)

            self.sequence_sent = True

            if sequence.wait_for_trigger:
                self._send_command('TRIGGERMODE=1\r\n')

        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(sequence.driving_sys.connect_info)
            self.send_sequence(sequence)

    def execute_sequence(self, sequence):
        """
        Executes the previously sent sequence on the Sonic Concepts ultrasound driving system.
        """

        if self.is_connected():
            if self.is_sequence_sent():
                try:
                    cmd = 'START\r'
                    self.gen.write(cmd.encode('ascii'))
                    time.sleep(0.05)
                    line = self.gen.readline()
                    logger.info('START: %s', line)

                except Exception as why:
                    logger.error("Exception: %s", str(why))
            else:
                logger.warning('The sequence has to be sent first using send_sequence() before ' +
                               'the driving system can execute a sequence.')
                logger.warning('Sending sequence...')

                self.send_sequence(sequence)
                self.execute_sequence(sequence)

        else:
            logger.warning("No connection with driving system.")
            logger.warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(sequence.driving_sys.connect_info)
            self.send_sequence(sequence)
            self.execute_sequence(sequence)

    def disconnect(self):
        """
        Disconnects from the Sonic Concepts ultrasound driving system.
        """

        if self.gen is not None:
            self.gen.close()
            self.connected = False

    def _send_command(self, command, sleep_time_s=1):
        """
        Sends a command to the Sonic Concepts ultrasound driving system and waits for the response.

        Parameters:
            command (str): The command to be sent.
            sleep_time_s (float): Time to sleep after sending the command [seconds].

        Returns:
            str: The response from the ultrasound driving system.
        """

        self.gen.write(command.encode("ascii"))
        logger.info("Sent to gen: %s", command.strip())
        time.sleep(sleep_time_s)
        response = self.gen.readline().decode("ascii").rstrip()
        logger.info(f"Response from gen: {response}")

        if response == 'E2':
            logger.error("Error E2")
            sys.exit()

        return response

    def _reset_parameters(self):
        """
        Resets parameters on the Sonic Concepts ultrasound driving system.
        """

        # Make sure gen is not in advanced mode
        command = 'LOCAL=1\r\n'
        self._send_command(command)
        self._reset_ramping()

    def _reset_ramping(self):
        """
        Resets ramping on the Sonic Concepts ultrasound driving system.
        """

        # Make sure ramping is off prior to experiment
        command = 'ABORT\r\n'
        self._send_command(command, 0.5)

        command = 'RAMPMODE=0\r\n'
        self._send_command(command)

    def _set_operating_freq(self, oper_freq):
        """
        Sets the operating frequency on the Sonic Concepts ultrasound driving system.

        Parameters:
            oper_freq (int): The operating frequency value [kHz].
        """

        # Set operating frequency on gen
        oper_freq_hz = oper_freq * 1e3
        command = f'GLOBALFREQ={oper_freq_hz}\r\n'
        self._send_command(command)

    def _set_focus(self, focus):
        """
        Sets the focus on the Sonic Concepts ultrasound driving system.

        Parameters:
            focus (int): The focus value [mm].
        """

        # convert focus in mm to micro meter
        focus = focus * 1e3

        # Set focus on gen
        command = f'FOCUS={focus}\r\n'
        self._send_command(command)

    def _set_global_power(self, global_power):
        """
        Sets the global power on the Sonic Concepts ultrasound driving system.

        Parameters:
            global_power (float): The global power value [W].
        """

        if global_power is not None:
            # convert global power in W to mW
            global_power = global_power * 1e3
            command = f'GLOBALPOWER={global_power}\r\n'
            self._send_command(command, 0.1)
        else:
            logger.error("Intensity parameter may be set incorrectly. Global power is None.")
            sys.exit()

    def _set_burst_length(self, burst):
        """
        Sets the burst length on the Sonic Concepts ultrasound driving system.

        Parameters:
            burst (float): The burst length value [us].
        """

        # Set pulse duration (PD)
        command = f'BURST={burst}\r\n'
        self._send_command(command, 0.1)

    def _set_period(self, period):
        """
        Sets the period on the Sonic Concepts ultrasound driving system.

        Parameters:
            period (float): The period value [us].
        """

        # Set pulse repetition period (PRP)
        command = f'PERIOD={period}\r\n'
        self._send_command(command, 0.1)

    def _set_burst_and_period(self, des_burst, des_period):
        """
        Sets the burst length and period on the Sonic Concepts ultrasound driving system.

        Parameters:
            des_burst (float): Desired burst length [ms].
            des_period (float): Desired period [ms].
        """

        # convert burst in milliseconds to micro seconds
        des_burst = des_burst * 1e3

        # convert period in milliseconds to micro seconds
        des_period = des_period * 1e3

        # Get current pulse repetition period (PRP)
        command = 'PERIOD?\r\n'

        feedback = self._send_command(command, 0.1)
        matches = re.findall(r'\d+\.?\d*', feedback)  # extract the number
        read_prp = float(matches[0])*1e3  # convert to float and from ms to us

        # Depending on current settings, set PD and PRP in the appropriate order
        # Check if desired PD is larger than the current PRP
        if des_burst > read_prp:
            self._set_period(des_period)
            self._set_burst_length(des_burst)
        else:
            self._set_burst_length(des_burst)
            self._set_period(des_period)

    def _set_timer(self, timer):
        """
        Sets the sonication duration (timer) on the Sonic Concepts ultrasound driving system.

        Parameters:
            timer (float): The sonication duration value [ms].
        """

        # convert timer in milliseconds to micro seconds
        timer = timer * 1e3

        # Set sonication duration (SD)
        command = f'TIMER={timer}\r\n'
        self._send_command(command, 0.1)

    def _set_ramping(self, ramp_mode, ramp_length):
        """
        Sets ramping parameters on the Sonic Concepts ultrasound driving system.

        Parameters:
            ramp_mode (int): Ramping mode (0 = Rectangular - no ramping, 1 = Linear, 2 = Tukey).
            ramp_length (float): Ramping length  [ms].
        """

        # convert ramp_length in milliseconds to micro seconds
        ramp_length = ramp_length * 1e3

        if ramp_mode == config['General']['Ramp shape.rect']:
            self._reset_ramping()

            # Send abort command to allow further control after applying ramping
            command = 'ABORT\r\n'
            self._send_command(command, 0.1)
        else:
            if ramp_mode == config['General']['Ramp shape.lin']:
                ramp_mode = 1
            elif ramp_mode == config['General']['Ramp shape.tuk']:
                ramp_mode = 2
            else:
                logger.error("Unknown modulation value: %s", ramp_mode)
                sys.exit(f"Unknown modulation value: {ramp_mode}")

            command = 'RAMPMODE={ramp_mode}\r\n'
            self._send_command(command)

            command = f'RAMPLENGTH={ramp_length}\r\n'
            self._send_command(command)

    def check_tran_sel(self):
        """
        Displays a warning dialog to encourage the user to check the correct transducer selection on
        the Sonic Concepts ultrasound driving system.
        """

        message = config['Equipment.Manufacturer.SC']['Check tran message']

        master = tkinter.Tk()
        master.withdraw()

        message_box = CTkMessagebox(title="Attention", message=message, icon="warning",
                                    option_1="Confirm")
        response = message_box.get()

        logger.info(f"Message box closed with response: {response}")

        if response == 'Confirm':
            logger.info("Correct transducer selection is confirmed.")
        else:
            logger.error("Pipeline is cancelled by user.")
            sys.exit()
