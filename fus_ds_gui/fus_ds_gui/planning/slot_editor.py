# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from fus_driving_systems.exceptions import FDSValidationError

from fus_ds_gui.planning.apply_panel import ApplyPanel


def _mm_spinbox():
    spin = QDoubleSpinBox()
    spin.setDecimals(2)
    spin.setRange(-1000.0, 1000.0)
    spin.setSuffix(' mm')
    return spin


class SlotEditor(ApplyPanel):
    """
    One transducer slot's editor: transducer, focus, power. Backed by ProtocolBuilder, which
    already filters engineering-only focus/power options (see its own docstring); this widget
    never sees those at all, so there's nothing here to gate on an engineering-mode toggle.

    Only oper_freq/dephasing_degree are left out of this v1 editor. Both already have sensible
    defaults (the transducer's own fundamental frequency, and "no dephasing"), which is why v1
    ships without them; adding both is scoped as its own follow-up (see the implementation
    plan's Phase 2b).

    Before the first successful "Apply", this widget represents a not-yet-added slot: clicking
    Apply then calls ProtocolBuilder.add_slot(). After that, it represents an already-added slot
    (self.slot is set): Apply instead calls slot.update_transducer() (if the transducer changed)
    or slot.configure() (if only focus/power changed); never removes and re-adds, since the
    backend has no way to remove a slot at all.

    Focus value entry switches between a single field and three (x, y, z) fields depending on
    whether the currently selected focus_option is one of the 3D ones ('Focus xyz wrt exit plane
    [mm]'/'Focus xyz wrt mid bowl [mm]'), matching TransducerSlot._set_focus_xyz()'s own (x, y,
    z) tuple contract. Only reachable when the selected transducer has can_3d_steer=True (see
    ProtocolBuilder.focus_options()), e.g. any of the Clover transducers.

    Signals:
        transducer_selection_changed(): Emitted whenever this editor's own transducer_combo
            selection changes (not just on Apply): PlanningTab listens for this on every
            SlotEditor to keep every *other* editor's own transducer_combo excluding whichever
            transducer this one currently has selected (see set_excluded_transducers()).
    """

    transducer_selection_changed = Signal()

    def __init__(self, builder, excluded_transducer_serials=(), parent=None):
        super().__init__(parent)

        self.builder = builder
        self.slot = None  # Set once this editor's first Apply succeeds.
        # Applied *before* the combo is first populated below, not after, so a freshly added
        # editor's own dropdown never even lists an already-chosen transducer as an option, not
        # even fleetingly (see PlanningTab._add_slot_editor()). A fresh editor itself always
        # starts on the "no transducer selected" placeholder regardless (see
        # _populate_transducer_combo()), so this is about the options offered, not the default.
        self._excluded_transducer_serials = frozenset(excluded_transducer_serials)

        self.transducer_combo = QComboBox()
        self._populate_transducer_combo()
        self.transducer_combo.currentIndexChanged.connect(self._on_transducer_changed)

        self.focus_option_combo = QComboBox()
        self.focus_option_combo.currentTextChanged.connect(self._on_focus_option_changed)

        self.focus_value_spin = _mm_spinbox()

        self.focus_value_x_spin = _mm_spinbox()
        self.focus_value_y_spin = _mm_spinbox()
        self.focus_value_z_spin = _mm_spinbox()
        self.focus_value_xyz_widget = QWidget()
        xyz_layout = QHBoxLayout(self.focus_value_xyz_widget)
        xyz_layout.setContentsMargins(0, 0, 0, 0)
        for label, spin in (("x:", self.focus_value_x_spin), ("y:", self.focus_value_y_spin),
                            ("z:", self.focus_value_z_spin)):
            xyz_layout.addWidget(QLabel(label))
            xyz_layout.addWidget(spin)

        self.power_option_combo = QComboBox()

        self.power_value_spin = QDoubleSpinBox()
        self.power_value_spin.setDecimals(3)
        # 0, not negative: every backend power setter (_set_global_power/_set_press/_set_volt/
        # _set_ampl in transducer_slot.py) validates its value with check_pos=True, so a negative
        # value is never valid for any power option, on either driving system.
        self.power_value_spin.setRange(0.0, 100000.0)

        self._focus_value_label = QLabel("Focus value:")

        self._form = QFormLayout()
        self._form.addRow("Transducer:", self.transducer_combo)
        self._form.addRow("Focus option:", self.focus_option_combo)
        self._form.addRow(self._focus_value_label, self.focus_value_spin)
        self._form.addRow("Focus value (x, y, z):", self.focus_value_xyz_widget)
        self._form.addRow("Power option:", self.power_option_combo)
        self._form.addRow("Power value:", self.power_value_spin)

        # Only safe from here on: _update_focus_options()/_update_focus_value_fields() both
        # need self._form (setRowVisible()) to already exist. _update_focus_options() must run
        # before _update_focus_range(), not after: the range's own offset depends on which
        # focus_option ends up selected (see _focus_range_offset()), which is empty/unset until
        # _update_focus_options() populates the combo.
        self._update_focus_options()
        self._update_focus_range()
        self._update_power_options()

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.error_label)

    def set_excluded_transducers(self, serials):
        """
        Called by PlanningTab whenever any SlotEditor's transducer selection changes: excludes
        the given serials (chosen by sibling slots) from this editor's own transducer_combo, so
        the same physical transducer can never be assigned to two slots at once. This editor's
        own current selection is never excluded from its own dropdown, even if it happens to be
        in `serials`: exclusion is about what other slots have taken, not this one.
        """

        self._excluded_transducer_serials = frozenset(serials)
        self._populate_transducer_combo()

    def _populate_transducer_combo(self):
        """
        Always includes a leading "no transducer selected" placeholder (itemData None), on top
        of every non-excluded compatible transducer. A fresh editor starts on this placeholder
        rather than auto-picking the first compatible transducer, so two editors can never
        default to the same one, and a researcher can always deliberately clear an editor's own
        pick (freeing that transducer up for another editor, e.g. to swap two slots' transducers
        without ever needing both to point at the same one at once). SlotEditor._apply() already
        raises a clear "Choose a transducer first." error for the placeholder, unchanged.
        """

        current = self.transducer_combo.currentData() if self.transducer_combo.count() else None
        current_serial = current.serial if current is not None else None

        self.transducer_combo.blockSignals(True)
        self.transducer_combo.clear()
        self.transducer_combo.addItem("-- Select a transducer --", None)
        restore_index = 0
        for tran in self.builder.compatible_transducers():
            if tran.serial in self._excluded_transducer_serials and tran.serial != current_serial:
                continue
            self.transducer_combo.addItem(tran.name, tran)
            if tran.serial == current_serial:
                restore_index = self.transducer_combo.count() - 1
        self.transducer_combo.setCurrentIndex(restore_index)
        self.transducer_combo.blockSignals(False)

    def _on_transducer_changed(self, _index):
        """
        Mirrors TransducerSlot._set_transducer()'s own reset behavior (see equipment_panel.py's
        docstring for the same pattern applied to the driving-system dropdown): a focus/power
        value chosen for the previous transducer's calibration curve/geometric range doesn't
        mean anything for the new one, so both value fields reset here, never silently kept and
        reused.

        _update_focus_options() must run before _update_focus_range(), not after: the range's
        own offset depends on which focus_option ends up selected (see _focus_range_offset()),
        and _update_focus_options() is what settles that (the old selection may no longer be
        valid for the new transducer). The range update in turn must happen before the focus
        reset below, not after: resetting to a value outside the *old* range first would get
        silently clamped against it, before the new transducer's own range ever applies. Reset
        to the new transducer's own min_foc (offset the same way the range itself is), not a
        hardcoded 0: 0 isn't necessarily even in range (many transducers have a strictly
        positive minimum focus).
        """

        self._update_focus_options()  # also refreshes the value-field visibility, see its body
        self._update_focus_range()
        self._update_power_options()
        tran = self.transducer_combo.currentData()
        default_focus = tran.min_foc + self._focus_range_offset(tran) if tran is not None else 0.0
        self.focus_value_spin.setValue(default_focus)
        # z is depth, same axis/default as the single-value field above; x/y have no equivalent
        # config-driven default, so they simply reset to 0.
        self.focus_value_x_spin.setValue(0.0)
        self.focus_value_y_spin.setValue(0.0)
        self.focus_value_z_spin.setValue(default_focus)
        self.power_value_spin.setValue(0.0)
        self.transducer_selection_changed.emit()

    def _focus_range_offset(self, tran):
        """
        transducer.min_foc/max_foc are wrt-exit-plane bounds. TransducerSlot.
        _set_focus_wrt_mid_bowl() converts a mid-bowl value to its exit-plane equivalent
        (focus - exit_plane_dist) before checking it against those same bounds, so the actual
        valid range for the mid-bowl option is [min_foc + exit_plane_dist, max_foc +
        exit_plane_dist], not [min_foc, max_foc] directly.

        Returns:
            float: tran.exit_plane_dist when the currently selected focus_option is the scalar
            'wrt mid bowl' one, 0.0 otherwise (the 'wrt exit plane' option needs no offset at
            all, matching min_foc/max_foc's own reference frame).
        """

        if self.focus_option_combo.currentText() == self.builder.mid_bowl_focus_option():
            return tran.exit_plane_dist
        return 0.0

    def _update_focus_range(self):
        """Bounds the single-value focus spinbox to the currently selected transducer's own
        min_foc/max_foc, offset for the currently selected focus_option when needed (see
        _focus_range_offset()). A helpful default, not the actual source of truth (the backend's
        own curve-range checks are, and still run on Apply regardless). Doesn't apply to the
        (x, y, z) fields: min_foc/max_foc describe the z-axis-only (depth) range, whereas z
        there is only one of three independent coordinates, and x/y have no equivalent
        config-driven bound at all today.

        Also puts that range in the row label and the spinbox's own tooltip: QDoubleSpinBox
        silently clamps an out-of-range typed value to the nearest bound with no visual cue at
        all, so without this a researcher has no way to tell why their entry changed.
        """

        tran = self.transducer_combo.currentData()
        if tran is None:
            return

        offset = self._focus_range_offset(tran)
        min_foc, max_foc = tran.min_foc + offset, tran.max_foc + offset
        self.focus_value_spin.setRange(min_foc, max_foc)
        range_text = f"{min_foc:.1f} to {max_foc:.1f} mm"
        if offset:
            # Derived from min_foc/max_foc plus exit_plane_dist (see _focus_range_offset()),
            # not read directly from config the way the wrt-exit-plane range is, so labeled as
            # an estimate: an active calibration curve's own range can differ from this.
            self._focus_value_label.setText(f"Focus value ({range_text}, estimate):")
            self.focus_value_spin.setToolTip(
                f"Estimated valid range for {tran.name}: {range_text}. The actual range "
                "enforced on Apply may differ once an active calibration curve applies.")
        else:
            self._focus_value_label.setText(f"Focus value ({range_text}):")
            self.focus_value_spin.setToolTip(f"Valid range for {tran.name}: {range_text}")

    def _update_focus_options(self):
        """Repopulates focus_option_combo for whichever transducer is currently selected; see
        ProtocolBuilder.focus_options()'s own docstring for why the 3D (x, y, z) options only
        ever appear for a 3D-steering-capable transducer. Rebuilt with signals blocked, so this
        also explicitly re-syncs the value-field visibility afterward: a blocked
        currentTextChanged wouldn't otherwise fire _update_focus_value_fields() even if the
        selection silently changed underneath (e.g. the previously-chosen xyz option disappearing
        because the new transducer can't 3D-steer)."""

        tran = self.transducer_combo.currentData()
        current_text = self.focus_option_combo.currentText()

        self.focus_option_combo.blockSignals(True)
        self.focus_option_combo.clear()
        self.focus_option_combo.addItems(self.builder.focus_options(tran))
        index = self.focus_option_combo.findText(current_text)
        if index >= 0:
            self.focus_option_combo.setCurrentIndex(index)
        self.focus_option_combo.blockSignals(False)
        self._update_focus_value_fields(self.focus_option_combo.currentText())

    def _update_power_options(self):
        """Repopulates power_option_combo for whichever transducer is currently selected; see
        ProtocolBuilder.power_options()'s own docstring for why a non-native option only appears
        once an active calibration exists for the current (driving system, transducer) pair."""

        tran = self.transducer_combo.currentData()
        current_text = self.power_option_combo.currentText()

        self.power_option_combo.clear()
        self.power_option_combo.addItems(self.builder.power_options(tran))
        index = self.power_option_combo.findText(current_text)
        self.power_option_combo.setCurrentIndex(index if index >= 0 else 0)

    def _update_focus_value_fields(self, focus_option):
        """Switches focus value entry between the single field (every ordinary focus option) and
        the three (x, y, z) fields (the two 3D options); see this class's own docstring."""

        is_xyz = focus_option in self.builder.xyz_focus_options()
        self._form.setRowVisible(self.focus_value_spin, not is_xyz)
        self._form.setRowVisible(self.focus_value_xyz_widget, is_xyz)

    def _on_focus_option_changed(self, focus_option):
        """Handles an interactive focus_option_combo change (not the blocked-signal one
        _update_focus_options() does internally, which calls both of these directly itself):
        switches which value field(s) are shown, and refreshes the scalar field's own range,
        since which focus_option is selected changes that range too (see
        _update_focus_range()'s own docstring)."""

        self._update_focus_value_fields(focus_option)
        self._update_focus_range()

    def _apply(self):
        transducer = self.transducer_combo.currentData()
        if transducer is None:
            raise FDSValidationError("Choose a transducer first.")

        focus_option = self.focus_option_combo.currentText()
        if focus_option in self.builder.xyz_focus_options():
            focus_value = (self.focus_value_x_spin.value(), self.focus_value_y_spin.value(),
                           self.focus_value_z_spin.value())
        else:
            focus_value = self.focus_value_spin.value()
        power_option = self.power_option_combo.currentText()
        power_value = self.power_value_spin.value()

        if self.slot is None:
            self.slot = self.builder.add_slot(transducer.serial, focus_option, focus_value,
                                              power_option, power_value)
        elif transducer.serial != self.slot.transducer.serial:
            self.slot.update_transducer(transducer.serial, focus_option, focus_value,
                                        power_option, power_value)
        else:
            self.slot.configure(focus_option, focus_value, power_option, power_value)
