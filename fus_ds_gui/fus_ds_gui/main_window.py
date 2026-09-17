# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import pathlib

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter

from fus_driving_systems.exceptions import FDSError

from fus_ds_gui.error_dialogs import show_fds_error
from fus_ds_gui.executing.executing_panel import ExecutingPanel
from fus_ds_gui.models import protocol_io
from fus_ds_gui.planning.planning_tab import PlanningTab

# fus_ds_gui/fus_ds_gui/main_window.py -> fus_ds_gui/ -> repo root -> example_protocols/
_EXAMPLE_PROTOCOLS_DIR = pathlib.Path(__file__).resolve().parents[2] / 'example_protocols'

_YAML_FILE_FILTER = "Protocol files (*.yaml *.yml)"

# Long enough for Qt's own deferred layout pass (triggered by the many setVisible()/
# setRowVisible() calls Demo mode's smaller form makes) to fully settle before
# _shrink_to_fit_content() reads sizeHint(): read too early and it still reflects the
# larger Advanced-mode layout, undoing the whole point of shrinking back down.
_SHRINK_DELAY_MS = 50


class MainWindow(QMainWindow):
    """
    Top-level window: Planning (build/load a protocol) and Executing (connect/send/execute it
    on real hardware) side by side in a resizable splitter, not tabs, so a researcher never
    loses sight of what's currently locked and ready to send while looking at the Executing
    panel (see PlanningTab.is_locked()'s own docstring for why that distinction exists at all).

    Drives PlanningTab's load_button/save_button/approve_button directly (see that class's own
    docstring for why). self._current_file_path, this class's own state, is separate from
    PlanningTab's in-progress protocol: switching driving systems, or otherwise rebuilding the
    Planning tab's own widgets, never touches it. Only an actual Load/Save does, since it's
    about "which file on disk are we talking about", not "what does the form show".
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Radboud FUS Driving System GUI")

        self.planning_tab = PlanningTab()
        self.executing_panel = ExecutingPanel(self.planning_tab)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.planning_tab)
        splitter.addWidget(self.executing_panel)

        self.setCentralWidget(splitter)

        self._current_file_path = None
        self.planning_tab.load_button.clicked.connect(self._on_load_protocol)
        self.planning_tab.save_button.clicked.connect(self._on_save_protocol)
        self.planning_tab.approve_button.clicked.connect(self._on_approve_current_file)

        self.planning_tab.validation_changed.connect(self._update_save_button_enabled)
        self.planning_tab.lock_changed.connect(self._update_save_button_enabled)
        self._update_save_button_enabled()

        self.planning_tab.advanced_mode_checkbox.toggled.connect(
            self._on_advanced_mode_toggled)
        self.planning_tab.equipment_panel.driving_system_changed.connect(
            self._schedule_shrink_to_fit)

    def _on_advanced_mode_toggled(self, advanced):
        """Demo mode's own form needs less height than Advanced mode's; see
        _schedule_shrink_to_fit()'s own docstring for why this is needed at all. Only leaving
        Advanced mode can ever need a shrink here, so growing (entering Advanced mode) skips
        it."""

        if not advanced:
            self._schedule_shrink_to_fit()

    def _schedule_shrink_to_fit(self, *_args):
        """A QMainWindow already on screen doesn't shrink itself back down once its content
        does (unlike growing, which it already handles on its own), a known Qt limitation, not
        something specific to this window. Switching to a driving system needing fewer slots
        (e.g. a "1x10 ch." variant after a "2x10 ch." one) can shrink the Planning tab's own
        content the same way leaving Advanced mode does, so both are wired here. Deferred via
        _SHRINK_DELAY_MS; see its own comment."""

        QTimer.singleShot(_SHRINK_DELAY_MS, self._shrink_to_fit_content)

    def _shrink_to_fit_content(self):
        self.resize(self.width(), self.centralWidget().sizeHint().height())

    def _update_save_button_enabled(self):
        """Disables Save until is_locked(): current_protocol() only reflects the last Applied
        state, so saving while unlocked would save stale values, not what's shown. is_locked()
        alone covers can_save() too, since it's only ever set from it (see PlanningTab's own
        docstrings). Same reasoning as Send's own gating, see
        ExecutingPanel._refresh_send_enabled()."""

        self.planning_tab.save_button.setEnabled(self.planning_tab.is_locked())

    def _on_load_protocol(self):
        # Defaults to example_protocols/ (the shipped examples are the most useful place to
        # start browsing from), falling back to the researcher's own home directory only if
        # that folder isn't present at all (e.g. a packaged install shipped without it).
        start_dir = (str(_EXAMPLE_PROTOCOLS_DIR) if _EXAMPLE_PROTOCOLS_DIR.is_dir()
                     else str(pathlib.Path.home()))
        self._load_from_dialog(start_dir)

    def _load_from_dialog(self, start_dir):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load protocol", start_dir, _YAML_FILE_FILTER)
        if not path:
            return  # Dialog cancelled.

        try:
            load_result = protocol_io.load(path)
            self.planning_tab.load_protocol(load_result)
        except FDSError as e:
            show_fds_error(self, e)
            return

        self._current_file_path = path
        # Approving hashes exactly the file on disk at self._current_file_path (see
        # protocol_io.approve()): if any slot in it failed to construct, that file is known to
        # be broken, so it must not be approvable until it's fixed and saved again.
        self.planning_tab.approve_button.setEnabled(not load_result.failed_slots)

    def _on_save_protocol(self):
        # save_button is disabled whenever is_locked() is False (see
        # _update_save_button_enabled()), so this only defends against a stale/forced trigger,
        # not the normal path. can_save() is checked here too, on top of is_locked() itself,
        # purely to tell the two ways of being unlocked apart for a more specific message.
        if not self.planning_tab.can_save():
            QMessageBox.warning(self, "Cannot save",
                                "Configure at least one transducer slot, and resolve any "
                                "validation problems, before saving.")
            return

        if not self.planning_tab.is_locked():
            QMessageBox.warning(self, "Cannot save",
                                "Click Apply on the Planning tab first: saving now would save "
                                "the last applied version, not what's currently shown.")
            return

        protocol = self.planning_tab.current_protocol()
        default_path = self._current_file_path or str(pathlib.Path.home() / 'protocol.yaml')
        path, _ = QFileDialog.getSaveFileName(
            self, "Save protocol", default_path, _YAML_FILE_FILTER)
        if not path:
            return  # Dialog cancelled.

        try:
            protocol_io.save(protocol, path)
        except FDSError as e:
            show_fds_error(self, e)
            return

        self._current_file_path = path
        self.planning_tab.approve_button.setEnabled(True)

    def _on_approve_current_file(self):
        try:
            protocol_io.approve(self._current_file_path)
        except FDSError as e:
            show_fds_error(self, e)
            return

        QMessageBox.information(self, "Approved",
                                f"Approved {self._current_file_path}.")
