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
from fus_driving_systems.igt.utils import (ExecListener, VoltageFeedbackDispatcher,
                                           VoltageFeedbackTracker)


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


class _FakeVoltageMeasures:
    """A measures fake for VoltageFeedbackTracker tests -- unlike _FakeMeasures above (fixed at
    1 channel / 1.0 V), this returns a caller-chosen voltage per channel index, since these
    tests need to control which channels see which values."""

    def __init__(self, channel_voltages):
        self._channel_voltages = channel_voltages

    def channelCount(self):
        return len(self._channel_voltages)

    def channelPhysicalValue(self, channel, measure):  # pylint: disable=unused-argument
        return self._channel_voltages[channel]


def _channel_range(serial, channel_start, channel_end, expected_volt):
    return {'serial': serial, 'channel_start': channel_start, 'channel_end': channel_end,
            'expected_volt': expected_volt}


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

    def test_on_pulse_result_logs_through_the_measurements_logger_not_the_main_one(
            self, caplog):
        """This is real per-pulse, per-channel hardware data -- potentially thousands of lines
        for a protocol with many repetitions -- kept off the main info/debug logger so it
        doesn't drown those out (GitHub #78/#137, see get_measurements_logger()'s own
        comment)."""
        listener = ExecListener()
        measures = _FakeMeasures(channel_measure_count=5)
        result = _fake_pulse_result(shared_measurements=measures)

        with caplog.at_level('DEBUG'):
            listener.onPulseResult(result)

        main_logger_records = [r for r in caplog.records if r.name == 'driving_system']
        measurements_logger_records = [r for r in caplog.records
                                       if r.name == 'driving_system.measurements']
        assert not main_logger_records
        assert measurements_logger_records
        assert any('PULS RESULT' in r.message for r in measurements_logger_records)

    def test_on_sequence_result_clears_running_flag_on_success(self):
        listener = ExecListener()
        listener._running = True

        listener.onSequenceResult(exec_id=1, exec_index=0, pulse_index=0, error_code=0)

        assert listener._running is False
        assert listener.exec_error_code is None

    def test_on_sequence_result_clears_running_flag_on_error(self):
        listener = ExecListener()
        listener._running = True

        listener.onSequenceResult(exec_id=1, exec_index=0, pulse_index=1, error_code=7)

        assert listener._running is False

    def test_on_sequence_result_stores_error_code_on_error(self):
        """GitHub issue #112: onSequenceResult() used to only log the error, with nothing
        callers could check afterwards -- igt_ds.py's execute_protocol() now reads this
        attribute (on the calling thread, after wait_protocol() returns) and sys.exit()s,
        since unifus.FUSListener's own docstring says exceptions raised inside its callbacks
        are not propagated to Python (so sys.exit() cannot live in the callback itself)."""
        listener = ExecListener()

        listener.onSequenceResult(exec_id=1, exec_index=0, pulse_index=0, error_code=2863311530)

        assert listener.exec_error_code == 2863311530

    def test_on_sequence_result_resets_error_code_on_a_later_success(self):
        """The listener object is reused across executions -- a stale error_code from a
        previous failed execution must not leak into a later successful one."""
        listener = ExecListener()
        listener.exec_error_code = 2863311530

        listener.onSequenceResult(exec_id=2, exec_index=0, pulse_index=0, error_code=0)

        assert listener.exec_error_code is None


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

    def test_wait_protocol_returns_none_immediately_when_not_running(self):
        listener = ExecListener()
        assert listener._running is False

        assert listener.wait_protocol(timeout=5.0) is None

    def test_wait_protocol_returns_false_on_timeout(self):
        listener = ExecListener()
        listener._running = True  # never resolves

        assert listener.wait_protocol(timeout=0.01) is False

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


class TestVoltageFeedbackTracker:
    """VoltageFeedbackTracker (GitHub #137) -- grouped, per-transducer live voltage feedback.
    See its own docstring for why it averages per transducer (not per channel) and uses a flat
    volt margin (not a percentage)."""

    def test_logs_info_every_group_even_within_margin(self, caplog):
        """The INFO heartbeat fires every group regardless of deviation -- it's the
        "system is doing something" signal, independent of the WARNING logic below."""
        ranges = [_channel_range('TRAN-A', 0, 2, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=4, num_groups=2, margin_v=1.0,
                                         consecutive_for_warning=2)

        with caplog.at_level('INFO'):
            for _ in range(4):
                tracker.add_pulse(_FakeVoltageMeasures([10.0, 10.0]))

        assert caplog.text.count('Voltage feedback (group') == 2
        assert 'TRAN-A' in caplog.text

    def test_does_not_warn_on_a_single_over_margin_group(self, caplog):
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=2, num_groups=2, margin_v=1.0,
                                         consecutive_for_warning=2)

        with caplog.at_level('INFO'):
            tracker.add_pulse(_FakeVoltageMeasures([15.0]))  # one group, 5 V over margin

        assert 'WARNING' not in caplog.text

    def test_warns_after_consecutive_over_margin_groups(self, caplog):
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=2, num_groups=2, margin_v=1.0,
                                         consecutive_for_warning=2)

        with caplog.at_level('INFO'):
            tracker.add_pulse(_FakeVoltageMeasures([15.0]))  # group 1: over margin
            tracker.add_pulse(_FakeVoltageMeasures([15.0]))  # group 2: over margin again

        warnings = [r for r in caplog.records if r.levelname == 'WARNING']
        assert len(warnings) == 1
        assert 'TRAN-A' in warnings[0].message

    def test_resets_consecutive_count_when_back_within_margin(self, caplog):
        """An over-margin group followed by a within-margin one must not let a later,
        unrelated over-margin group warn immediately -- the streak has to be genuinely
        consecutive."""
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=3, num_groups=3, margin_v=1.0,
                                         consecutive_for_warning=2)

        with caplog.at_level('INFO'):
            tracker.add_pulse(_FakeVoltageMeasures([15.0]))  # over margin (streak: 1)
            tracker.add_pulse(_FakeVoltageMeasures([10.0]))  # back within margin (streak: 0)
            tracker.add_pulse(_FakeVoltageMeasures([15.0]))  # over margin again (streak: 1)

        assert not any(r.levelname == 'WARNING' for r in caplog.records)

    def test_averages_across_a_transducers_own_channels_not_between_transducers(self, caplog):
        """Two transducers with very different voltages must not bleed into each other's
        average -- each channel range only ever averages its own channels."""
        ranges = [_channel_range('TRAN-A', 0, 2, expected_volt=20.0),
                  _channel_range('TRAN-B', 2, 3, expected_volt=0.5)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=1, num_groups=1, margin_v=1.0,
                                         consecutive_for_warning=1)

        with caplog.at_level('INFO'):
            tracker.add_pulse(_FakeVoltageMeasures([18.0, 22.0, 0.4]))  # TRAN-A: 20.0, TRAN-B: 0.4

        info_lines = [r.message for r in caplog.records if r.levelname == 'INFO']
        assert any('TRAN-A' in line and '20.00 V' in line for line in info_lines)
        assert any('TRAN-B' in line and '0.40 V' in line for line in info_lines)
        # TRAN-A is exactly on target (mean of 18/22), TRAN-B is 0.1 V off -- neither exceeds
        # the 1.0 V margin, so no warning for either.
        assert not any(r.levelname == 'WARNING' for r in caplog.records)

    def test_still_reports_measured_average_when_no_expected_voltage_is_available(self, caplog):
        """A slot with expected_volt=None (no active calibration, see
        IGT._configure_voltage_feedback()) still gets its measured average reported every group
        -- the driving system returns a real voltage regardless of calibration, so there's no
        reason to withhold it -- it just skips the deviation/margin/warning logic, since there's
        nothing to compare against."""
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0),
                  _channel_range('TRAN-OFF', 1, 2, expected_volt=None)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=1, num_groups=1, margin_v=1.0,
                                         consecutive_for_warning=1)

        with caplog.at_level('INFO'):
            tracker.add_pulse(_FakeVoltageMeasures([10.0, 999.0]))

        assert 'TRAN-A' in caplog.text
        info_lines = [r.message for r in caplog.records if r.levelname == 'INFO']
        assert any('TRAN-OFF' in line and '999.00 V' in line
                   and 'no active calibration' in line for line in info_lines)
        assert not any(r.levelname == 'WARNING' for r in caplog.records)

    def test_add_pulse_never_raises_when_measures_is_none(self, caplog):
        """A pulse with no shared measurements (result.sharedMeasurements() returned None) must
        still count towards the group's pulse total -- it just contributes no voltage data --
        so grouping stays aligned instead of drifting because some pulses were silently
        skipped."""
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=2, num_groups=2, margin_v=1.0,
                                         consecutive_for_warning=1)

        with caplog.at_level('INFO'):
            tracker.add_pulse(None)  # must not raise
            tracker.add_pulse(_FakeVoltageMeasures([10.0]))

        # Two groups' worth of pulses were fed in, but only the second carried real data --
        # exactly one INFO line, for the group that had something to report.
        assert caplog.text.count('Voltage feedback (group') == 1

    def test_group_average_excludes_pulses_with_no_measurements(self, caplog):
        """Unlike the test above (where pulses_per_group=1 means a None pulse and a real one
        can never land in the same group), this uses pulses_per_group=3 so a None pulse sits
        *inside* the same group as two real ones -- proving the group average is computed over
        only the pulses that actually had data (10.0, 12.0 -> mean 11.0), not diluted by
        treating the None pulse as a 0 V contribution (which would wrongly give 22/3 = 7.33)."""
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=11.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=3, num_groups=1, margin_v=1.0,
                                         consecutive_for_warning=1)

        with caplog.at_level('INFO'):
            tracker.add_pulse(None)
            tracker.add_pulse(_FakeVoltageMeasures([10.0]))
            tracker.add_pulse(_FakeVoltageMeasures([12.0]))

        info_lines = [r.message for r in caplog.records if r.levelname == 'INFO']
        assert any('averaged 11.00 V' in line for line in info_lines)
        assert not any(r.levelname == 'WARNING' for r in caplog.records)

    def test_add_pulse_never_raises_on_a_broken_measures_object(self, caplog):
        """unifus.FUSListener's callbacks cannot propagate exceptions to Python (see
        ExecListener.onPulseResult()'s own comment) -- add_pulse() must swallow any internal
        failure instead of letting it escape, or it would vanish silently and invisibly deep
        inside the driving system's own callback machinery."""
        ranges = [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)]
        tracker = VoltageFeedbackTracker(ranges, total_pulses=1, num_groups=1, margin_v=1.0,
                                         consecutive_for_warning=1)

        class _BrokenMeasures:
            def channelCount(self):
                raise RuntimeError('simulated hardware-layer failure')

        with caplog.at_level('DEBUG'):
            tracker.add_pulse(_BrokenMeasures())  # must not raise

        assert 'Voltage feedback tracking failed' in caplog.text


class TestExecListenerVoltageFeedback:

    def test_on_pulse_result_feeds_voltage_feedback_when_configured(self):
        """ExecListener.onPulseResult() only touches voltage_feedback when
        IGT._configure_voltage_feedback() has actually set one -- confirms the wiring without
        re-testing VoltageFeedbackTracker's own grouping logic (covered above)."""
        listener = ExecListener()
        tracker = VoltageFeedbackTracker(
            [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)],
            total_pulses=1, num_groups=1, margin_v=1.0, consecutive_for_warning=1)
        listener.voltage_feedback = tracker
        # _FakeMeasures (not _FakeVoltageMeasures) -- onPulseResult() also runs its own
        # pre-existing measurements-logging block against the same object, which needs the
        # full boardMeasureCount()/channelRawValue()/power() interface that fake provides.
        measures = _FakeMeasures(channel_measure_count=5)

        listener.onPulseResult(_fake_pulse_result(shared_measurements=measures))

        assert tracker._pulse_count == 1  # pylint: disable=protected-access

    def test_on_pulse_result_does_not_touch_voltage_feedback_when_none(self):
        """The default (see ExecListener.__init__) -- must not raise just because no tracker
        was ever configured for this execution."""
        listener = ExecListener()
        assert listener.voltage_feedback is None

        listener.onPulseResult(_fake_pulse_result(shared_measurements=None))  # must not raise


class TestVoltageFeedbackDispatcher:
    """VoltageFeedbackDispatcher (GitHub #137) -- routes pulses to one VoltageFeedbackTracker
    per interleaved protocol, cycling in a fixed round-robin order. See its own docstring for
    the (not yet hardware-verified) assumption this routing relies on."""

    def test_single_tracker_receives_every_pulse(self):
        """The single-protocol case (the overwhelming majority) must behave identically to
        using that one tracker directly -- every pulse routes to index 0, always."""
        tracker = VoltageFeedbackTracker(
            [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)],
            total_pulses=3, num_groups=1, margin_v=1.0, consecutive_for_warning=1)
        dispatcher = VoltageFeedbackDispatcher([tracker])

        for _ in range(3):
            dispatcher.add_pulse(_FakeVoltageMeasures([10.0]))

        assert tracker._pulse_count == 3  # pylint: disable=protected-access

    def test_cycles_pulses_across_trackers_in_round_robin_order(self):
        """Two interleaved protocols -- consecutive pulses must alternate between the two
        trackers (0, 1, 0, 1, ...), each seeing only every other pulse, matching how
        send_protocol() constructs pulse_train_seq as one Pulse per protocol repeated as a
        whole (see VoltageFeedbackDispatcher's own docstring)."""
        tracker_a = VoltageFeedbackTracker(
            [_channel_range('TRAN-A', 0, 1, expected_volt=20.0)],
            total_pulses=2, num_groups=1, margin_v=1.0, consecutive_for_warning=1)
        tracker_b = VoltageFeedbackTracker(
            [_channel_range('TRAN-B', 0, 1, expected_volt=0.5)],
            total_pulses=2, num_groups=1, margin_v=1.0, consecutive_for_warning=1)
        dispatcher = VoltageFeedbackDispatcher([tracker_a, tracker_b])

        for _ in range(4):  # two full alternating rounds
            dispatcher.add_pulse(_FakeVoltageMeasures([1.0]))

        # pylint: disable=protected-access
        assert tracker_a._pulse_count == 2
        assert tracker_b._pulse_count == 2

    def test_cycles_across_three_trackers_not_just_two(self, caplog):
        """The routing itself (self._pulse_count % len(self._trackers)) is written generically,
        not hardcoded to two -- proving it here for three protocols/transducers, not just
        reasoning about the modulo by inspection. Each pulse carries a distinct voltage so a
        misrouted pulse (e.g. tracker B getting one of tracker A's or C's values) would show up
        as a wrong averaged value, not just a wrong count."""
        tracker_a = VoltageFeedbackTracker(
            [_channel_range('TRAN-A', 0, 1, expected_volt=10.0)],
            total_pulses=2, num_groups=1, margin_v=0.5, consecutive_for_warning=1)
        tracker_b = VoltageFeedbackTracker(
            [_channel_range('TRAN-B', 0, 1, expected_volt=20.0)],
            total_pulses=2, num_groups=1, margin_v=0.5, consecutive_for_warning=1)
        tracker_c = VoltageFeedbackTracker(
            [_channel_range('TRAN-C', 0, 1, expected_volt=30.0)],
            total_pulses=2, num_groups=1, margin_v=0.5, consecutive_for_warning=1)
        dispatcher = VoltageFeedbackDispatcher([tracker_a, tracker_b, tracker_c])

        with caplog.at_level('INFO'):
            for _ in range(2):  # two full alternating rounds of A, B, C
                dispatcher.add_pulse(_FakeVoltageMeasures([10.0]))
                dispatcher.add_pulse(_FakeVoltageMeasures([20.0]))
                dispatcher.add_pulse(_FakeVoltageMeasures([30.0]))

        # pylint: disable=protected-access
        assert tracker_a._pulse_count == 2
        assert tracker_b._pulse_count == 2
        assert tracker_c._pulse_count == 2
        # Each tracker's own group average matches only the value it should have received --
        # if routing were wrong (e.g. tracker_b receiving tracker_a's 10.0 V pulses), this
        # would show up as a deviation big enough to trip the tight 0.5 V margin.
        assert not any(r.levelname == 'WARNING' for r in caplog.records)
