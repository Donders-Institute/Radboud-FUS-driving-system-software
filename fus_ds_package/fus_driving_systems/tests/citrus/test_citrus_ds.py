# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.citrus.citrus_ds.CITRUS.

connect() instantiates serial.Serial() inline with no injection seam, so
connect() tests go through the mock_serial fixture (patches the class).
execute_protocol()/disconnect() don't need connect() at all -- they just
read/write whatever object sits in self.ser_bitsi, so those tests assign a
plain mocker.Mock() directly, which is simpler than patching the constructor.
"""
from types import SimpleNamespace

import pytest

from fus_driving_systems.citrus.citrus_ds import CITRUS


def _valid_protocol(**overrides):
    values = dict(
        pulse_dur=1,
        pulse_rep_int=2,
        pulse_train_dur=10,
        pulse_train_rep_int=10,
        pulse_train_rep_dur=10,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_connect_configures_and_opens_serial_port(mock_serial):
    citrus = CITRUS()

    citrus.connect("COM5")

    assert mock_serial.baudrate == 115200
    assert mock_serial.port == "COM5"
    assert mock_serial.bytesize == 8
    assert mock_serial.parity == 'N'
    assert mock_serial.stopbits == 1
    assert mock_serial.timeout == 1
    mock_serial.open.assert_called_once()
    assert citrus.connected is True


def test_execute_protocol_writes_expected_trigger_byte(mocker):
    citrus = CITRUS()
    citrus.ser_bitsi = mocker.Mock()
    mocker.patch("fus_driving_systems.citrus.citrus_ds.time.sleep")

    citrus.execute_protocol(mocker.Mock())

    citrus.ser_bitsi.write.assert_called_once_with(b'\x20')
    citrus.ser_bitsi.flush.assert_called_once()


def test_execute_protocol_sleeps_after_triggering(mocker):
    citrus = CITRUS()
    citrus.ser_bitsi = mocker.Mock()
    mock_sleep = mocker.patch("fus_driving_systems.citrus.citrus_ds.time.sleep")

    citrus.execute_protocol(mocker.Mock())

    mock_sleep.assert_called_once_with(0.7)


def test_send_protocol_does_not_raise():
    """send_protocol's own hardware-facing logic is currently a stub (just
    logs), but it now validates the protocol first (see
    test_send_protocol_exits_when_validation_produces_errors below)."""
    citrus = CITRUS()
    citrus.send_protocol(_valid_protocol())  # must not raise


def test_send_protocol_exits_when_validation_produces_errors():
    """Regression test: send_protocol previously never called
    validate_protocol at all, so a malformed protocol would silently be
    accepted instead of failing loudly like IGT/SonicConcepts already do."""
    citrus = CITRUS()

    with pytest.raises(SystemExit):
        citrus.send_protocol(_valid_protocol(pulse_train_dur=11))


def test_disconnect_closes_serial_port_and_marks_disconnected(mocker):
    citrus = CITRUS()
    citrus.ser_bitsi = mocker.Mock()

    citrus.disconnect()

    citrus.ser_bitsi.close.assert_called_once()
    assert citrus.connected is False


def test_disconnect_before_connect_is_a_no_op():
    """
    Regression test for a real bug: CITRUS used to never set self.ser_bitsi
    in __init__ (it was only ever assigned inside connect()), so
    disconnect()'s 'if self.ser_bitsi is not None' guard assumed the
    attribute already existed. Calling disconnect() on a freshly constructed
    CITRUS that was never connected raised AttributeError instead of a
    friendly no-op. Fixed by initializing self.ser_bitsi = None in __init__.
    """
    citrus = CITRUS()

    citrus.disconnect()

    assert citrus.connected is False
