# -*- coding: utf-8 -*-
"""
Tests for ControlDrivingSystem.validate_protocol -- the single fixture-free,
hardware-free, config-free pure-logic target in the abstract driving-system
layer. It only needs a duck-typed object exposing the five timing
attributes it reads, so a plain SimpleNamespace stands in for a real
TUSProtocol.
"""
from types import SimpleNamespace

import pytest

from fus_driving_systems.control_driving_system import ControlDrivingSystem


class _ConcreteDrivingSystem(ControlDrivingSystem):
    """Minimal concrete subclass so the ABC's validate_protocol can be
    exercised directly -- the abstract methods themselves are out of
    scope here."""

    def connect(self, connect_info):
        raise NotImplementedError

    def send_protocol(self, *args, **kwargs):
        raise NotImplementedError

    def execute_protocol(self, *args, **kwargs):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError


@pytest.fixture
def driving_system():
    return _ConcreteDrivingSystem()


def _protocol(pulse_dur=1, pulse_rep_int=2, pulse_train_dur=10,
              pulse_train_rep_int=20, pulse_train_rep_dur=40, **overrides):
    """A internally-consistent baseline protocol stand-in, with any field
    overridable to violate exactly one validate_protocol check at a time."""
    values = dict(
        pulse_dur=pulse_dur,
        pulse_rep_int=pulse_rep_int,
        pulse_train_dur=pulse_train_dur,
        pulse_train_rep_int=pulse_train_rep_int,
        pulse_train_rep_dur=pulse_train_rep_dur,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_valid_protocol_has_no_errors(driving_system):
    assert driving_system.validate_protocol(_protocol()) == []


def test_pulse_train_dur_not_whole_multiple_of_pulse_rep_int(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_train_dur=10, pulse_rep_int=3))
    assert any("not a whole number" in e and "Pulse Train Duration" in e
               for e in errors)


def test_pulse_train_rep_dur_not_whole_multiple_of_pulse_train_rep_int(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_train_rep_dur=45, pulse_train_rep_int=20))
    assert any("not a whole number" in e and "Pulse Train Repetition" in e
               for e in errors)


def test_pulse_dur_greater_than_pulse_rep_int(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_dur=5, pulse_rep_int=2))
    assert any("Pulse Duration is not allowed to be higher" in e for e in errors)


def test_pulse_rep_int_greater_than_pulse_train_dur(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_train_dur=0, pulse_rep_int=5))
    assert any("Pulse Repetiton Interval is not allowed to be higher" in e
               for e in errors)


def test_pulse_train_dur_greater_than_pulse_train_rep_int(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_dur=1, pulse_rep_int=5, pulse_train_dur=25,
                  pulse_train_rep_int=20))
    assert any("Pulse Train Duration is not allowed to be higher" in e
               for e in errors)


def test_pulse_train_rep_int_greater_than_pulse_train_rep_dur(driving_system):
    errors = driving_system.validate_protocol(
        _protocol(pulse_dur=1, pulse_rep_int=5, pulse_train_dur=5,
                  pulse_train_rep_int=10, pulse_train_rep_dur=0))
    assert any("Pulse Train Repetition Interval is not allowed to be higher"
               in e for e in errors)


def test_zero_pulse_rep_int_is_a_validation_error(driving_system):
    """
    Regression test: pulse_rep_int=0 used to make validate_protocol divide
    by zero (pulse_train_dur / pulse_rep_int) before any of the friendly
    validation messages could fire, raising a raw ZeroDivisionError instead
    of a clean error message. Fixed by guarding the division.

    See test_zero_pulse_train_rep_int_is_a_validation_error below for the
    same class of bug at the second division in this function.
    """
    errors = driving_system.validate_protocol(_protocol(pulse_rep_int=0))
    assert any("Pulse Repetition Interval" in e and "not allowed to be 0" in e
               for e in errors)


def test_zero_pulse_train_rep_int_is_a_validation_error(driving_system):
    """
    Same fix as the pulse_rep_int=0 case above, but for the function's
    second division (pulse_train_rep_dur / pulse_train_rep_int): a raw
    ZeroDivisionError is now a clean validation error instead. Kept as a
    separate, explicit test rather than folded into the one above so both
    division sites are independently guarded against a future regression
    accidentally covering only one of them.
    """
    errors = driving_system.validate_protocol(_protocol(pulse_train_rep_int=0))
    assert any("Pulse Train Repetition Interval" in e and "not allowed to be 0" in e
               for e in errors)
