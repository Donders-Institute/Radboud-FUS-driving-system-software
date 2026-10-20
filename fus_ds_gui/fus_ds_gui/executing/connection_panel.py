# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)
from serial.tools import list_ports


class ConnectionPanel(QWidget):
    """
    Driving system name, a COM port field (only for a driving system on a serial port), Connect/
    Disconnect buttons, and a status label. A thin composition
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

        # Only for a driving system on a serial port: the TPO can be on another COM port than the
        # one in ds_config.ini, depending on the computer. Editable, so a port can be typed too.
        self.com_port_label = QLabel("COM port:")
        self.com_port_combo = QComboBox()
        self.com_port_combo.setEditable(True)
        self.com_port_combo.setToolTip(
            "The COM port of the driving system. Pre-filled with the one in ds_config.ini; "
            "choose or type another one if it is on a different port on this computer.")
        self.set_com_port_visible(False)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_clicked)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_clicked)
        self.disconnect_button.setEnabled(False)

        # Shown only while connecting to IGT: its own retry/backoff can legitimately take 10+
        # seconds, and without this the wait looks like the GUI has simply hung.
        self.igt_hint_label = QLabel("Connecting to IGT hardware can take up to ~10s.")
        self.igt_hint_label.setVisible(False)

        com_port_row = QHBoxLayout()
        com_port_row.addWidget(self.com_port_label)
        com_port_row.addWidget(self.com_port_combo, stretch=1)

        button_row = QHBoxLayout()
        button_row.addWidget(self.connect_button)
        button_row.addWidget(self.disconnect_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.driving_system_label)
        layout.addWidget(self.status_label)
        layout.addLayout(com_port_row)
        layout.addLayout(button_row)
        layout.addWidget(self.igt_hint_label)

    def set_com_port_visible(self, visible):
        """Shows or hides the COM port label and field together."""

        self.com_port_label.setVisible(visible)
        self.com_port_combo.setVisible(visible)

    def show_com_port(self, default_port):
        """Shows the COM port field, offering default_port (first, selected) and the ports this
        computer has, and leaving room to type another one."""

        try:
            detected = [port.device for port in list_ports.comports()]
        except OSError:
            detected = []
        ports = [default_port] + [port for port in detected if port != default_port]
        self.com_port_combo.clear()
        self.com_port_combo.addItems(ports)
        self.com_port_combo.setCurrentIndex(0)
        self.set_com_port_visible(True)

    def com_port(self):
        """The COM port as shown: without surrounding whitespace, upper case, and a bare number
        (9) completed to COM9."""

        port = self.com_port_combo.currentText().strip().upper()
        return f'COM{port}' if port.isdigit() else port
