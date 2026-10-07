# -*- coding: utf-8 -*-
"""Tests for the helpers that log a message and raise (or are about to raise) an FDSError."""
import pytest

from fus_driving_systems.exceptions import (FDSHardwareError, FDSSafetyError, FDSValidationError,
                                            log_critical, raise_logged)


def _fails_validation():
    """Fails through raise_logged(), to check which function the log record is attributed to."""
    raise_logged(FDSValidationError, 'the value is out of range')


def test_raise_logged_raises_the_class_with_the_message(caplog):
    """The raised exception is an instance of the given class, carrying the message."""
    with caplog.at_level('CRITICAL'):
        with pytest.raises(FDSValidationError, match='the value is out of range'):
            _fails_validation()


def test_raise_logged_logs_the_class_name_from_the_class_itself(caplog):
    """The prefix is taken from the class, not typed at the call site."""
    with caplog.at_level('CRITICAL'):
        with pytest.raises(FDSSafetyError):
            raise_logged(FDSSafetyError, 'too high')

    assert 'FDSSafetyError: too high' in caplog.text


def test_raise_logged_attributes_the_log_record_to_the_caller(caplog):
    """Not to raise_logged() itself, so the log's function and line point at the failing code."""
    with caplog.at_level('CRITICAL'):
        with pytest.raises(FDSValidationError):
            _fails_validation()

    record = caplog.records[-1]
    assert record.funcName == '_fails_validation'
    assert record.module == 'test_exceptions'


def test_raise_logged_chains_the_cause_when_given():
    """cause becomes __cause__, like raise ... from cause."""
    cause = OSError('port closed')

    with pytest.raises(FDSHardwareError) as info:
        raise_logged(FDSHardwareError, 'lost the connection', cause=cause)

    assert info.value.__cause__ is cause


def test_raise_logged_without_a_cause_keeps_the_implicit_context():
    """No 'from None': the exception being handled stays visible as the context."""
    with pytest.raises(FDSValidationError) as info:
        try:
            raise KeyError('inner')
        except KeyError:
            raise_logged(FDSValidationError, 'outer')

    assert info.value.__suppress_context__ is False
    assert isinstance(info.value.__context__, KeyError)


def test_log_critical_logs_the_class_name_without_raising(caplog):
    """For sites that log several messages before one exception is raised."""
    with caplog.at_level('CRITICAL'):
        log_critical(FDSValidationError, 'first problem')

    assert 'FDSValidationError: first problem' in caplog.text
