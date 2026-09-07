# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from fus_ds_gui.planning.equipment_panel import EquipmentPanel


class PlanningTab(QWidget):
    """
    Build/load a protocol: equipment selection, transducer slots, timing, save/load. Only
    equipment selection exists so far; the rest is built in later phases.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.equipment_panel = EquipmentPanel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.equipment_panel)
        layout.addStretch()
