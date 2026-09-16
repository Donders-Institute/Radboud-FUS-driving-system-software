# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

from fus_driving_systems import driving_system
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSError

# CITRUS is excluded from the GUI for v1: it was built as a minimal MVP with no direct SDK
# connection, unlike IGT/SonicConcepts. This is a GUI-side decision, not a config change, so
# ds_config.ini's own 'active?' flag for CITRUS_V2 is left untouched.
_EXCLUDED_MANUFACTURERS = {'CITRUS'}


class EquipmentPanel(QWidget):
    """
    Driving system selection for the Planning tab. Populates its dropdown from
    fus_driving_systems.driving_system.get_ds_list(), with CITRUS filtered out.

    No engineering-mode toggle lives here or anywhere else in the GUI: every GUI-built protocol
    always uses engineering_mode=False, so a researcher can't flip this by accident.

    Signals:
        driving_system_changed(object): Emitted with the newly selected DrivingSystem instance
            (or None once the dropdown is empty).
    """

    driving_system_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._driving_system_combo = QComboBox()
        self._driving_system_combo.currentIndexChanged.connect(self._on_selection_changed)

        layout = QFormLayout(self)
        layout.addRow("Driving system:", self._driving_system_combo)

        self.reload_driving_systems()

    def reload_driving_systems(self):
        """
        (Re)populates the driving system dropdown from the current configuration file, with
        CITRUS filtered out. Safe to call again later if ds_config.ini changes during a session.
        """

        self._driving_system_combo.clear()

        try:
            available = driving_system.get_ds_list()
        except FDSError as e:
            get_logger().error("Could not load the driving system list: %s", e)
            return

        for ds in available:
            if (ds.manufact or '').strip().upper() in _EXCLUDED_MANUFACTURERS:
                continue
            self._driving_system_combo.addItem(ds.name, ds)

    def selected_driving_system(self):
        """
        Returns:
            The currently selected DrivingSystem instance, or None if the dropdown is empty.
        """

        return self._driving_system_combo.currentData()

    def select_driving_system(self, driving_sys):
        """
        Selects driving_sys in the dropdown by serial, not object identity: a caller like
        protocol_io.load() constructs its own DrivingSystem instance while parsing a file, never
        the same object already sitting in this combo.

        Parameters:
            driving_sys (DrivingSystem): The driving system to select.

        Returns:
            bool: True if a matching entry was found and selected, False otherwise (e.g.
            driving_sys is a CITRUS one, filtered out of this dropdown entirely, or has since
            become inactive in ds_config.ini). PlanningTab.load_protocol() raises FDSConfigError
            on False, since a loaded protocol naming a driving system this dropdown can't offer
            can't be edited here at all.
        """

        for i in range(self._driving_system_combo.count()):
            if self._driving_system_combo.itemData(i).serial == driving_sys.serial:
                self._driving_system_combo.setCurrentIndex(i)
                return True
        return False

    def driving_systems(self):
        """
        Returns:
            List of every DrivingSystem instance currently in the dropdown, in display order.
        """

        combo = self._driving_system_combo
        return [combo.itemData(i) for i in range(combo.count())]

    def _on_selection_changed(self, _index):
        self.driving_system_changed.emit(self.selected_driving_system())
