# -*- coding: utf-8 -*-
"""
Tests for ConsolePanel. Every panel using get_logger() calls detach_handler() explicitly in
teardown (see ConsolePanel's own docstring on why destroyed alone isn't good enough here).
"""
from fus_driving_systems.config.logging_config import get_logger

from fus_ds_gui.executing.console_panel import ConsolePanel


def test_an_info_message_is_shown(qtbot):
    panel = ConsolePanel()
    qtbot.addWidget(panel)

    get_logger().info("connecting to COM1")

    assert "connecting to COM1" in panel.text_edit.toPlainText()
    panel.detach_handler()


def test_an_error_message_is_shown(qtbot):
    """ERROR records report things nothing else shows, such as why a connection attempt failed."""
    panel = ConsolePanel()
    qtbot.addWidget(panel)

    get_logger().error("Exception during connection: timed out")

    assert "Exception during connection: timed out" in panel.text_edit.toPlainText()
    panel.detach_handler()


def test_a_critical_message_is_not_shown(qtbot):
    """FDSErrors are logged as CRITICAL and already get their own explicit display elsewhere (an
    inline error_label on the Planning side, a QMessageBox on the Executing side); showing the
    same message here too would just duplicate it."""
    panel = ConsolePanel()
    qtbot.addWidget(panel)

    get_logger().critical("FDSHardwareError: Not connected")

    assert panel.text_edit.toPlainText() == ""
    panel.detach_handler()


def test_replay_shows_earlier_records_in_the_same_format_and_skips_critical(qtbot):
    """Start-up records are logged before the panel exists (see app.main())."""
    import logging

    panel = ConsolePanel()
    qtbot.addWidget(panel)
    make = logging.LogRecord
    records = [make('x', logging.INFO, __file__, 1, 'version 1.2.3', None, None),
               make('x', logging.WARNING, __file__, 1, 'MODIFIED limit', None, None),
               make('x', logging.ERROR, __file__, 1, 'an error', None, None),
               make('x', logging.CRITICAL, __file__, 1, 'a critical error', None, None),
               make('x', logging.DEBUG, __file__, 1, 'debug detail', None, None)]

    panel.replay(records)

    text = panel.text_edit.toPlainText()
    assert 'INFO version 1.2.3' in text and 'WARNING MODIFIED limit' in text
    assert 'ERROR an error' in text
    assert 'a critical error' not in text and 'debug detail' not in text
    panel.detach_handler()
