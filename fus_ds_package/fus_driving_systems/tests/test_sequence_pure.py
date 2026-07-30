# -*- coding: utf-8 -*-
"""
Tests for the pure, hardware- and file-I/O-free functions in
fus_driving_systems.sequence: _check_parameter, validate_value,
safe_evaluate_pp and find_x_for_y_in_pp. extract_and_define_pp (the one
sequence-module function that touches the filesystem) is already covered
by test_fitparams_loading.py against the real in-package JSON files.
"""
import logging
from types import SimpleNamespace

import pytest
from scipy.interpolate import PPoly

from fus_driving_systems.sequence import (_check_parameter, find_x_for_y_in_pp,
                                          safe_evaluate_pp, validate_value)


# --- _check_parameter -------------------------------------------------

def test_check_parameter_passes_with_no_messages_when_all_checks_ok():
    messages = _check_parameter([], 5, 'Param', check_nonzero=True, check_num=True,
                                check_pos=True, check_bool=False)
    assert messages == []


def test_check_parameter_flags_zero_when_check_nonzero():
    messages = _check_parameter([], 0, 'Param', check_nonzero=True, check_num=False,
                                check_pos=False, check_bool=False)
    assert any('not allowed to be zero' in m for m in messages)


def test_check_parameter_flags_non_number_when_check_num():
    messages = _check_parameter([], 'not-a-number', 'Param', check_nonzero=False,
                                check_num=True, check_pos=False, check_bool=False)
    assert any('should be a number' in m for m in messages)


def test_check_parameter_flags_negative_when_check_pos():
    messages = _check_parameter([], -5, 'Param', check_nonzero=False, check_num=False,
                                check_pos=True, check_bool=False)
    assert any('not allowed to be negative' in m for m in messages)


def test_check_parameter_flags_non_bool_when_check_bool():
    messages = _check_parameter([], 'yes', 'Param', check_nonzero=False, check_num=False,
                                check_pos=False, check_bool=True)
    assert any('should be a boolean' in m for m in messages)


@pytest.mark.parametrize("value", [True, False])
def test_check_parameter_passes_when_check_bool_and_value_is_a_boolean(value):
    """
    Positive counterpart to test_check_parameter_flags_non_bool_when_check_bool:
    check_bool=True must NOT flag an actual bool. check_nonzero/check_pos are
    left False here to sidestep the (unrelated) quirk that False == 0 in
    Python, which would otherwise trip the check_nonzero branch for value=False.
    """
    messages = _check_parameter([], value, 'Param', check_nonzero=False, check_num=False,
                                check_pos=False, check_bool=True)
    assert messages == []


def test_check_parameter_appends_to_existing_messages():
    messages = _check_parameter(['existing error'], 0, 'Param', check_nonzero=True,
                                check_num=False, check_pos=False, check_bool=False)
    assert messages[0] == 'existing error'
    assert len(messages) == 2


# --- validate_value -----------------------------------------------------

def test_validate_value_returns_true_when_valid():
    assert validate_value(5, 'Param', check_num=True, check_pos=True,
                          check_nonzero=True, check_bool=False) is True


def test_validate_value_exits_when_invalid():
    with pytest.raises(SystemExit) as exc_info:
        validate_value('not-a-number', 'Param', check_num=True, check_pos=False,
                       check_nonzero=False, check_bool=False)
    assert 'Validation of input parameters failed.' in str(exc_info.value)


def test_validate_value_logs_every_message_before_exiting(caplog):
    """
    validate_value's for-loop logs every collected message via
    logger.critical BEFORE calling sys.exit -- pick a value that fails two
    independent checks at once (0 with check_nonzero+check_bool) so this
    actually proves "every message", not just "a message".
    """
    caplog.set_level(logging.CRITICAL)

    with pytest.raises(SystemExit):
        validate_value(0, 'Param', check_num=False, check_pos=False,
                       check_nonzero=True, check_bool=True)

    critical_messages = [r.message for r in caplog.records if r.levelno == logging.CRITICAL]
    assert any('not allowed to be zero' in m for m in critical_messages)
    assert any('should be a boolean' in m for m in critical_messages)


def test_validate_value_checks_each_item_when_check_list():
    assert validate_value([1, 2, 3], 'Param', check_num=True, check_pos=True,
                          check_nonzero=True, check_bool=False, check_list=True) is True


def test_validate_value_exits_when_check_list_and_not_a_list():
    with pytest.raises(SystemExit):
        validate_value(5, 'Param', check_num=True, check_pos=False,
                       check_nonzero=False, check_bool=False, check_list=True)


def test_validate_value_exits_when_check_list_and_item_invalid():
    with pytest.raises(SystemExit):
        validate_value([1, 'bad', 3], 'Param', check_num=True, check_pos=False,
                       check_nonzero=False, check_bool=False, check_list=True)


# --- safe_evaluate_pp -----------------------------------------------------

@pytest.fixture
def linear_pp():
    """pp(x) == x over the domain [0, 10]."""
    return PPoly(c=[[1.0], [0.0]], x=[0.0, 10.0], extrapolate=False)


def test_safe_evaluate_pp_below_range(linear_pp):
    value, status = safe_evaluate_pp(linear_pp, -1)
    assert value is None
    assert status == "below_range"


def test_safe_evaluate_pp_above_range(linear_pp):
    value, status = safe_evaluate_pp(linear_pp, 11)
    assert value is None
    assert status == "above_range"


def test_safe_evaluate_pp_in_range(linear_pp):
    value, status = safe_evaluate_pp(linear_pp, 5)
    assert value == pytest.approx(5.0)
    assert status == "in_range"


@pytest.mark.parametrize("boundary", [0, 10])
def test_safe_evaluate_pp_at_boundaries_is_in_range(linear_pp, boundary):
    value, status = safe_evaluate_pp(linear_pp, boundary)
    assert status == "in_range"
    assert value == pytest.approx(float(boundary))


# --- find_x_for_y_in_pp ---------------------------------------------------

@pytest.fixture
def decreasing_pp():
    """pp(x) == -x + 10 over the domain [0, 10]."""
    return PPoly(c=[[-1.0], [10.0]], x=[0.0, 10.0], extrapolate=False)


def test_find_x_for_y_finds_matching_x_when_increasing(linear_pp):
    x, found = find_x_for_y_in_pp(linear_pp, 5)
    assert found is True
    assert x == pytest.approx(5.0, abs=1e-5)


def test_find_x_for_y_finds_matching_x_when_decreasing(decreasing_pp):
    x, found = find_x_for_y_in_pp(decreasing_pp, 5)
    assert found is True
    assert x == pytest.approx(5.0, abs=1e-5)


@pytest.mark.parametrize("y_value", [-1, 11])
def test_find_x_for_y_out_of_range_when_increasing(linear_pp, y_value):
    x, found = find_x_for_y_in_pp(linear_pp, y_value)
    assert x is None
    assert found is False


@pytest.mark.parametrize("y_value", [-1, 11])
def test_find_x_for_y_out_of_range_when_decreasing(decreasing_pp, y_value):
    x, found = find_x_for_y_in_pp(decreasing_pp, y_value)
    assert x is None
    assert found is False


def test_find_x_for_y_respects_explicit_bounds(linear_pp):
    # Restrict the search to [2, 4]; 3 is inside that sub-range.
    x, found = find_x_for_y_in_pp(linear_pp, 3, x_min=2, x_max=4)
    assert found is True
    assert x == pytest.approx(3.0, abs=1e-5)


def test_find_x_for_y_returns_false_on_unexpected_exception():
    """Characterizes the broad except-Exception fallback: any failure while
    evaluating pp (not just an out-of-range value) is swallowed and reported
    as 'not found' rather than propagating."""
    broken_pp = SimpleNamespace(x=[0.0, 10.0])  # not callable -> TypeError inside
    x, found = find_x_for_y_in_pp(broken_pp, 5)
    assert x is None
    assert found is False
