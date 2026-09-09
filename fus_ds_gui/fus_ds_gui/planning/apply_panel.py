# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSError


class ApplyPanel(QWidget):
    """
    Base for a Planning-tab panel with an "Apply" button and an inline FDSError display,
    shared by SlotEditor and TimingPanel, which otherwise duplicated this exact boilerplate
    (flagged by pylint's own duplicate-code check). A subclass only needs to build its own
    widgets and implement _apply() (the actual backend call, which may raise FDSError); this
    class handles wiring the button, catching the error, and emitting applied().

    Signals:
        applied(): Emitted after every successful Apply.
    """

    applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply_clicked)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()

    def _apply(self):
        """Subclasses override this with their own backend call. May raise FDSError."""

        raise NotImplementedError

    def _on_apply_clicked(self):
        try:
            self._apply()
        except FDSError as e:
            get_logger().error("Could not apply %s: %s", type(self).__name__, e)
            self._show_error(str(e))
            return

        self._clear_error()
        self.applied.emit()

    def _show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()

    def _clear_error(self):
        self.error_label.clear()
        self.error_label.hide()
