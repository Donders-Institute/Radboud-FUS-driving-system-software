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

# Basis import

# Miscellaneous import
from abc import ABC, abstractmethod

# Own packages


class ControlDrivingSystem(ABC):
    """
    Abstract base class for an ultrasound driving system.

    Attributes:
        connected (bool): Indicates whether the system is connected.
        gen: Generator object.
        logger_name (str): Name of the logger.
    """

    def __init__(self):
        """
        Initializes the DrivingSystem object.
        """

        # boolean to determine if gen is connected
        self.connected = False

        self.sequence_sent = False

        # generator object
        self.gen = None

    @abstractmethod
    def connect(self, connect_info):
        """
        Abstract method for connecting to the ultrasound driving system.

        Parameters:
            connect_info: Information required for establishing a connection, either a com port or
            configuration file.
        """

    @abstractmethod
    def send_sequence(self, sequence):
        """
        Abstract method for sending an ultrasound sequence to the ultrasound driving system.

        Parameters:
            sequence(Object): contains, amongst other things, of:
                the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
        """

    @abstractmethod
    def execute_sequence(self):
        """
        Abstract method for executing the previously sent sequence.
        """

    @abstractmethod
    def disconnect(self):
        """
        Abstract method for disconnecting from the ultrasound driving system.
        """

    def is_connected(self):
        """
        Checks whether the ultrasound driving system is currently connected.

        Returns:
            bool: True if connected, False otherwise.
        """

        return self.connected

    def is_sequence_sent(self):
        """
        Checks whether a sequence has been sent to the ultrasound driving system.

        Returns:
            bool: True if a sequence has been sent, False otherwise.
        """

        return self.sequence_sent
