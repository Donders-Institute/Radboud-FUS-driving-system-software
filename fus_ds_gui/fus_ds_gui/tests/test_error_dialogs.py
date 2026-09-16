# -*- coding: utf-8 -*-
"""
Tests for error_dialogs.show_fds_error(). Every branch's own QMessageBox call is monkeypatched
out rather than actually shown: a real modal dialog would block the test suite waiting for a
click that never comes.
"""
from PySide6.QtWidgets import QApplication, QMessageBox

from fus_driving_systems.exceptions import (FDSConfigError, FDSHardwareError, FDSInternalError,
                                            FDSSafetyError, FDSValidationError)

from fus_ds_gui.error_dialogs import show_fds_error


def test_safety_error_shows_a_critical_dialog(qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *args: calls.append(args)))

    show_fds_error(None, FDSSafetyError('max pressure exceeded'))

    assert len(calls) == 1
    assert 'max pressure exceeded' in calls[0][-1]


def test_validation_error_shows_a_warning_dialog(qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(lambda *args: calls.append(args)))

    show_fds_error(None, FDSValidationError('bad value'))

    assert len(calls) == 1
    assert 'bad value' in calls[0][-1]


def test_hardware_error_shows_a_critical_dialog(qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *args: calls.append(args)))

    show_fds_error(None, FDSHardwareError('connection lost'))

    assert len(calls) == 1
    assert 'connection lost' in calls[0][-1]


def test_config_error_shows_a_critical_dialog_mentioning_ds_config(qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *args: calls.append(args)))

    show_fds_error(None, FDSConfigError('missing section'))

    assert len(calls) == 1
    assert 'missing section' in calls[0][-1]
    assert 'ds_config.ini' in calls[0][-1]


def test_internal_error_shows_a_dedicated_dialog_with_a_copy_button(qtbot, monkeypatch):
    """Distinct from the other subtypes: builds its own QMessageBox with a "Copy details"
    button, rather than a plain QMessageBox.critical() one-liner."""
    exec_calls = []
    monkeypatch.setattr(QMessageBox, 'exec', lambda self: exec_calls.append(self) or 0)

    show_fds_error(None, FDSInternalError('should never happen'))

    assert len(exec_calls) == 1
    box = exec_calls[0]
    assert 'bug in the software' in box.text()
    assert 'should never happen' in box.text()
    assert any(button.text() == 'Copy details' for button in box.buttons())


def _find_copy_button(box):
    return next(button for button in box.buttons() if button.text() == 'Copy details')


def test_internal_error_copy_button_copies_details_to_the_clipboard(qtbot, monkeypatch):
    # Simulates the researcher clicking "Copy details": clickedButton() would normally report
    # whichever button exec()'s real event loop saw clicked, not reachable here since exec()
    # itself is mocked out too, below.
    monkeypatch.setattr(QMessageBox, 'exec', lambda self: 0)
    monkeypatch.setattr(QMessageBox, 'clickedButton', _find_copy_button)

    show_fds_error(None, FDSInternalError('should never happen'))

    assert QApplication.clipboard().text() == 'should never happen'


def test_unknown_exception_falls_back_to_a_generic_critical_dialog(qtbot, monkeypatch):
    """FDSError itself (the plain base class, no subtype) or any other exception: still shown,
    never silently swallowed."""
    calls = []
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *args: calls.append(args)))

    show_fds_error(None, ValueError('not even an FDSError'))

    assert len(calls) == 1
    assert 'not even an FDSError' in calls[0][-1]
