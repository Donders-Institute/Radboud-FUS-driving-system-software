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


def test_an_error_message_is_not_shown(qtbot):
    """FDSErrors already get their own explicit display elsewhere (an inline error_label on the
    Planning side, a QMessageBox on the Executing side); showing the same message here too
    would just duplicate it."""
    panel = ConsolePanel()
    qtbot.addWidget(panel)

    get_logger().error("Could not apply SlotEditor: something went wrong")

    assert panel.text_edit.toPlainText() == ""
    panel.detach_handler()
