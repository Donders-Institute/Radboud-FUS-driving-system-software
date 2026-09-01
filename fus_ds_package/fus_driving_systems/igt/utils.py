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

import math
import time
from fus_driving_systems.igt import unifus

# Access the logger
from fus_driving_systems.config.logging_config import get_logger, get_measurements_logger


class VoltageFeedbackTracker:
    """
    Accumulates per-transducer onPulseResult() voltage across an execution's pulses, grouped
    into batches, and logs periodic INFO progress plus a WARNING once a transducer's own group
    average strays past a configured volt margin for several consecutive groups in a row
    (GitHub #137). Built fresh per execution (see IGT._configure_voltage_feedback()) since its
    accumulated state (group progress, consecutive-over-margin counts) is only meaningful for
    one run.

    Averages across a transducer's own channels (and across the pulses within one group), not
    per individual channel -- comparing at the same level the configured "expected voltage"
    itself represents, and avoids a systematic per-channel bias (one channel consistently
    reading a bit higher/lower than its neighbours, not a fault) from making that channel trip
    a warning before the others do. A channel-specific issue is still visible in the separate
    measurements log and via parse_intensity_log.py -- this is a coarse, low-noise "is this
    transducer roughly on target" signal for the researcher watching the console, not a
    diagnostic tool.

    A fixed volt margin (not a percentage) on purpose: a transducer deliberately configured at
    or near 0% amplitude (e.g. the "other" transducer in a two-transducer protocol where only
    one fires at a time) has an expected voltage close to 0 V -- a percentage-based margin
    would either be trivially always exceeded (tiny denominator inflating any noise into a
    huge-looking percentage) or need its own near-zero-voltage exemption, the same problem
    parse_intensity_log.py's swing_pct/MIN_EXPECTED_VOLTAGE_V handling was built around. A flat
    volt margin sidesteps this entirely: it's automatically far too loose to ever trigger for a
    near-0 V transducer, while still being meaningful for one that's actively driven.
    """

    def __init__(self, channel_ranges, total_pulses, num_groups, margin_v,
                 consecutive_for_warning):
        """
        Parameters:
            channel_ranges (list(dict)): One entry per transducer slot, each with 'serial',
                'channel_start', 'channel_end' (exclusive) and 'expected_volt' (float or None --
                None when there's no active calibration to derive one, see TransducerSlot.volt;
                such a slot still gets its measured average reported every group, it just skips
                the deviation/margin/warning logic below since there's nothing to compare
                against).
            total_pulses (int): Total pulses expected this execution (n_pulse_train_rep) -- 0 or
                None is treated as 1 (the smallest valid value), which forces a group size of 1
                pulse: every single pulse becomes its own group, rather than never grouping at
                all. In practice this never happens: send_protocol() always computes a real,
                positive n_pulse_train_rep whenever a protocol is actually sent.
            num_groups (int): How many groups to divide total_pulses into -- if there are fewer
                pulses than this, the group size still floors at 1 pulse (never 0), so fewer,
                smaller groups are reported instead of forcing num_groups onto too little data.
            margin_v (float): Volt deviation from expected voltage a group's own average may
                have before it counts as "over margin" for that group.
            consecutive_for_warning (int): How many consecutive over-margin groups (for the
                same transducer) before a WARNING is actually logged, instead of just the
                regular per-group INFO line -- avoids reacting to a single noisy group (e.g. one
                reflection-driven outlier).
        """

        self._channel_ranges = list(channel_ranges)
        self._pulses_per_group = max(1, math.ceil((total_pulses or 1) / max(1, num_groups)))
        self._margin_v = margin_v
        self._consecutive_for_warning = max(1, consecutive_for_warning)

        self._pulse_count = 0
        self._group_index = 0
        # Per-transducer serial: running sum/count for the group currently being filled, and
        # how many consecutive groups so far have been over margin (reset to 0 the moment a
        # group is back within margin).
        self._group_sum = {c['serial']: 0.0 for c in self._channel_ranges}
        self._group_n = {c['serial']: 0 for c in self._channel_ranges}
        self._consecutive_over = {c['serial']: 0 for c in self._channel_ranges}

    def add_pulse(self, measures):
        """Feeds one onPulseResult()'s worth of per-channel voltage in, and finalizes/logs the
        current group once enough pulses have accumulated. Never raises -- unifus.FUSListener's
        callbacks cannot propagate exceptions to Python (see ExecListener.onPulseResult()'s own
        comment), so a failure here is logged and swallowed rather than left to fail silently
        and invisibly instead."""

        try:
            self._add_pulse(measures)
        except Exception as e:  # pylint: disable=broad-exception-caught
            get_logger().debug(f"Voltage feedback tracking failed for this pulse: {e}")

    def _add_pulse(self, measures):
        if self._channel_ranges and measures is not None:
            channel_count = measures.channelCount()
            for entry in self._channel_ranges:
                channels = range(entry['channel_start'],
                                 min(entry['channel_end'], channel_count))
                values = [measures.channelPhysicalValue(ch, 0) for ch in channels]
                if values:
                    self._group_sum[entry['serial']] += sum(values) / len(values)
                    self._group_n[entry['serial']] += 1

        self._pulse_count += 1
        if self._pulse_count % self._pulses_per_group == 0:
            self._finalize_group()

    def _finalize_group(self):
        self._group_index += 1
        for entry in self._channel_ranges:
            serial = entry['serial']
            n = self._group_n[serial]
            self._group_n[serial] = 0
            group_sum = self._group_sum[serial]
            self._group_sum[serial] = 0.0
            if n == 0:
                continue

            mean_v = group_sum / n
            expected_v = entry['expected_volt']

            if expected_v is None:
                # Nothing to compare against (no active calibration, see this class's own
                # __init__ docstring) -- still report what was actually measured, since the
                # driving system does return a real voltage regardless, but skip the
                # deviation/margin/warning logic entirely below.
                get_logger().info(
                    f"Voltage feedback (group {self._group_index}): {serial} averaged "
                    f"{mean_v:.2f} V (no active calibration to compare against).")
                continue

            deviation_v = mean_v - expected_v
            get_logger().info(
                f"Voltage feedback (group {self._group_index}): {serial} averaged "
                f"{mean_v:.2f} V (expected {expected_v:.2f} V, {deviation_v:+.2f} V).")

            if abs(deviation_v) > self._margin_v:
                self._consecutive_over[serial] += 1
            else:
                self._consecutive_over[serial] = 0

            if self._consecutive_over[serial] >= self._consecutive_for_warning:
                get_logger().warning(
                    f"{serial}'s measured voltage has stayed more than {self._margin_v:.2f} V "
                    f"from its expected {expected_v:.2f} V for "
                    f"{self._consecutive_over[serial]} consecutive group(s) (currently "
                    f"{mean_v:.2f} V, {deviation_v:+.2f} V off).")


class VoltageFeedbackDispatcher:
    """
    Cycles incoming pulses across one VoltageFeedbackTracker per protocol in an interleaved
    group (GitHub #137), so each protocol's own grouping/reporting stays entirely independent
    of how the others' pulses interleave with it -- protocol[0]'s 5th pulse (wherever it falls
    in wall-clock time) still produces its own group report once protocol[0] itself has fired 5
    pulses, regardless of how many of protocol[1]'s pulses happened in between. Exposes the
    same add_pulse() interface as VoltageFeedbackTracker itself, so ExecListener.onPulseResult()
    doesn't need to know or care whether this execution is interleaved at all.

    IMPORTANT -- relies on an assumption not yet verified against real interleaved hardware:
    that onPulseResult() callbacks arrive in the same fixed, repeating cyclic order
    send_protocol() built pulse_train_seq in (protocol[0]'s pulse, protocol[1]'s, ..., back to
    protocol[0]'s, ...), with no drops or reordering. This matches how send_protocol() itself
    constructs pulse_train_seq (one Pulse per protocol, the whole list repeated as a unit
    n_pulse_train_rep times) and is the most natural reading of it, but has only been checked by
    reasoning about that code, not by inspecting a real log from an actual interleaved run. To
    verify: run two clearly distinguishable interleaved protocols (e.g. this package's own
    standalone_igt_alternating_single_pulse_train.py, where each fires a different transducer)
    and confirm the onPulseResult() sequence in the resulting log alternates in perfect
    lockstep -- transducer A active, transducer B active, transducer A active, ... -- with no
    exception, over the whole run. If it ever doesn't, this modulo-based routing will
    misattribute a pulse to the wrong protocol's tracker.

    Single-protocol executions (the overwhelming majority) get exactly one tracker here, so
    every pulse routes to it -- behaviourally identical to using that one tracker directly.
    """

    def __init__(self, trackers):
        self._trackers = trackers
        self._pulse_count = 0

    def add_pulse(self, measures):
        tracker = self._trackers[self._pulse_count % len(self._trackers)]
        self._pulse_count += 1
        tracker.add_pulse(measures)


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
        # Set by IGT._configure_voltage_feedback(), right before each execution's own
        # startSequence() -- a VoltageFeedbackDispatcher (which itself owns one
        # VoltageFeedbackTracker per protocol, see that class's own docstring). Only None before
        # the first execution has ever configured it, in which case onPulseResult() below skips
        # it entirely.
        self.voltage_feedback = None
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
        if self.voltage_feedback is not None:
            self.voltage_feedback.add_pulse(measures)
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
