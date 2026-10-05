# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QWidget

from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSError


class ApplyPanel(QWidget):
    """
    Base for a Planning-tab panel with an inline FDSError display, shared by SlotEditor and
    TimingPanel, which otherwise duplicated this exact boilerplate (flagged by pylint's own
    duplicate-code check). A subclass only needs to build its own widgets and implement
    _apply() (the actual backend call, which may raise FDSError); this class handles catching
    the error and emitting applied(). PlanningTab's own shared Apply button (not owned by this
    class or any subclass) is what actually calls try_apply() on every panel at once.

    Signals:
        applied(): Emitted after every successful Apply.
        changed(): Emitted by a subclass whenever any of its own value-bearing widgets changes,
            so PlanningTab can unlock a previously-applied protocol the moment a panel no
            longer matches it (see PlanningTab's own lock/unlock docstring). Declared here so
            both subclasses share one definition; each subclass wires its own widgets to it.
    """

    applied = Signal()
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()

    def _apply(self):
        """Subclasses override this with their own backend call. May raise FDSError."""

        raise NotImplementedError

    def try_apply(self):
        """Attempts _apply(), updating error_label either way. Returns True on success, False
        on a caught FDSError, so a caller applying several panels at once (see PlanningTab's own
        shared Apply button) can tell which of them actually succeeded."""

        try:
            self._apply()
        except FDSError as e:
            get_logger().error("Could not apply %s: %s", type(self).__name__, e)
            self._show_error(str(e))
            return False

        self._clear_error()
        self.applied.emit()
        return True

    def _show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()

    def _clear_error(self):
        self.error_label.clear()
        self.error_label.hide()
