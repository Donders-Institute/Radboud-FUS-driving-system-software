# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basis import

# Miscellaneous import
from abc import ABC, abstractmethod

# Own packages


class ControlDrivingSystem(ABC):
    """
    Abstract base class for an ultrasound driving system.

    Attributes:
        gen: Generator object.
        logger_name (str): Name of the logger.
    """

    def __init__(self):
        """
        Initializes the DrivingSystem object.
        """

        # Private -- subclasses must use is_connected()/set this via their own connect()/
        # disconnect(), never read/write it directly (nor should any external caller, e.g. a
        # host application). This is what actually enforces that: is_connected() is the only
        # supported way to check connection status.
        self._connected = False

        self.protocol_sent = False

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
    def send_protocol(self, protocol):
        """
        Abstract method for sending an ultrasound protocol to the ultrasound driving system.

        Parameters:
            protocol(Object): a TUSProtocol instance containing, amongst other things:
                the timing/power/focus parameters (focus, pulse duration, pulse rep. interval
                and etcetera) and the equipment used (driving system and transducer)
        """

    @abstractmethod
    def execute_protocol(self):
        """
        Abstract method for executing the previously sent protocol.
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

        return self._connected

    def is_protocol_sent(self):
        """
        Checks whether a protocol has been sent to the ultrasound driving system.

        Returns:
            bool: True if a protocol has been sent, False otherwise.
        """

        return self.protocol_sent

    def validate_protocol(self, protocol):
        """
        Validates if the protocol is within the expected ranges.

        Parameters:
            protocol(Object): a TUSProtocol instance containing, amongst other things:
                the timing/power/focus parameters (focus, pulse duration, pulse rep. interval
                and etcetera) and the equipment used (driving system and transducer)

        Returns:
            List: List of error messages.
        """

        error_messages = []

        if protocol.pulse_rep_int == 0:
            error_messages.append("Pulse Repetition Interval [ms] is not allowed to be 0.")
        else:
            n_pulses = protocol.pulse_train_dur/protocol.pulse_rep_int
            if not n_pulses.is_integer():
                error_messages.append("Number of pulses within the pulse train is not a whole " +
                                      "number: " +
                                      f"Pulse Train Duration of {protocol.pulse_train_dur} " +
                                      "[ms] divided by Pulse Rep. Interval of " +
                                      f"{protocol.pulse_rep_int} [ms] is {n_pulses:.2f}.")

        if protocol.pulse_train_rep_int == 0:
            error_messages.append("Pulse Train Repetition Interval [ms] is not allowed to be 0.")
        else:
            n_pulse_trains = protocol.pulse_train_rep_dur/protocol.pulse_train_rep_int
            if not n_pulse_trains.is_integer():
                error_messages.append(
                    "Number of pulse trains within the pulse train repetition is " +
                    "not a whole number: Pulse Train Repetition Duration of " +
                    f"{protocol.pulse_train_rep_dur} [ms] divided by Pulse " +
                    "Train Repetition Interval of " +
                    f"{protocol.pulse_train_rep_int} [ms] is {n_pulse_trains:.2f}.")

        if protocol.pulse_dur > protocol.pulse_rep_int:
            error_messages.append("Pulse Duration is not allowed to be higher than the Pulse " +
                                  f"Repetition Interval: {protocol.pulse_dur} [ms] vs. " +
                                  f"{protocol.pulse_rep_int} [ms], respectively.")

        if protocol.pulse_rep_int > protocol.pulse_train_dur:
            error_messages.append("Pulse Repetiton Interval is not allowed to be higher than " +
                                  f"the Pulse Train Duration: {protocol.pulse_rep_int} [ms] vs. " +
                                  f"{protocol.pulse_train_dur} [ms], respectively.")

        if protocol.pulse_train_dur > protocol.pulse_train_rep_int:
            error_messages.append("Pulse Train Duration is not allowed to be higher than the " +
                                  f"Pulse Train Repetition Interval: {protocol.pulse_train_dur} " +
                                  f"[ms] vs. {protocol.pulse_train_rep_int} [ms], respectively.")

        if protocol.pulse_train_rep_int > protocol.pulse_train_rep_dur:
            error_messages.append("Pulse Train Repetition Interval is not allowed to be higher " +
                                  "than the Pulse Train Repetition Duration: " +
                                  f" {protocol.pulse_train_rep_int} [ms] vs. " +
                                  f"{protocol.pulse_train_rep_dur} [ms], respectively.")

        return error_messages
