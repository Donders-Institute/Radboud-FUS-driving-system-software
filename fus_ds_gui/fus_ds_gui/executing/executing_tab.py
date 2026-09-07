# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ExecutingTab(QWidget):
    """
    Connect/send/execute a protocol on real hardware. Empty placeholder until Phase 4 builds
    the connection/execution controls.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Executing tab, not yet implemented."))
        layout.addStretch()
