# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSpinBox, QVBoxLayout, QWidget

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.utils import get_config_value

ONE_PULSE_TRAIN = get_config_value(get_logger(), config, 'Trigger', 'Option.pulse_train',
                                   'TriggerOnePulseTrain')
WHOLE_PROTOCOL = get_config_value(get_logger(), config, 'Trigger', 'Option.whole_protocol',
                                  'TriggerWholeProtocol')


class TriggerPanel(QWidget):
    """
    "Use external trigger" checkbox plus mode/n_triggers controls, and a waiting-for-trigger
    status label. A thin composition widget, see ConnectionPanel's own docstring for why.

    trigger_mode_combo/n_triggers_spin only matter for driving systems with selectable trigger
    modes; ExecutingPanel shows/hides them per ProtocolBuilder.supports_trigger_options().

    Signals:
        settings_changed(): Emitted whenever the checkbox or the mode combo changes, so
            ExecutingPanel can refresh visibility/labels from one place.
    """

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.use_trigger_checkbox = QCheckBox("Use external trigger")
        self.use_trigger_checkbox.toggled.connect(self.settings_changed)

        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems([WHOLE_PROTOCOL, ONE_PULSE_TRAIN])
        self.trigger_mode_combo.currentIndexChanged.connect(self.settings_changed)

        self.n_triggers_spin = QSpinBox()
        self.n_triggers_spin.setRange(1, 999)
        self.n_triggers_spin.setValue(1)

        # Elapsed time, not a countdown: there's no known duration to count down from until
        # the external trigger actually arrives.
        self.waiting_label = QLabel()
        self.waiting_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.use_trigger_checkbox)
        layout.addWidget(self.trigger_mode_combo)
        layout.addWidget(self.n_triggers_spin)
        layout.addWidget(self.waiting_label)

    def trigger_option(self):
        """Returns: str: The chosen trigger option, for IGT.wait_for_trigger()."""

        return self.trigger_mode_combo.currentText()

    def n_triggers(self):
        """Returns: int or None: n_triggers if the chosen mode needs one, else None."""

        if self.trigger_option() == ONE_PULSE_TRAIN:
            return self.n_triggers_spin.value()
        return None
