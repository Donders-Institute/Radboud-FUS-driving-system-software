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
import re
import sys
import time
import tkinter

# Miscellaneous packages
from CTkMessagebox import CTkMessagebox

import serial

# Own packages
from fus_driving_systems import control_driving_system as ds
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.utils import get_config_value


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

        get_logger().info('Connecting...')

        # When no connection, it is assumed that sent protocol isn't available (anymore)
        self.protocol_sent = False

        self.gen = serial.Serial(connect_info, 115200, timeout=1)
        startup_message = self.gen.readline().decode("ascii").strip()
        get_logger().debug("Driving system: %s", startup_message)

        if startup_message == 'E2':
            self.connected = False
            message = "Error E2; connection cannot be made with driving system"
            get_logger().critical(message)
            sys.exit(message)
        else:
            self.connected = True
            get_logger().debug("Connection with driving system %s is established", startup_message)

    def send_protocol(self, protocol):
        """
        Sends an ultrasound protocol to the Sonic Concepts ultrasound driving system.

        Parameters:
            protocol(Object): a TUSProtocol instance containing, amongst other things:
                the timing/power/focus parameters (focus, pulse duration, pulse rep. interval
                and etcetera) and the equipment used (driving system and transducer)
        """

        get_logger().info('Validating protocol...')

        error_messages = self.validate_protocol(protocol)
        if error_messages:
            for error in error_messages:
                get_logger().critical(error)
            sys.exit('(Multiple) error(s) found when validating protocol, see log file.')

        get_logger().info('Sending protocol...')

        get_logger().debug(
            'Protocol with the following parameters is send to the driving system: \n' +
            ' %s', protocol)

        if self.is_connected():

            self._reset_parameters()

            self._set_operating_freq(protocol.oper_freq)
            self._set_focus(protocol.focus_wrt_exit_plane)
            self._set_global_power(protocol.global_power)
            self._set_burst_and_period(protocol.pulse_dur, protocol.pulse_rep_int)
            self._set_timer(protocol.pulse_train_dur)
            self._set_ramping(protocol.pulse_ramp_shape, protocol.pulse_ramp_dur)

            self.protocol_sent = True

            if protocol.wait_for_trigger:
                self._send_command('TRIGGERMODE=1\r\n')

        else:
            get_logger().error("No connection with driving system.")
            get_logger().error("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol.driving_sys.connect_info)
            self.send_protocol(protocol)

    def execute_protocol(self, protocol):
        """
        Executes the previously sent protocol on the Sonic Concepts ultrasound driving system.
        """

        get_logger().info('Executing protocol...')

        if self.is_connected():
            if self.is_protocol_sent():
                try:
                    cmd = 'START\r'
                    self.gen.write(cmd.encode('ascii'))
                    time.sleep(0.05)
                    line = self.gen.readline()
                    get_logger().debug('START: %s', line)

                except Exception as why:
                    message = "Exception: %s", str(why)
                    get_logger().critical(message)
                    sys.exit(message)
            else:
                get_logger().warning(
                    'The protocol has to be sent first using send_protocol() before ' +
                    'the driving system can execute a protocol.')
                get_logger().warning('Sending protocol...')

                self.send_protocol(protocol)
                self.execute_protocol(protocol)

        else:
            get_logger().warning("No connection with driving system.")
            get_logger().warning("Reconnecting with driving system...")

            # if no connection can be made, program stops preventing infinite loop
            self.connect(protocol.driving_sys.connect_info)
            self.send_protocol(protocol)
            self.execute_protocol(protocol)

    def disconnect(self):
        """
        Disconnects from the Sonic Concepts ultrasound driving system.
        """

        get_logger().info('Disconnecting...')

        if self.gen is not None:
            self.gen.close()
            self.connected = False
            get_logger().info("Disconnected.")

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
        get_logger().debug("Sent to gen: %s", command.strip())
        time.sleep(sleep_time_s)
        response = self.gen.readline().decode("ascii").rstrip()
        get_logger().debug(f"Response from gen: {response}")

        if response == 'E2':
            message = "Error E2"
            get_logger().critical(message)
            sys.exit(message)

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
            message = "Power parameter may be set incorrectly. Global power is None."
            get_logger().critical(message)
            sys.exit(message)

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

        if ramp_mode == get_config_value(get_logger(), config, 'Ramp', 'Option.rect',
                                         'Rectangular - no ramping'):
            self._reset_ramping()

            # Send abort command to allow further control after applying ramping
            command = 'ABORT\r\n'
            self._send_command(command, 0.1)
        else:
            if ramp_mode == get_config_value(get_logger(), config, 'Ramp', 'Option.lin', 'Linear'):
                ramp_mode = 1
            elif ramp_mode == get_config_value(
                    get_logger(), config, 'Ramp', 'Option.tuk', 'Tukey'):
                ramp_mode = 2
            else:
                message = f"Unknown modulation value: {ramp_mode}"
                get_logger().critical(message)
                sys.exit(message)

            command = f'RAMPMODE={ramp_mode}\r\n'
            self._send_command(command)

            command = f'RAMPLENGTH={ramp_length}\r\n'
            self._send_command(command)

    def check_tran_sel(self):
        """
        Displays a warning dialog to encourage the user to check the correct transducer
        selection on the Sonic Concepts ultrasound driving system.
        """

        default_message = 'Ensure the correct TRANSDUCER is selected on the driving system.'
        message = get_config_value(get_logger(), config, 'Equipment.Manufacturer.SC',
                                   'Check tran message', default_message)

        master = tkinter.Tk()
        master.withdraw()

        message_box = CTkMessagebox(title="Attention", message=message, icon="warning",
                                    option_1="Confirm")
        response = message_box.get()

        get_logger().debug(f"Message box closed with response: {response}")

        if response == 'Confirm':
            get_logger().debug("Correct transducer selection is confirmed.")
        else:
            message = "Pipeline is cancelled by user."
            get_logger().critical(message)
            sys.exit(message)
