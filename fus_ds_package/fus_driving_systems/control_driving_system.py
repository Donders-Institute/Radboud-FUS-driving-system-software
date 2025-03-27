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

        error_messages = []

        n_pulses = sequence.pulse_train_dur/sequence.pulse_rep_int
        if not n_pulses.is_integer():
            error_messages.append("Number of pulses within the pulse train is not a whole number:" +
                                  f" Pulse Train Duration of {sequence.pulse_train_dur} [ms] " +
                                  f"divided by Pulse Rep. Interval of {sequence.pulse_rep_int} " +
                                  f"[ms] is {n_pulses:.2f}.")

        n_pulse_trains = sequence.pulse_train_rep_dur/sequence.pulse_train_rep_int
        if not n_pulse_trains.is_integer():
            error_messages.append("Number of pulse trains within the pulse train repetition is " +
                                  "not a whole number: Pulse Train Repetition Duration of " +
                                  f"{sequence.pulse_train_rep_dur} [ms] divided by Pulse Train " +
                                  f"Repetition Interval of {sequence.pulse_train_rep_int} [ms] is" +
                                  f" {n_pulse_trains:.2f}.")

        if sequence.pulse_dur > sequence.pulse_rep_int:
            error_messages.append("Pulse Duration is not allowed to be higher than the Pulse " +
                                  f"Repetition Interval: {sequence.pulse_dur} [ms] vs. " +
                                  f"{sequence.pulse_rep_int} [ms], respectively.")

        if sequence.pulse_rep_int > sequence.pulse_train_dur:
            error_messages.append("Pulse Repetiton Interval is not allowed to be higher than the " +
                                  f"Pulse Train Duration: {sequence.pulse_rep_int} [ms] vs. " +
                                  f"{sequence.pulse_train_dur} [ms], respectively.")

        if sequence.pulse_train_dur > sequence.pulse_train_rep_int:
            error_messages.append("Pulse Train Duration is not allowed to be higher than the " +
                                  f"Pulse Train Repetition Interval: {sequence.pulse_train_dur} " +
                                  f"[ms] vs. {sequence.pulse_train_rep_int} [ms], respectively.")

        if sequence.pulse_train_rep_int > sequence.pulse_train_rep_dur:
            error_messages.append("Pulse Train Repetition Interval is not allowed to be higher " +
                                  "than the Pulse Train Repetition Duration: " +
                                  f" {sequence.pulse_train_rep_int} [ms] vs. " +
                                  f"{sequence.pulse_train_rep_dur} [ms], respectively.")

        return error_messages
