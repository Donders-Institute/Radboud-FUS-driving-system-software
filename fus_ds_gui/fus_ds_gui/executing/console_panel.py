# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from fus_driving_systems.config.logging_config import get_logger


class _QtLogHandler(QObject, logging.Handler):
    """Bridges a Python logging.Handler to a Qt signal, so ConsolePanel can show log records as
    they happen instead of polling. QObject must come first in the MRO for Qt's own metaclass
    to cooperate with logging.Handler's plain-Python one."""

    message_logged = Signal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record):
        self.message_logged.emit(self.format(record))


def _is_below_error(record):
    # Every FDSError in this GUI already gets its own explicit display (a panel's inline
    # error_label on the Planning side, a QMessageBox via show_fds_error() on the Executing
    # side); showing its ERROR-level log record here too would just duplicate it.
    return record.levelno < logging.ERROR


class ConsolePanel(QWidget):
    """
    A small, read-only, auto-scrolling log view fed by a logging.Handler attached to the same
    logger get_logger() returns: the "what is it doing right now" view (connection retries,
    send/execute progress) without needing to go find the log file.

    detach_handler() removes that handler again; called both from destroyed (best-effort
    cleanup once Qt actually gets around to destroying this widget) and explicitly by tests
    (get_logger() is a shared, module-level logger, so a handler left attached past a test's
    own teardown would keep firing into that test's now-deleted widget on every later test).
    logging.Logger.removeHandler() is a no-op if already removed, so calling this twice is
    always safe.

    fus_ds_gui never calls initialize_logger()/sync_logger() itself, so the shared logger's own
    effective level otherwise defaults to WARNING (no ancestor ever set it lower): INFO-level
    progress records, this panel's whole reason to exist, would be dropped by the logger itself
    before ever reaching this handler. __init__ lowers it to INFO if it's currently higher.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(500)  # avoid unbounded growth over a long session

        logger = get_logger()
        if logger.getEffectiveLevel() > logging.INFO:
            logger.setLevel(logging.INFO)

        self._handler = _QtLogHandler()
        self._handler.setLevel(logging.INFO)
        self._handler.addFilter(_is_below_error)
        self._handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))
        self._handler.message_logged.connect(self.text_edit.appendPlainText)
        logger.addHandler(self._handler)
        self.destroyed.connect(self.detach_handler)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_edit)

    def detach_handler(self):
        """Stops feeding this panel from the shared logger; see this class's own docstring."""

        get_logger().removeHandler(self._handler)
