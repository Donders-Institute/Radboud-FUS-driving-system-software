# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import QCoreApplication, QEvent, QObject
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSpinBox, QComboBox


class WheelGuard(QObject):
    """
    Application-wide event filter: the mouse wheel never changes a spinbox or dropdown, focused
    or not (a field clicked earlier keeps focus, and scrolling over it would still change it).
    Over such a field the wheel scrolls the surrounding scroll area instead. Values change by
    typing, the arrow keys or the buttons.
    """

    def eventFilter(self, watched, event):  # pylint: disable=invalid-name
        if event.type() != QEvent.Type.Wheel or not isinstance(
                watched, (QAbstractSpinBox, QComboBox)):
            return False

        parent = watched.parentWidget()
        while parent is not None and not isinstance(parent, QAbstractScrollArea):
            parent = parent.parentWidget()
        if parent is not None:
            QCoreApplication.sendEvent(parent.viewport(), event)
        return True
