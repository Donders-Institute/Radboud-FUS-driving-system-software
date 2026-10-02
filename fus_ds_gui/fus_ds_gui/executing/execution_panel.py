# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from fus_ds_gui.styles import ACCENT_BUTTON_STYLE


class ExecutionPanel(QWidget):
    """
    Send/Execute buttons, the sent-protocol status, and an estimated execution countdown. A
    thin composition widget, see ConnectionPanel's own docstring for why.

    sent_protocol_label only ever shows a plain "sent"/"not sent yet" status: the driving
    system's own send_protocol()/execute_protocol() already log the real details to the
    console panel, so repeating them here would just be a duplicate to keep in sync.

    Signals:
        send_clicked(): Emitted when the Send button is clicked.
        execute_clicked(): Emitted when the Execute/Arm button is clicked.
        abort_clicked(): Emitted when the Abort button is clicked.
    """

    send_clicked = Signal()
    execute_clicked = Signal()
    abort_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Replaces the Send button's own spot whenever the Planning tab isn't locked, so it's
        # never ambiguous why Send is unavailable.
        self.lock_hint_label = QLabel("Protocol not locked. Click Apply on the Planning tab.")

        self.sent_protocol_label = QLabel("Nothing sent yet.")
        self.sent_protocol_label.setWordWrap(True)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_clicked)
        self.send_button.setEnabled(False)

        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_clicked)
        self.execute_button.setEnabled(False)
        self.execute_button.setStyleSheet(ACCENT_BUTTON_STYLE)

        # Runs on its own dedicated worker thread (see ExecutingPanel), so it can reach the
        # hardware even while Execute/Arm is stuck in a blocking call on the main one.
        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.abort_clicked)
        self.abort_button.setEnabled(False)

        # Labeled as an estimate while counting down: IGT only confirms completion once
        # execute_protocol() itself returns; Sonic Concepts gives no ground truth at all (see
        # ProtocolBuilder.uses_pulse_train_repetition()'s own docstring on that asymmetry).
        # Stays visible once done too (text becomes "Execution complete."), so finishing is
        # never just a countdown silently disappearing.
        self.countdown_label = QLabel()
        self.countdown_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.lock_hint_label)
        layout.addWidget(self.sent_protocol_label)
        layout.addWidget(self.send_button)
        layout.addWidget(self.execute_button)
        layout.addWidget(self.abort_button)
        layout.addWidget(self.countdown_label)
