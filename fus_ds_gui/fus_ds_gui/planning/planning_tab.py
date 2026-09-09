# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from fus_ds_gui.models.protocol_builder import ProtocolBuilder
from fus_ds_gui.planning.equipment_panel import EquipmentPanel
from fus_ds_gui.planning.slot_editor import SlotEditor
from fus_ds_gui.planning.timing_panel import TimingPanel


class PlanningTab(QWidget):
    """
    Build a protocol: equipment selection, one or more transducer slots, and shared timing.
    Everything here is driven by one ProtocolBuilder at a time, replaced (never mutated in
    place) whenever the equipment selection changes, see EquipmentPanel.driving_system_changed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.builder = None
        self._slot_editors = []
        self.timing_panel = None

        self.equipment_panel = EquipmentPanel()
        self.equipment_panel.driving_system_changed.connect(self._on_driving_system_changed)

        self.slots_layout = QVBoxLayout()

        self.add_slot_button = QPushButton("Add transducer slot")
        self.add_slot_button.clicked.connect(self._add_slot_editor)

        self.timing_layout = QVBoxLayout()

        self.validation_title = QLabel("Validation:")
        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.equipment_panel)
        layout.addLayout(self.slots_layout)
        layout.addWidget(self.add_slot_button)
        layout.addLayout(self.timing_layout)
        layout.addWidget(self.validation_title)
        layout.addWidget(self.validation_label)
        layout.addStretch()

        self._on_driving_system_changed(self.equipment_panel.selected_driving_system())

    def _on_driving_system_changed(self, driving_system):
        """Replaces the current ProtocolBuilder (and every widget bound to it) with a fresh one
        for the newly selected driving system, see ProtocolBuilder's own docstring for why a
        new instance, not an in-place update, is the right response to this."""

        self._clear_slot_editors()
        self._clear_timing_panel()

        if driving_system is None:
            self.builder = None
            self.add_slot_button.setEnabled(False)
            self._refresh_validation()
            return

        self.builder = ProtocolBuilder(driving_system)

        self.timing_panel = TimingPanel(self.builder)
        self.timing_panel.applied.connect(self._refresh_validation)
        self.timing_layout.addWidget(self.timing_panel)

        self._add_slot_editor()
        self._refresh_validation()

    def _clear_slot_editors(self):
        for editor in self._slot_editors:
            editor.setParent(None)
        self._slot_editors = []

    def _clear_timing_panel(self):
        if self.timing_panel is not None:
            self.timing_panel.setParent(None)
            self.timing_panel = None

    def _add_slot_editor(self):
        already_chosen = {
            editor.transducer_combo.currentData().serial
            for editor in self._slot_editors
            if editor.transducer_combo.currentData() is not None
        }
        editor = SlotEditor(self.builder, excluded_transducer_serials=already_chosen)
        editor.applied.connect(self._on_slot_applied)
        editor.transducer_selection_changed.connect(self._refresh_transducer_exclusions)
        self._slot_editors.append(editor)
        self.slots_layout.addWidget(editor)
        self._update_add_button_enabled()
        self._refresh_transducer_exclusions()

    def _refresh_transducer_exclusions(self):
        """Keeps the same physical transducer from ever being assigned to two slots at once:
        each SlotEditor's own transducer_combo excludes whichever transducer every *other*
        editor currently has selected (not its own, see SlotEditor.set_excluded_transducers()'s
        own docstring)."""

        for editor in self._slot_editors:
            other_serials = {
                other.transducer_combo.currentData().serial
                for other in self._slot_editors
                if other is not editor and other.transducer_combo.currentData() is not None
            }
            editor.set_excluded_transducers(other_serials)

    def _update_add_button_enabled(self):
        """Gates on how many slot editors are already on screen, not ProtocolBuilder.
        can_add_slot() (which only counts slots actually added to the protocol so far): a
        driving system with max_tran_slots=1 must never offer a second editor row at all, even
        before the first one's own Apply has run."""

        max_slots = self.builder.driving_system.max_tran_slots
        self.add_slot_button.setEnabled(len(self._slot_editors) < max_slots)

    def _on_slot_applied(self):
        self._refresh_validation()
        self._update_add_button_enabled()

    def _refresh_validation(self):
        if self.builder is None:
            self.validation_label.setStyleSheet("")
            self.validation_label.setText("")
            return

        # Called even before any transducer slot has been added: ProtocolBuilder.validate()'s
        # own timing checks don't need one, so a timing problem is reported right away rather
        # than only after a slot editor's own Apply has also been clicked.
        errors = self.builder.validate()
        if errors:
            self.validation_label.setStyleSheet("color: red;")
            self.validation_label.setText("\n".join(f"- {error}" for error in errors))
        elif not self.builder.protocol.slots:
            # Distinct from "No problems found." below: nothing has actually been added to the
            # protocol yet, even though timing itself checks out so far.
            self.validation_label.setStyleSheet("")
            self.validation_label.setText(
                "Configure a transducer slot below and click its Apply button to begin.")
        else:
            self.validation_label.setStyleSheet("")
            self.validation_label.setText("No problems found.")
