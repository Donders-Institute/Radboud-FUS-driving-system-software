# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QSpinBox, QVBoxLayout, QWidget)

from fus_driving_systems.exceptions import FDSSafetyError, FDSValidationError

from fus_ds_gui.planning.apply_panel import ApplyPanel
from fus_ds_gui.planning.form_alignment import align_form_labels

_DEPHASING_NONE = "No dephasing"
_DEPHASING_CYCLIC = "Cyclic (one degree, applied to every element)"
_DEPHASING_PER_ELEMENT = "Per-element override (one phase value per element)"

_PER_ELEMENT_POWER_MESSAGE = (
    "This slot's power value is set per element. Loading that per-element list here isn't "
    "supported yet, since this field only ever holds one value shared by every element; enter "
    "a new value here to apply it to every element instead, or choose a different power "
    "option.")


def _mm_spinbox():
    spin = QDoubleSpinBox()
    spin.setDecimals(2)
    spin.setRange(-1000.0, 1000.0)
    spin.setSuffix(' mm')
    return spin


def _widen_range_to_fit(spinbox, value):
    """Widens spinbox's own range to include value first if it's currently outside it, so a raw,
    possibly out-of-range value from a failed slot_def (see _load_failed_slot()) shows exactly
    what the file gave, instead of being silently clamped to the field's own normal range the
    way typing such a value in by hand would be."""

    spinbox.setRange(min(spinbox.minimum(), value), max(spinbox.maximum(), value))


class SlotEditor(ApplyPanel):
    """
    One transducer slot's editor: transducer, focus, power. Backed by ProtocolBuilder, which
    already filters engineering-only focus/power options (see its own docstring); this widget
    never sees those at all, so there's nothing here to gate on an engineering-mode toggle.

    oper_freq defaults to the currently selected transducer's own fundamental frequency, matching
    TransducerSlot._set_transducer()'s own fallback exactly, so leaving it untouched reproduces
    today's implicit default.

    dephasing_degree has two mutually exclusive forms (see its own docstring on TransducerSlot):
    a single cyclic degree step applied uniformly across every element, or an explicit
    per-element override (one phase value per transducer element, replacing the focus-derived
    phases entirely). dephasing_mode_combo switches which of the two value widgets is shown,
    matching the single-vs-(x, y, z) focus field toggle above. The per-element form's own count
    must match transducer.elements exactly; the backend itself only catches a mismatch much
    later, inside IGT._define_pulse_group() (only reached once a protocol is actually sent,
    which this GUI doesn't support yet), so _apply() checks this itself instead, synchronously.

    Only IGT's own backend (igt_ds.py) ever reads dephasing_degree at all, SonicConcepts's own
    backend never does, so the whole dephasing section is hidden outright for a SonicConcepts-
    backed builder (see ProtocolBuilder.supports_dephasing()), rather than let a researcher
    configure something that would silently have no effect.

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

    def __init__(self, builder, excluded_transducer_serials=(), existing_slot=None,
                 failed_slot=None, title=None, parent=None):
        """
        Parameters:
            builder (ProtocolBuilder): Backs this editor; see this class's own docstring.
            excluded_transducer_serials (Iterable[str]): Transducers already claimed by a
                sibling slot editor, excluded from this one's own dropdown (see
                set_excluded_transducers()).
            title (str): Shown in bold above this editor's own fields, e.g. "Slot 1" (see
                set_title()); helps tell editors apart once more than one is on screen.
            existing_slot (TransducerSlot): An already-configured slot to pre-fill every field
                from, e.g. one just returned by protocol_loader.load_protocol() (see
                PlanningTab.load_protocol()). Every field below shows that slot's own already-
                chosen values instead of the fresh, empty defaults, and Apply edits it in place
                rather than adding a new one. None (the default) starts a fresh, empty editor
                for a not-yet-added slot instead.
            failed_slot (tuple(dict, FDSError)): A (slot_def, exception) pair for a slot whose
                own values a file described but that failed to actually construct (see
                protocol_io.load()'s own failed_slots, and PlanningTab.load_protocol()). The raw
                values are pre-filled exactly like existing_slot's own would be, but self.slot
                stays None (never added to the protocol) and the exception's own message is
                shown immediately in this editor's own inline error_label, exactly as if the
                researcher had just clicked Apply themselves and it failed. Mutually exclusive
                with existing_slot.
        """

        super().__init__(parent)

        self.builder = builder
        self.slot = None  # Set once this editor's first Apply succeeds.
        # Always starts in Demo mode; PlanningTab's own toggle calls set_advanced_mode() right
        # after construction if Advanced mode is already active.
        self._advanced_mode = False
        # The power option a failed slot_def's own per-element list was pre-filled from (see
        # _load_failed_slot()), or None. Not institution-specific: which power options require
        # engineering_mode is itself config-driven (_requires_engineering_mode()'s own
        # docstring), so this field's own single, shared value can't be relied on to always be
        # rejected before it would silently reach add_slot() -- _apply() checks this directly
        # instead of assuming that.
        self._per_element_power_option = None
        # The first entry of that same per-element list, i.e. exactly what power_value_spin
        # itself was pre-filled with (see _load_failed_slot()). _apply() only refuses to add a
        # new slot while power_value_spin still shows this exact, untouched value: the moment
        # the researcher types a genuinely different one in (even for the very same power
        # option), that's a deliberate choice of one shared value for every element, not an
        # accidental resend of the file's own per-element data.
        self._per_element_power_first_value = None
        # The raw, non-real option text (see _select_or_show_raw()) currently sitting as a
        # one-off item in focus_option_combo/power_option_combo, or None. Tracked by text, not
        # index, so _prune_raw_option() can still find and drop it correctly even after other
        # items have been inserted/removed around it in the meantime.
        self._raw_focus_option = None
        self._raw_power_option = None
        # A failed slot_def's own raw focus_value, still shown unclamped (see
        # _load_failed_slot()/_widen_range_to_fit()), or None. _update_focus_range() checks this
        # so that picking a different, real focus_option afterward doesn't silently clamp this
        # value away the moment it narrows focus_value_spin's own range back down -- flagged
        # via error_label instead, since the whole point of showing it was for the researcher to
        # see and fix it, not have it vanish the moment they start doing exactly that.
        self._raw_focus_value = None
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
        self.focus_option_combo.activated.connect(
            lambda _i: self._prune_raw_option(self.focus_option_combo, '_raw_focus_option'))

        self.focus_value_spin = _mm_spinbox()
        self._build_focus_xyz_widgets()

        self.power_option_combo = QComboBox()
        self.power_option_combo.activated.connect(
            lambda _i: self._prune_raw_option(self.power_option_combo, '_raw_power_option'))

        self.power_value_spin = QDoubleSpinBox()
        self.power_value_spin.setDecimals(2)
        # 0, not negative: every backend power setter (_set_global_power/_set_press/_set_volt/
        # _set_ampl in transducer_slot.py) validates its value with check_pos=True, so a negative
        # value is never valid for any power option, on either driving system.
        self.power_value_spin.setRange(0.0, 100000.0)

        self.oper_freq_spin = QSpinBox()
        self.oper_freq_spin.setSuffix(' kHz')
        # 0, matching focus_value_spin/power_value_spin's own "nothing selected yet" resting
        # value: tightened to exclude 0 once a real transducer is chosen, see
        # _on_transducer_changed().
        self.oper_freq_spin.setRange(0, 100000)

        self._build_dephasing_fields()
        self._build_title_label(title)

        self._focus_value_label = QLabel("Focus value:")
        self._focus_row_widget = self._build_option_and_value_row(
            self.focus_option_combo, self.focus_value_spin)
        self._power_row_widget = self._build_option_and_value_row(
            self.power_option_combo, self.power_value_spin)

        self._form = QFormLayout()
        for label, widget in (
                ("Transducer:", self.transducer_combo),
                (self._focus_value_label, self._focus_row_widget),
                ("Focus value (x, y, z):", self.focus_value_xyz_widget),
                ("Power:", self._power_row_widget),
                ("Operating frequency:", self.oper_freq_spin),
                ("Dephasing mode:", self.dephasing_mode_combo),
                ("Dephasing degree:", self.dephasing_degree_spin),
                ("Dephasing values:", self.dephasing_values_edit)):
            self._form.addRow(label, widget)
        align_form_labels(self._form)

        # Only safe from here on: _update_focus_options()/_update_focus_value_fields() both
        # need self._form (setRowVisible()) to already exist. _update_focus_options() must run
        # before _update_focus_range(), not after: the range's own offset depends on which
        # focus_option ends up selected (see _focus_range_offset()), which is empty/unset until
        # _update_focus_options() populates the combo.
        self._update_focus_options()
        self._update_focus_range()
        self._update_power_options()
        self._update_dephasing_value_fields(self.dephasing_mode_combo.currentText())
        self._update_transducer_dependent_visibility()
        self._load_initial_state(existing_slot, failed_slot)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addLayout(self._form)
        layout.addWidget(self.error_label)

    def _build_option_and_value_row(self, option_combo, value_spin):
        """Combines an option combo and its value spinbox onto one row (focus_option_combo/
        focus_value_spin, power_option_combo/power_value_spin): which unit is used and its
        actual value belong together at a glance. Only for the single-value case;
        focus_value_xyz_widget keeps its own row, three extra spinboxes wouldn't fit here."""

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(option_combo)
        layout.addWidget(value_spin)
        return widget

    def _build_focus_xyz_widgets(self):
        """Builds focus_value_x/y/z_spin plus the row widget combining them; extracted out of
        __init__ purely to keep its own statement count under pylint's limit."""

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

    def _load_initial_state(self, existing_slot, failed_slot):
        """Dispatches __init__'s own existing_slot/failed_slot parameters to whichever pre-fill
        this editor actually needs, or neither for a fresh, blank editor."""

        if existing_slot is not None:
            self._load_existing_slot(existing_slot)
        elif failed_slot is not None:
            self._load_failed_slot(*failed_slot)

    def _load_existing_slot(self, slot):
        """
        Pre-fills every field from an already-configured TransducerSlot; see __init__'s own
        existing_slot parameter. Selects the transducer first, exactly like an interactive pick
        (so the focus/power option combos and the xyz/dephasing sections populate correctly for
        it, via the same _on_transducer_changed()/_on_focus_option_changed() this triggers), then
        overwrites the fresh "reset to default" values those handlers themselves just applied
        with this slot's own actual, already-chosen ones.
        """

        self.slot = slot

        combo = self.transducer_combo
        index = next(i for i in range(combo.count())
                     if combo.itemData(i) is not None
                     and combo.itemData(i).serial == slot.transducer.serial)
        combo.setCurrentIndex(index)

        focus_index = self.focus_option_combo.findText(slot.chosen_focus)
        self.focus_option_combo.setCurrentIndex(focus_index)
        if slot.chosen_focus in self.builder.xyz_focus_options():
            x, y, z = slot.chosen_focus_value
            self.focus_value_x_spin.setValue(x)
            self.focus_value_y_spin.setValue(y)
            self.focus_value_z_spin.setValue(z)
        else:
            self.focus_value_spin.setValue(slot.chosen_focus_value)

        power_index = self.power_option_combo.findText(slot.chosen_power)
        self.power_option_combo.setCurrentIndex(power_index)
        power_value = slot.chosen_power_value
        # A list means one value per element (see TransducerSlot.chosen_power_value's own
        # docstring for which power options that applies to, config-driven per institution, see
        # TransducerSlot._requires_engineering_mode()); power_value_spin itself only ever
        # shows/sends a single, shared value, so only the first entry is shown here for a list.
        # Flagged immediately, the same way a failed slot_def's own problem is (see
        # _load_failed_slot()), rather than waiting for the researcher to click Apply and
        # discover only then that _apply() refuses to overwrite it with that single shared
        # value.
        if isinstance(power_value, list):
            self._show_error(_PER_ELEMENT_POWER_MESSAGE)
            power_value = power_value[0]
        self.power_value_spin.setValue(power_value)

        self.oper_freq_spin.setValue(slot.oper_freq)
        self._load_existing_dephasing(slot.dephasing_degree)

    def _load_existing_dephasing(self, dephasing_degree):
        """Selects the right dephasing_mode_combo entry (and fills its own value widget) for an
        already-configured slot's dephasing_degree, or a failed slot_def's raw one (see
        _load_failed_slot()); see this class's own docstring for what each length means.
        _widen_range_to_fit() is a no-op for an already-valid value, so this is safe either way."""

        if dephasing_degree is None:
            self.dephasing_mode_combo.setCurrentIndex(0)  # _DEPHASING_NONE
        elif len(dephasing_degree) == 1:
            self.dephasing_mode_combo.setCurrentIndex(1)  # _DEPHASING_CYCLIC
            _widen_range_to_fit(self.dephasing_degree_spin, dephasing_degree[0])
            self.dephasing_degree_spin.setValue(dephasing_degree[0])
        else:
            self.dephasing_mode_combo.setCurrentIndex(2)  # _DEPHASING_PER_ELEMENT
            self.dephasing_values_edit.setText(', '.join(str(v) for v in dephasing_degree))

    def _load_failed_slot(self, slot_def, exc):
        """
        Pre-fills every field from a raw slot_def dict that failed to actually construct via
        add_slot() (see __init__'s own failed_slot parameter), and shows why in this editor's
        own inline error_label. Closely mirrors _load_existing_slot(), but reads a plain dict
        instead of an already-configured TransducerSlot, and never sets self.slot: this slot
        was never actually added, so Apply (once the researcher fixes whatever's wrong) goes
        through the normal "add a new slot" path, not "edit this one in place".

        Every raw value below is shown exactly as the file gave it, deliberately never silently
        replaced by something that merely looks plausible: a numeric field would otherwise clamp
        an out-of-range value to its own normal range (see _widen_range_to_fit()), and an option
        combo would otherwise fall back to whichever real option it already happens to default
        to (see _select_or_show_raw()) -- either would leave the researcher looking at a
        seemingly valid field with no hint that this is not what the file actually said. Every
        field stays visible even when the transducer itself wasn't found (see the unmatched-
        serial case below): _update_transducer_dependent_visibility()'s own "nothing to show
        yet" default is for a blank, not-yet-touched editor, not this one.
        """

        combo = self.transducer_combo
        serial = slot_def.get('transducer_serial')
        index = next((i for i in range(combo.count())
                      if combo.itemData(i) is not None and combo.itemData(i).serial == serial),
                     None)
        if index is not None:
            combo.setCurrentIndex(index)

        focus_option = slot_def.get('focus_option')
        self._select_or_show_raw(self.focus_option_combo, focus_option, '_raw_focus_option')
        focus_value = slot_def.get('focus_value')
        if (focus_option in self.builder.xyz_focus_options()
                and isinstance(focus_value, (list, tuple)) and len(focus_value) == 3):
            x, y, z = focus_value
            for spin, value in ((self.focus_value_x_spin, x), (self.focus_value_y_spin, y),
                                (self.focus_value_z_spin, z)):
                _widen_range_to_fit(spin, value)
                spin.setValue(value)
        elif isinstance(focus_value, (int, float)):
            self._raw_focus_value = focus_value
            _widen_range_to_fit(self.focus_value_spin, focus_value)
            self.focus_value_spin.setValue(focus_value)

        power_option = slot_def.get('power_option')
        self._select_or_show_raw(self.power_option_combo, power_option, '_raw_power_option')
        power_value = slot_def.get('power_value')
        # See _load_existing_slot()'s own comment on the same list case.
        if isinstance(power_value, list) and power_value:
            self._per_element_power_option = power_option
            power_value = power_value[0]
            self._per_element_power_first_value = power_value
        if isinstance(power_value, (int, float)):
            _widen_range_to_fit(self.power_value_spin, power_value)
            self.power_value_spin.setValue(power_value)

        if slot_def.get('oper_freq') is not None:
            _widen_range_to_fit(self.oper_freq_spin, slot_def['oper_freq'])
            self.oper_freq_spin.setValue(slot_def['oper_freq'])
        self._load_existing_dephasing(slot_def.get('dephasing_degree'))
        self._show_every_field_for_review()

        self._show_error(str(exc))

    def _show_every_field_for_review(self):
        """Forces every field visible regardless of _update_transducer_dependent_visibility()'s
        own "nothing to show without a transducer" default: unlike a blank editor, a failed
        slot_def already has real (if possibly wrong) values to show, transducer match or
        not (see _load_failed_slot()'s own docstring)."""

        for row_widget in (self._focus_row_widget, self._power_row_widget, self.oper_freq_spin):
            self._form.setRowVisible(row_widget, True)
        self._update_focus_value_fields(self.focus_option_combo.currentText())
        if self.builder.supports_dephasing():
            self._form.setRowVisible(self.dephasing_mode_combo, True)
            self._update_dephasing_value_fields(self.dephasing_mode_combo.currentText())

    def _select_or_show_raw(self, combo, text, raw_attr):
        """Selects text in combo if it's one of the real options currently offered; otherwise
        inserts and selects it as its own one-off item, so a raw option string a failed slot_def
        gave (e.g. a focus/power option this transducer or driving system doesn't currently
        offer) is shown exactly as-is, rather than combo silently falling back to whatever its
        own first real item already happens to be, which would look like a plausible, unrelated
        choice instead. raw_attr (e.g. '_raw_focus_option') names the attribute on self that
        remembers the inserted text, so _prune_raw_option() can remove it again later once the
        researcher actually picks something else."""

        if not text:
            return
        index = combo.findText(text)
        if index < 0:
            combo.insertItem(0, text)
            setattr(self, raw_attr, text)
            index = 0
        combo.setCurrentIndex(index)

    def _prune_raw_option(self, combo, raw_attr):
        """Removes combo's own one-off raw item (see _select_or_show_raw()) once the researcher
        has actually picked something else, so a stale, invalid entry doesn't linger in the list
        forever after a real choice has been made. Looked up by text, not the index it was
        originally inserted at, since other items may have been added/removed around it since
        (e.g. a rebuilt combo after the transducer changed already dropped it on its own; this
        is then simply a no-op, see the index check below)."""

        raw_text = getattr(self, raw_attr)
        if raw_text is None or combo.currentText() == raw_text:
            return
        index = combo.findText(raw_text)
        if index >= 0:
            combo.removeItem(index)
        setattr(self, raw_attr, None)

    def _build_title_label(self, title):
        """Extracted out of __init__ purely to keep its own statement count under pylint's
        limit."""

        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-weight: bold;")
        self.set_title(title)

    def _build_dephasing_fields(self):
        """Builds the mode selector plus its two mutually exclusive value widgets; see this
        class's own docstring for what each mode means. Row visibility toggles between them the
        same way _update_focus_value_fields() toggles the single vs. (x, y, z) focus rows."""

        self.dephasing_mode_combo = QComboBox()
        self.dephasing_mode_combo.addItems([_DEPHASING_NONE, _DEPHASING_CYCLIC,
                                            _DEPHASING_PER_ELEMENT])
        self.dephasing_mode_combo.currentTextChanged.connect(self._update_dephasing_value_fields)

        self.dephasing_degree_spin = QDoubleSpinBox()
        self.dephasing_degree_spin.setDecimals(1)
        # >0, not >=0: apply_cyclic_dephasing() (transducer_xyz.py) divides 360 by this value, so
        # 0 would raise a ZeroDivisionError rather than a clear, catchable FDSValidationError.
        self.dephasing_degree_spin.setRange(0.1, 360.0)
        self.dephasing_degree_spin.setValue(90.0)
        self.dephasing_degree_spin.setSuffix(' deg')

        self.dephasing_values_edit = QLineEdit()
        self.dephasing_values_edit.setPlaceholderText("e.g. 0, 90, 180, 270")

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

    def set_title(self, title):
        """Updates the bold title shown above this editor's own fields (e.g. "Slot 1"), or
        hides it entirely when title is None."""

        self._title_label.setText(title or "")
        self._title_label.setVisible(bool(title))

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

        # Cleared before _update_focus_range()/_update_power_options() run below, not after: a
        # different transducer makes the file's own raw, unconfirmed values (if any) meaningless
        # regardless, and every field is about to be reset to this transducer's own default a
        # few lines down anyway -- clearing first avoids briefly flagging a value that's already
        # on its way out.
        self._raw_focus_value = None
        self._per_element_power_option = None
        self._per_element_power_first_value = None

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
        # Mirrors TransducerSlot.update_transducer()'s own documented reset behavior:
        # dephasing_degree always resets to "no dephasing" rather than carrying over, since a
        # per-element list is sized to a specific transducer's own element count.
        if tran is not None:
            # 1, not 0: the backend's own oper_freq setter validates check_nonzero=True
            # (transducer_slot.py), so 0 is never actually valid once a real transducer is
            # chosen. tran.fund_freq itself is always a real, positive config value.
            self.oper_freq_spin.setRange(1, 100000)
            self.oper_freq_spin.setValue(tran.fund_freq)
        else:
            # Widened back to include 0: Apply already blocks on "Choose a transducer first."
            # before oper_freq is ever read, so this is never actually reachable at Apply.
            self.oper_freq_spin.setRange(0, 100000)
            self.oper_freq_spin.setValue(0)
        self.dephasing_mode_combo.setCurrentIndex(0)  # _DEPHASING_NONE
        self.dephasing_values_edit.setToolTip(
            f"Comma-separated phase values [deg], exactly {tran.elements} for {tran.name}."
            if tran is not None else "")
        self._update_transducer_dependent_visibility()
        self.transducer_selection_changed.emit()

    def set_advanced_mode(self, advanced):
        """Hides/shows the fields Demo mode simplifies away (see this method's own callers in
        PlanningTab): operating frequency and dephasing. The focus/power option pickers and
        value fields all stay visible and editable regardless of mode; every option offered is
        already non-engineering-only (see ProtocolBuilder.focus_options()/power_options()), so
        there's nothing unsafe left to restrict further here."""

        self._advanced_mode = advanced
        self._update_transducer_dependent_visibility()

    def _update_transducer_dependent_visibility(self):
        """Hides every field below the transducer picker until a real transducer is actually
        chosen: focus/power ranges, calibration availability, and even how many dephasing
        values are expected all depend on which one is picked, so showing these fields with
        meaningless defaults before that choice is made would look like something already
        worth configuring. Re-evaluated on every transducer change (not just once in __init__),
        so switching back to the placeholder hides them again too. Supersedes what used to be a
        separate, SonicConcepts-only _apply_dephasing_support(): that decision (see
        ProtocolBuilder.supports_dephasing()'s own docstring) never actually changes for this
        editor's own lifetime, so folding it in here instead of calling it separately is safe.

        Also folds in Demo mode's own, further restriction (see set_advanced_mode()): unlike
        has_transducer, self._advanced_mode only hides oper_freq/dephasing, never the option/
        value fields."""

        has_transducer = self.transducer_combo.currentData() is not None
        self._form.setRowVisible(self._focus_row_widget, has_transducer)
        self._form.setRowVisible(self._power_row_widget, has_transducer)
        self._form.setRowVisible(self.oper_freq_spin, has_transducer and self._advanced_mode)

        if has_transducer:
            self._update_focus_value_fields(self.focus_option_combo.currentText())
        else:
            self.focus_value_spin.setVisible(False)
            self._form.setRowVisible(self.focus_value_xyz_widget, False)

        show_dephasing = (has_transducer and self._advanced_mode
                          and self.builder.supports_dephasing())
        self._form.setRowVisible(self.dephasing_mode_combo, show_dephasing)
        if show_dephasing:
            self._update_dephasing_value_fields(self.dephasing_mode_combo.currentText())
        else:
            self._form.setRowVisible(self.dephasing_degree_spin, False)
            self._form.setRowVisible(self.dephasing_values_edit, False)

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

        A failed slot_def's own raw, still-unconfirmed focus_value (self._raw_focus_value, see
        _load_failed_slot()) is a special case of that same silent-clamp problem: narrowing the
        range here would otherwise erase it the moment the researcher picks a different, real
        focus_option (still showing the file's own out-of-range value was the whole point of
        loading it this way). Flagged via error_label instead of erased.
        """

        tran = self.transducer_combo.currentData()
        if tran is None:
            return

        offset = self._focus_range_offset(tran)
        min_foc, max_foc = tran.min_foc + offset, tran.max_foc + offset
        self.focus_value_spin.setRange(min_foc, max_foc)
        range_text = f"{min_foc:.1f} to {max_foc:.1f} mm"
        if self._raw_focus_value is not None and not min_foc <= self._raw_focus_value <= max_foc:
            # The setRange() call above already clamped the widget's own current value to
            # max_foc/min_foc as a side effect; widening the range back doesn't undo that on its
            # own, so the raw value has to be written back in explicitly too.
            _widen_range_to_fit(self.focus_value_spin, self._raw_focus_value)
            self.focus_value_spin.setValue(self._raw_focus_value)
            self._show_error(
                f"The loaded focus value ({self._raw_focus_value}) is outside {tran.name}'s "
                f"valid range for this focus option ({range_text}). Correct it before "
                "applying.")
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
        """Switches focus value entry between the single field (every ordinary focus option,
        shown alongside focus_option_combo in the same row) and the three (x, y, z) fields (the
        two 3D options, shown on their own row instead); see this class's own docstring."""

        is_xyz = focus_option in self.builder.xyz_focus_options()
        self.focus_value_spin.setVisible(not is_xyz)
        self._form.setRowVisible(self.focus_value_xyz_widget, is_xyz)

    def _on_focus_option_changed(self, focus_option):
        """Handles an interactive focus_option_combo change (not the blocked-signal one
        _update_focus_options() does internally, which calls both of these directly itself):
        switches which value field(s) are shown, and refreshes the scalar field's own range,
        since which focus_option is selected changes that range too (see
        _update_focus_range()'s own docstring)."""

        self._update_focus_value_fields(focus_option)
        self._update_focus_range()

    def _update_dephasing_value_fields(self, mode):
        """Only one of the two value widgets is relevant per mode; see this class's own
        docstring for what each mode means."""

        self._form.setRowVisible(self.dephasing_degree_spin, mode == _DEPHASING_CYCLIC)
        self._form.setRowVisible(self.dephasing_values_edit, mode == _DEPHASING_PER_ELEMENT)

    def _resolve_dephasing_degree(self, transducer):
        """
        Resolves dephasing_mode_combo's current selection to the dephasing_degree value Apply
        should actually send; see this class's own docstring for what each mode means.

        Raises:
            FDSValidationError: For the per-element mode, if dephasing_values_edit doesn't parse
            to exactly transducer.elements numbers, checked here, synchronously, since the
            backend itself only catches a mismatch much later (see this class's own docstring).
        """

        mode = self.dephasing_mode_combo.currentText()
        if mode == _DEPHASING_CYCLIC:
            return [self.dephasing_degree_spin.value()]
        if mode == _DEPHASING_PER_ELEMENT:
            raw_values = self.dephasing_values_edit.text().split(',')
            try:
                values = [float(value) for value in raw_values]
            except ValueError as e:
                raise FDSValidationError(
                    "Dephasing values must be a comma-separated list of numbers.") from e
            if len(values) != transducer.elements:
                raise FDSValidationError(
                    f"Number of dephasing entries ({len(values)}) does not correspond to "
                    f"number of transducer elements ({transducer.elements}). Enter exactly "
                    "one value per element.")
            return values
        return None

    def _apply(self):
        # Whatever the outcome, this Apply attempt settles the question the raw-value flag in
        # _update_focus_range() exists for: either this succeeds (nothing left to flag), or it
        # fails on the backend's own real validation (a fresher, more specific error than that
        # earlier heuristic). Cleared up front so a later, unrelated focus_option change never
        # re-flags a value the researcher has already moved past.
        self._raw_focus_value = None

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
        oper_freq = self.oper_freq_spin.value()
        dephasing_degree = self._resolve_dephasing_degree(transducer)

        # Demo mode's own, stricter ceiling, enforced here on top of the backend's own
        # get_max_pressure() limit, not instead of it (see ProtocolBuilder.demo_max_pressure()).
        if (not self._advanced_mode and power_option == self.builder.pressure_power_option()
                and power_value > self.builder.demo_max_pressure()):
            raise FDSSafetyError(
                f"{power_value} MPa exceeds Demo mode's own maximum of "
                f"{self.builder.demo_max_pressure()} MPa. Use a lower pressure in Demo mode.")

        if self.slot is None:
            # Blocked only while power_value_spin still shows the exact, untouched first entry
            # of the file's own per-element list (see _load_failed_slot()): the moment the
            # researcher types a genuinely different number in, even for this very same power
            # option, that's a deliberate choice of one shared value for every element, not an
            # accidental resend of data that was never really a single, shared value at all.
            if (power_option == self._per_element_power_option
                    and power_value == self._per_element_power_first_value):
                raise FDSValidationError(
                    "This slot's power value was set per element in the file. Loading that "
                    "per-element list here isn't supported yet, since this field only ever "
                    "holds one value shared by every element; enter a new value here to apply "
                    "it to every element instead, or choose a different power option.")
            self.slot = self.builder.add_slot(transducer.serial, focus_option, focus_value,
                                              power_option, power_value, oper_freq,
                                              dephasing_degree)
        elif transducer.serial != self.slot.transducer.serial:
            self.slot.update_transducer(transducer.serial, focus_option, focus_value,
                                        power_option, power_value, oper_freq, dephasing_degree)
        else:
            # power_option is '' (nothing selected) rather than self.slot.chosen_power itself
            # whenever the latter is filtered out of power_option_combo as engineering-only (see
            # _update_power_options()) -- which every per-element option is today, but isn't
            # guaranteed to stay true for every institution's own config (see this class's own
            # _per_element_power_option comment). Block on either, not just an exact match. Same
            # "still the untouched first entry" carve-out as the self.slot is None branch above.
            if (isinstance(self.slot.chosen_power_value, list)
                    and power_option in ('', self.slot.chosen_power)
                    and power_value == self.slot.chosen_power_value[0]):
                raise FDSValidationError(_PER_ELEMENT_POWER_MESSAGE)
            self.slot.configure(focus_option, focus_value, power_option, power_value)
            self.slot.oper_freq = oper_freq
            self.slot.dephasing_degree = dephasing_degree
