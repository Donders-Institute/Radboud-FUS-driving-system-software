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
import serial
import time

# Miscellaneous packages

# Own packages
from fus_driving_systems import control_driving_system as ds

# Access the logger
from fus_driving_systems.config.logging_config import logger


class CITRUS(ds.ControlDrivingSystem):
    """
    Class for an CITRUS ultrasound driving system, inheriting from the abstract class
    DrivingSystem.

    Attributes:
        connected (bool): Indicates whether the system is connected.
    """

    def connect(self, connect_info):
        """
        Connects to the CITRUS ultrasound driving system.

        Parameters:
            connect_info (str): Path with CITRUS driving system-specific configuration file.
        """

        logger.info('Connecting with BITSI...')

        # set up BITSI connection
        self.serBITSI = serial.Serial()
        self.serBITSI.baudrate = 115200
        self.serBITSI.port = connect_info
        self.serBITSI.bytesize = 8
        self.serBITSI.parity = 'N'
        self.serBITSI.stopbits = 1
        self.serBITSI.timeout = 1
        self.serBITSI.open()

        self.connected = True

    def send_sequence(self, seq):
        """
        Validates and sends an ultrasound sequence to the CITRUS ultrasound driving system.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

        logger.info('Sending sequence...')

    def execute_sequence(self, seq):
        """
        Executes the previously sent sequence on the CITRUS ultrasound driving system.
        """

        logger.info('Executing sequence...')

        # Stimulation onset (send starting trigger to execute sequence)
        binary = '00100000'  # 32
        decimal_number = int(binary, 2)
        byte_value = bytes([decimal_number])
        self.serBITSI.write(byte_value)
        self.serBITSI.flush()
        time.sleep(0.7)

    def disconnect(self):
        """
        Disconnects from the CITRUS ultrasound driving system.
        """

        logger.info('Disconnecting...')

        if self.serBITSI is not None:
            self.serBITSI.close()

        self.connected = False
