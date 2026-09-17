# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ExecutionPanel(QWidget):
    """
    Send/Execute buttons, the sent-protocol summary, and an estimated execution countdown. A
    thin composition widget, see ConnectionPanel's own docstring for why.

    sent_protocol_label always shows the protocol that was actually last sent (via str(), the
    same textual summary the core package itself already produces), separate from whatever the
    Planning tab currently shows: the two can diverge if the researcher keeps editing after
    sending, and this panel must always answer "what did I actually just send," not "what does
    the form currently say."

    Signals:
        send_clicked(): Emitted when the Send button is clicked.
        execute_clicked(): Emitted when the Execute button is clicked.
    """

    send_clicked = Signal()
    execute_clicked = Signal()

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

        # Labeled as an estimate throughout: IGT only confirms completion once
        # execute_protocol() itself returns; Sonic Concepts gives no ground truth at all (see
        # ProtocolBuilder.uses_pulse_train_repetition()'s own docstring on that asymmetry).
        self.countdown_label = QLabel()
        self.countdown_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.lock_hint_label)
        layout.addWidget(self.sent_protocol_label)
        layout.addWidget(self.send_button)
        layout.addWidget(self.execute_button)
        layout.addWidget(self.countdown_label)
