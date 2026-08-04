# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.igt.utils.ExecListener.

ExecListener subclasses the real unifus.FUSListener (fixed at class
definition time in utils.py's own import), which is safe to instantiate
directly -- it's a plain in-process event-flag tracker, no hardware
touched by any of its methods. Real unifus enums (ConnectResult, etc.)
are used directly rather than faked, since they're just plain values.
"""
from types import SimpleNamespace

from fus_driving_systems.igt import unifus
from fus_driving_systems.igt.utils import ExecListener


class _FakeMeasures:
    def __init__(self, channel_measure_count):
        self._channel_measure_count = channel_measure_count

    def boardMeasureCount(self):
        return 1

    def boardCount(self):
        return 1

    def channelMeasureCount(self):
        return self._channel_measure_count

    def channelCount(self):
        return 1

    def channelPhysicalValue(self, channel, measure):
        return 1.0

    def channelRawValue(self, channel, measure):
        return 1

    def power(self, channel):
        return 1.0


def _fake_pulse_result(shared_measurements=None):
    result = SimpleNamespace()
    result.execIndex = lambda: 1
    result.pulseIndex = lambda: 2
    result.duration = lambda: 0.5
    result.msFromStart = lambda: 10.0
    result.sharedMeasurements = lambda: shared_measurements
    return result


class TestConnectionCallbacks:

    def test_on_connect_start_sets_connecting_flag(self):
        listener = ExecListener()
        assert listener._connecting is False

        listener.onConnectStart()

        assert listener._connecting is True

    def test_on_connect_result_clears_connecting_flag_on_success(self):
        listener = ExecListener()
        listener._connecting = True

        listener.onConnectResult(unifus.ConnectResult.Success)

        assert listener._connecting is False

    def test_on_connect_result_clears_connecting_flag_on_failure(self):
        listener = ExecListener()
        listener._connecting = True

        listener.onConnectResult(unifus.ConnectResult.BadConfig)

        assert listener._connecting is False

    def test_on_disconnect_clears_running_flag(self):
        listener = ExecListener()
        listener._running = True

        listener.onDisconnect(unifus.DisconnectReason.__members__[
            next(iter(unifus.DisconnectReason.__members__))])

        assert listener._running is False


class TestSequenceCallbacks:

    def test_on_sequence_start_sets_running_and_resets_pulse_results(self):
        listener = ExecListener()
        listener.pulse_results = ["stale"]

        listener.onSequenceStart(exec_id=1, buffer=0, count=3, delay=0.0, flags=0)

        assert listener._running is True
        assert listener.pulse_results == []

    def test_on_pulse_result_appends_result_without_measurements(self):
        listener = ExecListener()
        result = _fake_pulse_result(shared_measurements=None)

        listener.onPulseResult(result)

        assert listener.pulse_results == [result]

    def test_on_pulse_result_appends_result_with_measurements(self):
        listener = ExecListener()
        measures = _FakeMeasures(channel_measure_count=5)
        result = _fake_pulse_result(shared_measurements=measures)

        listener.onPulseResult(result)

        assert listener.pulse_results == [result]

    def test_on_pulse_result_appends_result_with_non_five_channel_measurements(self):
        listener = ExecListener()
        measures = _FakeMeasures(channel_measure_count=4)
        result = _fake_pulse_result(shared_measurements=measures)

        listener.onPulseResult(result)

        assert listener.pulse_results == [result]

    def test_on_sequence_result_clears_running_flag_on_success(self):
        listener = ExecListener()
        listener._running = True

        listener.onSequenceResult(exec_id=1, exec_index=0, pulse_index=0, error_code=0)

        assert listener._running is False

    def test_on_sequence_result_clears_running_flag_on_error(self):
        listener = ExecListener()
        listener._running = True

        listener.onSequenceResult(exec_id=1, exec_index=0, pulse_index=1, error_code=7)

        assert listener._running is False


class TestMechanicCallbacks:

    def test_on_mech_origin_start_sets_finding_origin_flag(self):
        listener = ExecListener()

        listener.onMechOriginStart()

        assert listener._finding_origin is True

    def test_on_mech_origin_result_clears_finding_origin_flag(self):
        listener = ExecListener()
        listener._finding_origin = True
        result = SimpleNamespace(name="Found")

        listener.onMechOriginResult(result, "all good")

        assert listener._finding_origin is False

    def test_on_mech_start_sets_moving_flag_and_resets_result(self):
        listener = ExecListener()
        listener.mech_result = "stale"

        listener.onMechStart(exec_id=1, count=2)

        assert listener._moving is True
        assert listener.mech_result is None

    def test_on_mech_result_clears_moving_flag_and_stores_result(self):
        listener = ExecListener()
        listener._moving = True
        result = SimpleNamespace(name="Done")

        listener.onMechResult(exec_id=1, result=result, error_code=0)

        assert listener._moving is False
        assert listener.mech_result is result

    def test_on_mech_result_clears_moving_flag_on_error(self):
        listener = ExecListener()
        listener._moving = True
        result = SimpleNamespace(name="Failed")

        listener.onMechResult(exec_id=1, result=result, error_code=3)

        assert listener._moving is False
        assert listener.mech_result is result


class TestWaitMethods:
    """One 'already satisfied, returns immediately' test per wait* method,
    plus a real (not mocked) short-timeout test for two of them --
    representative of the shared poll-loop pattern used by all four."""

    def test_wait_connection_returns_true_immediately_when_not_connecting(self):
        listener = ExecListener()
        assert listener._connecting is False

        assert listener.wait_connection(timeout=5.0) is True

    def test_wait_connection_returns_false_on_timeout(self):
        listener = ExecListener()
        listener._connecting = True  # never resolves

        assert listener.wait_connection(timeout=0.05) is False

    def test_wait_sequence_returns_none_immediately_when_not_running(self):
        listener = ExecListener()
        assert listener._running is False

        assert listener.wait_sequence(timeout=5.0) is None

    def test_wait_sequence_returns_false_on_timeout(self):
        listener = ExecListener()
        listener._running = True  # never resolves

        assert listener.wait_sequence(timeout=0.01) is False

    def test_wait_origins_returns_none_immediately_when_not_finding_origin(self):
        listener = ExecListener()
        assert listener._finding_origin is False

        assert listener.wait_origins(timeout=5.0) is None

    def test_wait_origins_returns_false_on_timeout(self):
        listener = ExecListener()
        listener._finding_origin = True  # never resolves

        assert listener.wait_origins(timeout=0.05) is False

    def test_wait_motion_returns_none_immediately_when_not_moving(self):
        listener = ExecListener()
        assert listener._moving is False

        assert listener.wait_motion(timeout=5.0) is None

    def test_wait_motion_returns_false_on_timeout(self):
        listener = ExecListener()
        listener._moving = True  # never resolves

        assert listener.wait_motion(timeout=0.05) is False


class TestPrintExecResult:

    def test_print_exec_result_handles_none(self):
        listener = ExecListener()
        assert listener.exec_result is None

        listener.print_exec_result()  # must not raise

    def test_print_exec_result_handles_success(self):
        listener = ExecListener()
        listener.exec_result = SimpleNamespace(isError=lambda: False)

        listener.print_exec_result()  # must not raise

    def test_print_exec_result_handles_error(self):
        listener = ExecListener()
        listener.exec_result = SimpleNamespace(
            isError=lambda: True,
            status=lambda: 5,
            statusName=lambda: "SomeError",
            errorMessage=lambda: "boom",
        )

        listener.print_exec_result()  # must not raise
