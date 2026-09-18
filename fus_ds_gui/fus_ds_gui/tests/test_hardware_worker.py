# -*- coding: utf-8 -*-
"""
Tests for DrivingSystemWorker. Mocks the ControlDrivingSystem instance itself
(MagicMock(spec=IGT), matching the core package's own established mocking style for its SDK
seams) rather than moving anything onto a real QThread: these tests are about the worker's own
try/except-then-emit wiring, not about threading itself.
"""
from unittest.mock import MagicMock

import pytest

from fus_driving_systems.exceptions import FDSHardwareError, FDSValidationError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts

from fus_ds_gui.workers.hardware_worker import DrivingSystemWorker


@pytest.fixture
def mock_ds():
    return MagicMock(spec=IGT)


@pytest.fixture
def worker(mock_ds):
    return DrivingSystemWorker(mock_ds)


def test_do_connect_emits_connected_with_is_connected_result(qtbot, worker, mock_ds):
    mock_ds.is_connected.return_value = True

    with qtbot.waitSignal(worker.connected, timeout=1000) as blocker:
        worker.do_connect('COM1')

    mock_ds.connect.assert_called_once_with('COM1')
    assert blocker.args == [True]


def test_do_connect_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSHardwareError("no connection")
    mock_ds.connect.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_connect('COM1')

    assert blocker.args == [exc]


def test_do_disconnect_emits_disconnected_on_success(qtbot, worker, mock_ds):
    with qtbot.waitSignal(worker.disconnected, timeout=1000):
        worker.do_disconnect()

    mock_ds.disconnect.assert_called_once()


def test_do_disconnect_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSHardwareError("disconnect failed")
    mock_ds.disconnect.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_disconnect()

    assert blocker.args == [exc]


def test_do_send_protocol_emits_sent_on_success(qtbot, worker, mock_ds):
    protocol = object()

    with qtbot.waitSignal(worker.sent, timeout=1000):
        worker.do_send_protocol(protocol)

    mock_ds.send_protocol.assert_called_once_with(protocol)


def test_do_send_protocol_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSValidationError("bad protocol")
    mock_ds.send_protocol.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_send_protocol(object())

    assert blocker.args == [exc]


def test_do_execute_protocol_emits_executed_on_success(qtbot, worker, mock_ds):
    protocol = object()

    with qtbot.waitSignal(worker.executed, timeout=1000):
        worker.do_execute_protocol(protocol)

    mock_ds.execute_protocol.assert_called_once_with(protocol)


def test_do_execute_protocol_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSHardwareError("execution failed")
    mock_ds.execute_protocol.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_execute_protocol(object())

    assert blocker.args == [exc]


def test_do_wait_for_trigger_arms_then_waits_for_result_on_igt(qtbot, worker, mock_ds):
    protocol = object()

    with qtbot.waitSignals([worker.armed, worker.executed], timeout=1000):
        worker.do_wait_for_trigger(protocol, 'TriggerWholeProtocol', None)

    mock_ds.wait_for_trigger.assert_called_once_with(protocol, 'TriggerWholeProtocol', None)
    mock_ds.wait_for_trigger_result.assert_called_once()


def test_do_wait_for_trigger_only_arms_on_sonic_concepts(qtbot):
    mock_ds = MagicMock(spec=SonicConcepts)
    worker = DrivingSystemWorker(mock_ds)
    protocol = object()

    with qtbot.waitSignal(worker.armed, timeout=1000):
        worker.do_wait_for_trigger(protocol, None, None)

    mock_ds.wait_for_trigger.assert_called_once_with(protocol)


def test_do_wait_for_trigger_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSHardwareError("no connection")
    mock_ds.wait_for_trigger.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_wait_for_trigger(object(), 'TriggerWholeProtocol', None)

    assert blocker.args == [exc]


def test_do_wait_for_trigger_result_error_still_reaches_error_signal(qtbot, worker, mock_ds):
    exc = FDSHardwareError("timed out")
    mock_ds.wait_for_trigger_result.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_wait_for_trigger(object(), 'TriggerWholeProtocol', None)

    assert blocker.args == [exc]


def test_do_abort_emits_aborted_on_success(qtbot, worker, mock_ds):
    with qtbot.waitSignal(worker.aborted, timeout=1000):
        worker.do_abort()

    mock_ds.abort.assert_called_once()


def test_do_abort_emits_error_on_fdserror(qtbot, worker, mock_ds):
    exc = FDSHardwareError("abort failed")
    mock_ds.abort.side_effect = exc

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.do_abort()

    assert blocker.args == [exc]
