# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtWidgets import QMainWindow, QTabWidget

from fus_ds_gui.executing.executing_tab import ExecutingTab
from fus_ds_gui.planning.planning_tab import PlanningTab


class MainWindow(QMainWindow):
    """
    Top-level window: a Planning tab (build/load a protocol) and an Executing tab (connect/
    send/execute it on real hardware). Kept deliberately thin; each tab owns its own widgets.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Radboud FUS Driving System GUI")

        self.planning_tab = PlanningTab()
        self.executing_tab = ExecutingTab()

        tabs = QTabWidget()
        tabs.addTab(self.planning_tab, "Planning")
        tabs.addTab(self.executing_tab, "Executing")

        self.setCentralWidget(tabs)
