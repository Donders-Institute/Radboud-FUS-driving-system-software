# -*- coding: utf-8 -*-
"""Smoke tests for MainWindow: launches with exactly the two documented tabs."""
from fus_ds_gui.executing.executing_tab import ExecutingTab
from fus_ds_gui.main_window import MainWindow
from fus_ds_gui.planning.planning_tab import PlanningTab


def test_launches_with_planning_and_executing_tabs(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    tabs = window.centralWidget()

    assert tabs.count() == 2
    assert tabs.tabText(0) == "Planning"
    assert tabs.tabText(1) == "Executing"
    assert isinstance(tabs.widget(0), PlanningTab)
    assert isinstance(tabs.widget(1), ExecutingTab)
