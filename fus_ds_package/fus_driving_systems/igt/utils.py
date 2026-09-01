# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University and Image Guided Therapy

SPDX-License-Identifier: MIT
See the LICENSE file for full license text, and THIRD_PARTY_NOTICES.md for which files in this
package originate from Image Guided Therapy. This file was originally written by Image
Guided Therapy and has since been modified by Radboud University.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# This file contains some general purpose functions used in most examples.

import time
from fus_driving_systems.igt import unifus

# Access the logger
from fus_driving_systems.config.logging_config import get_logger, get_measurements_logger


class ExecListener(unifus.FUSListener):
    """
    A listener class used to illustrate how to receive events sent by the FUS object,
    and also how to wait for the end of an execution properly.
    """

    def __init__(self):
        unifus.FUSListener.__init__(self)
        self._connecting = False
        # for ultrasounds
        self._running = False
        self.pulse_results = []
        self.exec_result = None
        # Set by onSequenceResult() when a protocol execution fails; unifus.FUSListener's
        # callbacks cannot propagate exceptions to Python (see its docstring), so this is read
        # back and acted on (sys.exit()) by the caller on the main thread, after wait_protocol()
        # returns, rather than raised here.
        self.exec_error_code = None
        # for mechanics
        self._finding_origin = False
        self._moving = False
        self.mech_result = None

    def onConnectStart(self):  # pylint: disable=invalid-name
        self._connecting = True
        get_logger().debug("Listener: CONNECTING")

    def onConnectResult(self, result):  # pylint: disable=invalid-name
        self._connecting = False
        if result == unifus.ConnectResult.Success:
            get_logger().debug("Listener: CONNECTED")
        else:
            get_logger().error(f"Listener: CONNECTION FAILED ({result})")

    def onDisconnect(self, reason):  # pylint: disable=invalid-name
        self._running = False
        get_logger().debug(f"Listener: DISCONNECTED ({reason})")

    # pylint: disable-next=invalid-name
    def onSequenceStart(self, exec_id, buffer, count, delay, flags):
        self._running = True
        self.pulse_results = []
        get_logger().debug(f"Listener: EXEC START (buff: {buffer}, count: {count}, "
                           f"delay: {delay:g})")

    def onPulseResult(self, result):  # pylint: disable=invalid-name
        # Routed through get_measurements_logger() (not get_logger()), and always populated now
        # that debug_info no longer exists as an opt-out (see execute_protocol()/
        # wait_for_trigger()) -- this is real per-pulse, per-channel hardware data, potentially
        # thousands of lines for a protocol with many repetitions, kept out of the main info/
        # debug files for exactly that reason (see _measurements_logger's own comment).
        self.pulse_results.append(result)
        get_measurements_logger().debug(
            f"Listener: PULS RESULT (exec: {result.execIndex()}, "
            f"pulse: {result.pulseIndex()}, duration: {result.duration():g} ms, "
            f"elapsed: {result.msFromStart():g} ms)")
        measures = result.sharedMeasurements()
        if measures is not None:
            get_measurements_logger().debug(
                f"          Available: {measures.boardMeasureCount()} measures for "
                f"{measures.boardCount()} board(s), "
                f"{measures.channelMeasureCount()} measures for "
                f"{measures.channelCount()} channel(s)")
            for channel in range(measures.channelCount()):
                # Note: it is advised to call measures.physicalChannelMeasureAvailable(measure) to
                # check before calling .channelPhysicalValue (channel, measure).
                if measures.channelMeasureCount() == 5:
                    get_measurements_logger().debug(
                        f"    ch[{channel}] "
                        f"V={measures.channelPhysicalValue(channel, 0):#4.3g} V, "
                        f"I={measures.channelPhysicalValue(channel, 1):#4.3g} A, "
                        f"PhaseV/I={measures.channelPhysicalValue(channel, 2):#4.3g}°, "
                        f"PhaseV/Vref={measures.channelPhysicalValue(channel, 3):#5.4g}°, "
                        f"Freq={measures.channelRawValue(channel, 4):7d} Hz, "
                        f"Pow={measures.power(channel):#g} W")
                else:
                    get_measurements_logger().debug(
                        f"    ch[{channel}] "
                        f"Vfwd={measures.channelPhysicalValue(channel, 0):#4.3g} V, "
                        f"Vrev={measures.channelPhysicalValue(channel, 1):#4.3g} V, "
                        f"PhaseV/Vref={measures.channelPhysicalValue(channel, 2):#5.4g}°, "
                        f"Freq={measures.channelRawValue(channel, 3):7d} Hz, "
                        f"Pow={measures.power(channel):#g} W")

    # pylint: disable-next=invalid-name
    def onSequenceResult(self, exec_id, exec_index, pulse_index, error_code):
        self._running = False
        if error_code == 0:
            self.exec_error_code = None
            get_logger().debug(f"Listener: EXEC RESULT SUCCESS (exec: {exec_index})")
        else:
            self.exec_error_code = error_code
            get_logger().error(f"Listener: EXEC RESULT ERROR (code: {error_code}, "
                               f"on exec: {exec_index}, pulse: {pulse_index})")

    def onMechOriginStart(self):  # pylint: disable=invalid-name
        self._finding_origin = True
        get_logger().debug("Listener: START  finding mech origins")

    def onMechOriginResult(self, result, msg):  # pylint: disable=invalid-name
        self._finding_origin = False
        get_logger().debug(f"Listener: RESULT finding mech origins: {result.name} ({msg})")

    def onMechStart(self, exec_id, count):  # pylint: disable=invalid-name
        self._moving = True
        self.mech_result = None
        get_logger().debug(f"Listener: START  motion (id: {exec_id}, count: {count})")

    def onMechResult(self, exec_id, result, error_code):  # pylint: disable=invalid-name
        self._moving = False
        self.mech_result = result
        if error_code == 0:
            get_logger().debug(f"Listener: RESULT motion success (id: {exec_id})")
        else:
            get_logger().error(f"Listener: RESULT motion error (id: {exec_id}, "
                               f"code: {error_code}, result: {result})")

    def wait_connection(self, timeout=5.0):
        max_wait = time.time() + timeout
        while True:
            time.sleep(0.2)
            if not self._connecting:
                return True
            if time.time() > max_wait:
                return False

    def wait_protocol(self, timeout=5.0):
        """
            Wait until the current ultrasound protocol is finished, or specified timeout in
            seconds.
        """
        max_wait = time.time() + timeout
        # Start with a sleep to make sure the start event has been received
        # and _running has been set to true.
        while True:
            time.sleep(0.002)
            if not self._running:
                return
            if time.time() > max_wait:
                return False

    def wait_origins(self, timeout=20.0):
        """
            Wait until the mechanical origins are found, or specified timeout in seconds.
        """
        max_wait = time.time() + timeout
        # Start with a sleep to make sure the start event has been received
        # and _moving has been set to true.
        while True:
            time.sleep(0.2)
            if not self._finding_origin:
                return
            if time.time() > max_wait:
                return False

    def wait_motion(self, timeout=30.0):
        """Wait until the current motion is finished, or specified timeout in seconds."""
        max_wait = time.time() + timeout
        # Start with a sleep to make sure the start event has been received
        # and _moving has been set to true.
        while True:
            time.sleep(0.2)
            if not self._moving:
                return
            if time.time() > max_wait:
                return False

    def print_exec_result(self):
        msg = "Execution result: "
        if self.exec_result is None:
            msg += "Nothing received"
        elif self.exec_result.isError():
            msg += "ERROR\n"
            msg += f"  code: {self.exec_result.status()} / {self.exec_result.statusName()}\n"
            msg += "  message: " + self.exec_result.errorMessage()
        else:
            msg += "SUCCESS"
        get_logger().debug(msg)
