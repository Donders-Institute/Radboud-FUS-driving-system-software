# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import math
import threading
import time

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSHardwareError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.tus_protocol import TUSProtocol
from fus_driving_systems.utils import get_config_value

# Long enough to feel like a real connection attempt, short enough not to be annoying during a
# demo. connect() runs on the Executing panel's own worker thread (see hardware_worker.py), so
# blocking here for real, the same way IGT/SonicConcepts actually do, is exactly the point.
_CONNECT_DELAY_S = 0.5

# Simulates the delay before a human actually presses the external trigger button, on top of
# the protocol's own real pulse_train_dur once it does (see wait_for_trigger_result()). Public
# so tests can assert against it directly instead of hardcoding a copy of this value.
MOCK_TRIGGER_PRESS_DELAY_S = 3


class MockIGT(IGT):
    """
    Subclasses the real IGT, not ControlDrivingSystem, so isinstance(..., IGT) checks elsewhere
    in the GUI still find it (the "connecting can take ~10s" hint,
    ProtocolBuilder.uses_pulse_train_repetition()). connect()/disconnect()/send_protocol()/
    execute_protocol() below replace IGT's own real unifus calls entirely, just logging and
    succeeding. validate_protocol() skips IGT's own "Amplitude is None" check, since that value
    is only ever computed from real calibration data this driving system doesn't have.
    is_connected() is overridden back to self._connected, since IGT's own version reads
    self.fus (never created here) instead.

    send_protocol()/execute_protocol() below log the same INFO-level lines the real
    IGT.send_protocol()/execute_protocol() do (the per-protocol "Validating protocol for
    buffer..." line, and execute_protocol()'s own "Executing:"/"...executed successfully:"
    per-slot summary, see its own _log_intensity_summary()), so a researcher
    gets the exact same at-a-glance confirmation of what was sent/ran, in the same place (the
    console), that a real connection would give. execute_protocol() also blocks for the
    protocol's own real duration, same as real IGT's blocking wait for the sonication to
    finish, so the Executing panel's countdown (driven by its executed() signal for IGT, see
    ExecutingPanel._on_executed()) behaves the same way it would against real hardware.

    _abort_event lets abort() interrupt execute_protocol()/wait_for_trigger_result()'s own
    blocking wait, the same way calling stopSequence() interrupts real hardware's own blocking
    wait_protocol().
    """

    def __init__(self, log_dir=None):
        super().__init__(log_dir)
        self._abort_event = threading.Event()
        self._armed_n_triggers = 1
        self._armed_fire_duration_ms = 0

    def connect(self, connect_info, log_dir=None, log_name=None):
        time.sleep(_CONNECT_DELAY_S)
        self._connected = True
        get_logger().info("Mock IGT: connected (%s).", connect_info)

    def disconnect(self):
        self._connected = False
        self.sent_protocols = {}
        get_logger().info("Mock IGT: disconnected.")

    def send_protocol(self, protocols, total_alternating_duration_ms=None, buffer_num=0):
        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        for protocol in protocols:
            tran_serials = ', '.join(slot.transducer.serial for slot in protocol.slots)
            get_logger().info(
                'Mock IGT: validating protocol for buffer %s (%s slot(s): %s)...',
                buffer_num, len(protocol.slots), tran_serials)
        get_logger().info("Mock IGT: sending protocol...")
        self.sent_protocols[buffer_num] = True

        # Confirms the send itself actually succeeded, with the timing/intensity a researcher
        # would otherwise not see until execute_protocol(), same reasoning as real IGT's own
        # send_protocol() (GitHub #125/#122). pulse_train_delay matches real IGT's own
        # _define_pulse_train(): the gap left in each repetition interval after the pulse
        # train itself finishes playing.
        protocol0 = protocols[0]
        duration_ms = total_alternating_duration_ms or protocol0.pulse_train_rep_dur
        n_pulse_train_rep = math.floor(
            protocol0.pulse_train_rep_dur / protocol0.pulse_train_rep_int)
        pulse_train_delay = protocol0.pulse_train_rep_int - protocol0.pulse_train_dur
        lines = [f'  Slot {i}: {slot.intensity_summary()}'
                 for protocol in protocols for i, slot in enumerate(protocol.slots)]
        get_logger().info(
            'Mock IGT: protocol sent successfully (buffer %s): %.2f ms pulse every %.2f ms, '
            '%s repetition(s) with %.2f ms delay between, %.2f ms total duration.\n%s',
            buffer_num, protocol0.pulse_dur, protocol0.pulse_rep_int, n_pulse_train_rep,
            pulse_train_delay, duration_ms, '\n'.join(lines))

    def execute_protocol(self, protocols, total_alternating_duration_ms=None, buffer_num=0):
        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        # Real IGT's own execute_protocol() blocks here until the sonication itself is actually
        # done (self.listener.wait_protocol()); the Executing panel's countdown relies on that
        # (see ExecutingPanel._on_executed()'s own docstring) to know when execution finished,
        # so returning immediately here would make it skip straight to "Execution complete."
        # instead of counting down for real.
        duration_ms = total_alternating_duration_ms or protocols[0].pulse_train_rep_dur
        get_logger().info('Mock IGT: executing (expected duration: %.2f ms)...', duration_ms)
        if self._wait_or_abort(duration_ms / 1000.0):
            get_logger().info('Mock IGT: protocol executed successfully.')
        else:
            self._raise_aborted()

    def wait_for_trigger(self, protocols, trigger_option, n_triggers=None,
                         total_alternating_duration_ms=None, buffer_num=0):
        """A "TriggerWholeProtocol" trigger fires the entire protocol (all repetitions) on a
        single trigger, exactly like a plain execute_protocol() would, so it's timed the same
        way (pulse_train_rep_dur). A "TriggerOnePulseTrain" trigger instead fires one pulse
        train (pulse_train_dur) per trigger, n_triggers times, see this method's own real
        docstring."""

        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        whole_protocol_trigger = get_config_value(get_logger(), config, 'Trigger',
                                                  'Option.whole_protocol', 'TriggerWholeProtocol')
        if trigger_option == whole_protocol_trigger:
            self._armed_n_triggers = 1
            self._armed_fire_duration_ms = (
                total_alternating_duration_ms or protocols[0].pulse_train_rep_dur)
        else:
            self._armed_n_triggers = n_triggers or 1
            self._armed_fire_duration_ms = protocols[0].pulse_train_dur
        get_logger().info(
            "Mock IGT: waiting for a total of %s trigger(s) (expected duration: %.2f ms)...",
            self._armed_n_triggers, self._armed_fire_duration_ms)

    def wait_for_trigger_result(self, buffer_num=0, timeout_s=5.0):
        """Real hardware only ever reports one combined result for the whole armed group of
        n_triggers, never progress per individual trigger (onSequenceResult() fires once, after
        all of them have fired): one wait, one final line, nothing in between, matching that."""

        total_wait_s = self._armed_n_triggers * (
            MOCK_TRIGGER_PRESS_DELAY_S + self._armed_fire_duration_ms / 1000.0)
        if self._wait_or_abort(total_wait_s):
            get_logger().info("Mock IGT: triggered protocol executed successfully.")
        else:
            self._raise_aborted()

    def abort(self):
        self._abort_event.set()
        get_logger().info("Mock IGT: aborted.")

    def _wait_or_abort(self, duration_s):
        """Returns: bool: True once duration_s has elapsed, False if abort() fired first."""

        self._abort_event.clear()
        return not self._abort_event.wait(duration_s)

    def _raise_aborted(self):
        message = "Aborted before completion."
        get_logger().critical(message)
        raise FDSHardwareError(message)

    def is_connected(self):
        return self._connected

    def validate_protocol(self, protocol):
        errors = super().validate_protocol(protocol)
        return [error for error in errors if 'Amplitude is None' not in error]


class MockSonicConcepts(SonicConcepts):
    """
    Same reasoning as MockIGT's own docstring, for isinstance(..., SonicConcepts) (the
    transducer-selection confirmation dialog) instead. validate_protocol() is inherited
    unchanged: unlike IGT's, it only checks the researcher's own chosen power value, nothing
    derived from calibration, so it already works without real hardware.
    """

    def connect(self, connect_info):
        time.sleep(_CONNECT_DELAY_S)
        self._connected = True
        get_logger().info("Mock SC: connected (%s).", connect_info)

    def disconnect(self):
        self._connected = False
        self.protocol_sent = False
        get_logger().info("Mock SC: disconnected.")

    def send_protocol(self, protocol):
        slot = protocol.slots[0]
        get_logger().info("Mock SC: validating protocol (transducer: %s)...",
                          slot.transducer.serial)
        get_logger().info("Mock SC: sending protocol...")
        self.protocol_sent = True
        get_logger().info(
            "Mock SC: protocol sent successfully: %.2f ms pulse every %.2f ms, %.2f ms "
            "total duration.\n  %s", protocol.pulse_dur, protocol.pulse_rep_int,
            protocol.pulse_train_dur, slot.intensity_summary())

    def execute_protocol(self, protocol):
        get_logger().info("Mock SC: executing (expected duration: %.2f ms)...",
                          protocol.pulse_train_dur)
        get_logger().info("Mock SC: protocol execution started.")

    def wait_for_trigger(self, protocol):
        get_logger().info(
            "Mock SC: armed, waiting for external trigger (expected duration once fired: "
            "%.2f ms)...", protocol.pulse_train_dur)

    def abort(self):
        get_logger().info("Mock SC: aborted.")
