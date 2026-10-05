# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ConnectionPanel(QWidget):
    """
    Driving system name, Connect/Disconnect buttons, and a status label. A thin composition
    widget: ExecutingPanel drives every visible state directly (text/enabled/visible), the same
    way PlanningTab already drives SlotEditor/TimingPanel's own public widgets rather than
    wrapping every state transition in a dedicated setter here.

    Signals:
        connect_clicked(): Emitted when the Connect button is clicked.
        disconnect_clicked(): Emitted when the Disconnect button is clicked.
    """

    connect_clicked = Signal()
    disconnect_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.driving_system_label = QLabel("No driving system selected")
        self.status_label = QLabel("Not connected")

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_clicked)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_clicked)
        self.disconnect_button.setEnabled(False)

        # Shown only while connecting to IGT: its own retry/backoff can legitimately take 10+
        # seconds, and without this the wait looks like the GUI has simply hung.
        self.igt_hint_label = QLabel("Connecting to IGT hardware can take up to ~10s.")
        self.igt_hint_label.setVisible(False)

        button_row = QHBoxLayout()
        button_row.addWidget(self.connect_button)
        button_row.addWidget(self.disconnect_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.driving_system_label)
        layout.addWidget(self.status_label)
        layout.addLayout(button_row)
        layout.addWidget(self.igt_hint_label)
