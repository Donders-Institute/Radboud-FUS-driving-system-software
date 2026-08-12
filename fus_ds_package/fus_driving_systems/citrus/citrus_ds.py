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

        self.connected = True

    def send_protocol(self, protocol):
        """
        Validates and sends an ultrasound protocol to the CITRUS ultrasound driving system.

        Parameters:
            protocol(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
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

        self.connected = False
