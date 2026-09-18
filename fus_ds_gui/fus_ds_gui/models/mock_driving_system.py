# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import time

from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.tus_protocol import TUSProtocol

# Long enough to feel like a real connection attempt, short enough not to be annoying during a
# demo. connect() runs on the Executing panel's own worker thread (see hardware_worker.py), so
# blocking here for real, the same way IGT/SonicConcepts actually do, is exactly the point.
_CONNECT_DELAY_S = 0.5


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
    buffer..." line, and execute_protocol()'s own "About to execute:"/"...executed
    successfully:" per-slot summary, see its own _log_intensity_summary()), so a researcher
    gets the exact same at-a-glance confirmation of what was sent/ran, in the same place (the
    console), that a real connection would give. execute_protocol() also blocks for the
    protocol's own real duration, same as real IGT's blocking wait for the sonication to
    finish, so the Executing panel's countdown (driven by its executed() signal for IGT, see
    ExecutingPanel._on_executed()) behaves the same way it would against real hardware.
    """

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

    def execute_protocol(self, protocols, total_alternating_duration_ms=None, buffer_num=0):
        if isinstance(protocols, TUSProtocol):
            protocols = [protocols]
        lines = [f'  Slot {i}: {slot.intensity_summary()}'
                 for protocol in protocols for i, slot in enumerate(protocol.slots)]
        summary = '\n'.join(lines)
        get_logger().info('Mock IGT: about to execute:\n%s', summary)
        # Real IGT's own execute_protocol() blocks here until the sonication itself is actually
        # done (self.listener.wait_protocol()); the Executing panel's countdown relies on that
        # (see ExecutingPanel._on_executed()'s own docstring) to know when execution finished,
        # so returning immediately here would make it skip straight to "Execution complete."
        # instead of counting down for real.
        duration_ms = total_alternating_duration_ms or protocols[0].pulse_train_rep_dur
        time.sleep(duration_ms / 1000.0)
        get_logger().info('Mock IGT: protocol executed successfully:\n%s', summary)

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
        get_logger().info("Mock SC: validating protocol...")
        get_logger().info("Mock SC: sending protocol...")
        self.protocol_sent = True

    def execute_protocol(self, protocol):
        get_logger().info("Mock SC: executing protocol...")
