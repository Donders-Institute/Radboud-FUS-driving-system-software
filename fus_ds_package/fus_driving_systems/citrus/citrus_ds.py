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
import sys
import time

import serial

# Miscellaneous packages

# Own packages
from fus_driving_systems import control_driving_system as ds

# Access the logger
from fus_driving_systems.config.logging_config import get_logger


class CITRUS(ds.ControlDrivingSystem):
    """
    Class for an CITRUS ultrasound driving system, inheriting from the abstract class
    DrivingSystem.

    Attributes:
        connected (bool): Indicates whether the system is connected.
        ser_bitsi: Serial connection object for the BITSI interface.
    """

    def __init__(self):
        """
        Initializes the CITRUS object.
        """

        super().__init__()
        self.ser_bitsi = None

    def connect(self, connect_info):
        """
        Connects to the CITRUS ultrasound driving system.

        Parameters:
            connect_info (str): Path with CITRUS driving system-specific configuration file.
        """

        get_logger().info('Connecting with BITSI...')

        # set up BITSI connection
        self.ser_bitsi = serial.Serial()
        self.ser_bitsi.baudrate = 115200
        self.ser_bitsi.port = connect_info
        self.ser_bitsi.bytesize = 8
        self.ser_bitsi.parity = 'N'
        self.ser_bitsi.stopbits = 1
        self.ser_bitsi.timeout = 1
        self.ser_bitsi.open()

        self._connected = True

    def send_protocol(self, protocol):
        """
        Validates and sends an ultrasound protocol to the CITRUS ultrasound driving system.

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

    def execute_protocol(self, protocol):
        """
        Executes the previously sent protocol on the CITRUS ultrasound driving system.
        """

        get_logger().info('Executing protocol...')

        # Stimulation onset (send starting trigger to execute protocol)
        binary = '00100000'  # 32
        decimal_number = int(binary, 2)
        byte_value = bytes([decimal_number])
        self.ser_bitsi.write(byte_value)
        self.ser_bitsi.flush()
        time.sleep(0.7)

    def disconnect(self):
        """
        Disconnects from the CITRUS ultrasound driving system.
        """

        get_logger().info('Disconnecting...')

        if self.ser_bitsi is not None:
            self.ser_bitsi.close()

        self._connected = False
