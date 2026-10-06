# -*- coding: utf-8 -*-
"""
Hardware tests for the IGT driving system, with a dummy load attached (see conftest.py for how
to run them and for the safety limits). They automate the parts of the hardware test plan that
need no human in the loop. Not covered here, because they need hands: replugging the connection,
and the external trigger modes.
"""
import logging
import re
import threading
import time

import pytest

from fus_driving_systems.exceptions import FDSHardwareError

# A pulse train every 400 ms for 2 s: 5 trains of 4 pulses each.
TIMING = dict(pulse_rep_int=50, pulse_train_dur=200, pulse_train_rep_int=400,
              pulse_train_rep_dur=2)

# The repetition duration must be a whole multiple of the interval: 1 s and 3 s fit 500 ms.
WHOLE_SECOND_TIMING = dict(TIMING, pulse_train_rep_int=500)

SUCCESS_MESSAGE = 'Protocol executed successfully.'

# One of the package's own voltage feedback lines, with a calibration to compare against:
# 'Voltage feedback (group 2): <serial> averaged 2.70 V (expected 2.73 V, -0.03 V).'
EXPECTED_VOLTAGE_LINE = re.compile(
    r'Voltage feedback \(group \d+\): .* averaged (-?[\d.]+) V \(expected (-?[\d.]+) V')


def _messages(records):
    return [record.getMessage() for record in records]


def _errors(records):
    return [record.getMessage() for record in records if record.levelno >= logging.ERROR]


def _timed(function):
    start = time.monotonic()
    function()
    return (time.monotonic() - start) * 1000.0


def test_send_and_execute_with_native_options(igt, make_protocol, fds_log):
    """The electrical-only route: native amplitude and focus, no calibration involved."""
    protocol = make_protocol(**TIMING)

    igt.send_protocol([protocol])
    assert igt.is_protocol_sent(0)
    igt.execute_protocol([protocol])

    assert SUCCESS_MESSAGE in _messages(fds_log)
    assert not _errors(fds_log)


def test_voltage_feedback_reports_real_voltage(igt, make_protocol, fds_log):
    """The driving system measures the voltage per channel, whatever is on the other end of the
    cable, and the package reports it in batches (GitHub #137)."""
    protocol = make_protocol(**dict(TIMING, pulse_train_rep_dur=4))

    igt.send_protocol([protocol])
    igt.execute_protocol([protocol])

    pattern = re.compile(r'Voltage feedback \(group \d+\): .* averaged ([\d.]+) V')
    voltages = [float(match.group(1)) for message in _messages(fds_log)
                if (match := pattern.search(message))]
    assert voltages, 'No voltage feedback lines were logged.'
    assert max(voltages) > 0, f'The driving system reported no voltage at all: {voltages}'


def test_measured_voltage_follows_the_calibration(igt, make_protocol, hw_config, fds_log):
    """The electrical half of the calibration: the voltage the driving system really puts out
    must match what the calibration curve predicts for the amplitude asked for, and must go up
    with the amplitude. Only runs for a driving system and transducer with an active calibration
    (otherwise there is no expected voltage); it says nothing about acoustic pressure or focus,
    which needs a hydrophone. The tolerance is relative: the amplitude is capped low for safety,
    where the expected voltage is smaller than the package's own warning margin."""
    tolerance = hw_config.voltage_tolerance_percent / 100.0
    mean_measured = {}

    for amplitude in (hw_config.max_amplitude / 2, hw_config.max_amplitude):
        protocol = make_protocol(amplitude=amplitude, **dict(TIMING, pulse_train_rep_dur=4))
        if protocol.slots[0].volt is None:
            pytest.skip('No active calibration for this driving system and transducer, so '
                        'there is no expected voltage to compare against.')

        logged_before = len(fds_log)
        igt.send_protocol([protocol])
        igt.execute_protocol([protocol])

        pairs = [(float(match.group(1)), float(match.group(2)))
                 for message in _messages(fds_log[logged_before:])
                 if (match := EXPECTED_VOLTAGE_LINE.search(message))]
        assert pairs, f'No voltage feedback with an expected value was logged at {amplitude}%.'
        for measured, expected in pairs:
            assert abs(measured - expected) <= tolerance * expected, (
                f'At {amplitude}%: measured {measured:.2f} V, calibration expects '
                f'{expected:.2f} V (more than {hw_config.voltage_tolerance_percent:g}% off).')
        mean_measured[amplitude] = sum(measured for measured, _ in pairs) / len(pairs)

    low, high = sorted(mean_measured)
    assert mean_measured[high] > mean_measured[low], (
        f'Voltage did not rise with amplitude: {mean_measured}')


def test_two_buffers_hold_independent_protocols(igt, make_protocol, fds_log):
    """Each buffer runs the protocol that was sent to it, not the other one."""
    short = make_protocol(**dict(WHOLE_SECOND_TIMING, pulse_train_rep_dur=1))
    long = make_protocol(**dict(WHOLE_SECOND_TIMING, pulse_train_rep_dur=3))

    igt.send_protocol([short], buffer_num=0)
    igt.send_protocol([long], buffer_num=1)
    assert igt.is_protocol_sent(0) and igt.is_protocol_sent(1)
    expected = {buffer: igt.sent_protocols[buffer]['total_protocol_duration_ms']
                for buffer in (0, 1)}
    assert expected[1] > expected[0]

    elapsed_long = _timed(lambda: igt.execute_protocol([long], buffer_num=1))
    elapsed_short = _timed(lambda: igt.execute_protocol([short], buffer_num=0))

    assert elapsed_long >= 0.9 * expected[1]
    assert elapsed_short >= 0.9 * expected[0]
    assert elapsed_long > elapsed_short
    assert not _errors(fds_log)


def test_interleaved_protocols_run_for_the_alternating_duration(igt, make_protocol, fds_log):
    """Two protocols sharing one buffer: the whole group runs for total_alternating_duration."""
    protocol_a = make_protocol(pulse_dur=45, pulse_rep_int=100)
    protocol_b = make_protocol(pulse_dur=45, pulse_rep_int=100)
    total_ms = 3000

    igt.send_protocol([protocol_a, protocol_b], total_ms)
    elapsed = _timed(lambda: igt.execute_protocol([protocol_a, protocol_b], total_ms))

    assert 0.9 * total_ms <= elapsed <= total_ms + 5000
    assert SUCCESS_MESSAGE in _messages(fds_log)
    assert not _errors(fds_log)


def test_abort_from_another_thread_while_executing(igt, make_protocol):
    """abort() while another thread is blocked inside execute_protocol(): the call must return,
    execution must stop early, and the same connection must still work afterwards. Whether
    concurrent native calls are safe is exactly what this checks (see GitHub #126)."""
    long_run_s = 8
    protocol = make_protocol(**dict(TIMING, pulse_train_rep_dur=long_run_s))
    igt.send_protocol([protocol])

    def execute():
        try:
            igt.execute_protocol([protocol])
        except FDSHardwareError:
            pass  # the driving system may report an aborted execution as a failure

    executing = threading.Thread(target=execute)
    start = time.monotonic()
    executing.start()
    time.sleep(1.5)

    igt.abort()

    executing.join(timeout=10)
    assert not executing.is_alive(), 'execute_protocol() never returned after abort().'
    assert time.monotonic() - start < 0.8 * long_run_s, 'Execution was not stopped early.'
    assert igt.is_connected()

    follow_up = make_protocol(**dict(WHOLE_SECOND_TIMING, pulse_train_rep_dur=1))
    igt.send_protocol([follow_up])
    igt.execute_protocol([follow_up])
