# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import pathlib

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTabWidget

from fus_driving_systems.exceptions import FDSError

from fus_ds_gui.error_dialogs import show_fds_error
from fus_ds_gui.executing.executing_tab import ExecutingTab
from fus_ds_gui.models import protocol_io
from fus_ds_gui.planning.planning_tab import PlanningTab

# fus_ds_gui/fus_ds_gui/main_window.py -> fus_ds_gui/ -> repo root -> example_protocols/
_EXAMPLE_PROTOCOLS_DIR = pathlib.Path(__file__).resolve().parents[2] / 'example_protocols'

_YAML_FILE_FILTER = "Protocol files (*.yaml *.yml)"


class MainWindow(QMainWindow):
    """
    Top-level window: a Planning tab (build/load a protocol) and an Executing tab (connect/
    send/execute it on real hardware). Kept deliberately thin; each tab owns its own widgets.

    The File menu's own current-file tracking (self._current_file_path) is separate from
    PlanningTab's own in-progress protocol: switching driving systems, or otherwise rebuilding
    the Planning tab's own widgets, never touches it. Only an actual Load/Save does, since it's
    about "which file on disk are we talking about", not "what does the form show".
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

        self._current_file_path = None
        self._build_file_menu()

        self.planning_tab.validation_changed.connect(self._update_save_action_enabled)
        self._update_save_action_enabled()

    def _build_file_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        self._load_action = file_menu.addAction("&Load protocol...", self._on_load_protocol)
        self._save_action = file_menu.addAction("&Save protocol...", self._on_save_protocol)
        file_menu.addSeparator()
        self._approve_action = file_menu.addAction(
            "&Approve current file", self._on_approve_current_file)
        self._approve_action.setEnabled(False)

    def _update_save_action_enabled(self):
        """Disables Save outright while PlanningTab.can_save() is False (no slot configured
        yet, or the protocol currently fails its own validation, see that method's own
        docstring for why), rather than only catching this once the researcher already clicked
        it."""

        self._save_action.setEnabled(self.planning_tab.can_save())

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
        self._approve_action.setEnabled(not load_result.failed_slots)

    def _on_save_protocol(self):
        # The Save action is disabled whenever this is False (see _update_save_action_enabled()),
        # so this only defends against a stale/forced trigger, not the normal path.
        if not self.planning_tab.can_save():
            QMessageBox.warning(self, "Cannot save",
                                "Configure at least one transducer slot, and resolve any "
                                "validation problems, before saving.")
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
        self._approve_action.setEnabled(True)

    def _on_approve_current_file(self):
        try:
            protocol_io.approve(self._current_file_path)
        except FDSError as e:
            show_fds_error(self, e)
            return

        QMessageBox.information(self, "Approved",
                                f"Approved {self._current_file_path}.")
