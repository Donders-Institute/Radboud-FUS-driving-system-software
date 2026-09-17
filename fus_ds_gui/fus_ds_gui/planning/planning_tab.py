# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSConfigError

from fus_ds_gui.models.protocol_builder import ProtocolBuilder
from fus_ds_gui.planning.equipment_panel import EquipmentPanel
from fus_ds_gui.planning.slot_editor import SlotEditor
from fus_ds_gui.planning.timing_panel import TimingPanel


class PlanningTab(QWidget):
    """
    Build a protocol: equipment selection, one or more transducer slots, and shared timing.
    Everything here is driven by one ProtocolBuilder at a time, replaced (never mutated in
    place) whenever the equipment selection changes, see EquipmentPanel.driving_system_changed.

    Signals:
        validation_changed(): Emitted every time _refresh_validation() runs, i.e. whenever
            can_save()'s own answer might have changed. MainWindow listens for this to keep its
            own save_button's enabled state in sync, rather than polling it.
        lock_changed(bool): Emitted whenever is_locked()'s own answer changes; see its own
            docstring. The Executing panel listens for this to gate Send on it.

    load_button/save_button/approve_button are plain widgets, not wired to anything here:
    MainWindow owns the actual file dialogs and self._current_file_path (see its own docstring
    for why that tracking belongs there, not here), and connects/drives these directly, the same
    way it already does for ConnectionPanel/ExecutionPanel's own widgets.
    """

    validation_changed = Signal()
    lock_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.builder = None
        self._slot_editors = []
        self.timing_panel = None
        self._locked = False

        self.equipment_panel = EquipmentPanel()
        self.equipment_panel.driving_system_changed.connect(self._on_driving_system_changed)

        # Always starts unchecked (Demo mode); never persisted across app restarts.
        self.advanced_mode_checkbox = QCheckBox("Advanced mode")
        self.advanced_mode_checkbox.toggled.connect(self._on_advanced_mode_toggled)
        self.advanced_mode_checkbox.toggled.connect(self._mark_dirty)

        self.slots_layout = QVBoxLayout()

        self.add_slot_button = QPushButton("Add transducer slot")
        self.add_slot_button.clicked.connect(self._add_slot_editor)

        self.timing_layout = QVBoxLayout()

        # One shared Apply for the whole tab, not one per slot/timing panel: applies every
        # panel that currently exists at once, see _on_apply_clicked()'s own docstring.
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply_clicked)

        # See this class's own docstring for why these three are plain, undriven widgets here.
        self.load_button = QPushButton("Load protocol...")
        self.save_button = QPushButton("Save protocol...")
        self.approve_button = QPushButton("Approve protocol")
        self.approve_button.setEnabled(False)  # MainWindow enables it once a file is known
        file_buttons_layout = QHBoxLayout()
        for button in (self.load_button, self.save_button, self.approve_button):
            file_buttons_layout.addWidget(button)

        self.validation_title = QLabel("Validation:")
        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.equipment_panel)
        layout.addWidget(self.advanced_mode_checkbox)
        layout.addLayout(self.slots_layout)
        layout.addWidget(self.add_slot_button)
        layout.addLayout(self.timing_layout)
        layout.addWidget(self.apply_button)
        layout.addLayout(file_buttons_layout)
        layout.addWidget(self.validation_title)
        layout.addWidget(self.validation_label)
        layout.addStretch()

        self._on_driving_system_changed(self.equipment_panel.selected_driving_system())

    def current_protocol(self):
        """
        Returns:
            TUSProtocol or None: The protocol currently under construction (e.g. for
            protocol_io.save()), or None if no driving system is selected yet.
        """

        return self.builder.protocol if self.builder is not None else None

    def can_save(self):
        """
        Returns:
            bool: True if the current protocol has at least one slot, no validation problems,
            and no slot editor or the timing panel is currently showing its own unresolved
            error (see _has_unresolved_panel_error()). That last check matters because
            builder.validate() only ever checks what actually reached protocol.slots, so a slot
            that failed to apply (or failed to load) is invisible to it, and an otherwise-valid
            sibling slot could make the rest look fine even though the protocol on screen still
            has a real, unresolved problem the researcher hasn't actually fixed yet. Without it,
            saving would silently produce a YAML file quietly missing a slot the researcher
            meant to include. Matches what MainWindow's own Save action gates on (together with
            is_locked(), see its own docstring).
        """

        if self.builder is None or not self.builder.protocol.slots:
            return False
        return not self.builder.validate() and not self._has_unresolved_panel_error()

    def is_locked(self):
        """
        Returns:
            bool: True only right after a fully successful Apply (or a successful
            load_protocol()), while nothing has been touched since (see _mark_dirty()). Set
            from can_save() at those two points, not read from it directly here: can_save()
            alone can't tell "still valid" apart from "valid, but no longer what the researcher
            is currently looking at". Only a locked protocol matches what's actually on screen
            closely enough to send/execute; the Executing panel gates Send on this.
        """

        return self._locked

    def _set_locked(self, locked):
        if locked != self._locked:
            self._locked = locked
            self.lock_changed.emit(locked)

    def _mark_dirty(self, *_args):
        """Unlocks unconditionally the moment anything changes, regardless of whether the
        result would still validate cleanly: is_locked() means "matches what was last applied",
        not just "currently valid". Connected to every SlotEditor/TimingPanel's own `changed`
        signal, the Advanced mode checkbox, adding a slot, and switching driving system."""

        self._set_locked(False)

    def _on_driving_system_changed(self, driving_system):
        """Replaces the current ProtocolBuilder (and every widget bound to it) with a fresh one
        for the newly selected driving system, see ProtocolBuilder's own docstring for why a
        new instance, not an in-place update, is the right response to this."""

        self._clear_slot_editors()
        self._clear_timing_panel()
        self._mark_dirty()  # a different builder entirely is never still "what was applied"

        if driving_system is None:
            self.builder = None
            self.add_slot_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self._refresh_validation()
            return

        self.builder = ProtocolBuilder(driving_system)
        self.apply_button.setEnabled(True)

        self.timing_panel = TimingPanel(self.builder)
        self.timing_panel.set_advanced_mode(self.advanced_mode_checkbox.isChecked())
        self.timing_panel.applied.connect(self._refresh_validation)
        self.timing_panel.changed.connect(self._mark_dirty)
        self.timing_layout.addWidget(self.timing_panel)

        self._add_slot_editor()
        self._refresh_validation()

    def _clear_slot_editors(self):
        # setParent(None) alone would leave editor's own visible flag untouched and drop its
        # parent to None -- Qt then treats it as a standalone top-level window and actually
        # shows it as one (a stray, empty OS-level window), rather than making it disappear.
        # removeWidget() (keeps self as the Qt parent, just stops the layout from managing it)
        # plus deleteLater() (schedules the actual Qt object destruction once safe) is the
        # correct way to make a widget already added to a layout go away for good.
        for editor in self._slot_editors:
            self.slots_layout.removeWidget(editor)
            editor.deleteLater()
        self._slot_editors = []

    def _clear_timing_panel(self):
        if self.timing_panel is not None:
            self.timing_layout.removeWidget(self.timing_panel)  # see _clear_slot_editors()
            self.timing_panel.deleteLater()
            self.timing_panel = None

    def _add_slot_editor(self):
        self._build_slot_editor()
        self._mark_dirty()  # a brand new, not-yet-applied slot is never "what was applied"

    def _build_slot_editor(self, existing_slot=None, failed_slot=None):
        """Adds one SlotEditor: blank by default, pre-filled from existing_slot, or pre-filled
        (with its own inline error already showing) from failed_slot, see SlotEditor's own
        existing_slot/failed_slot parameters. Used by the "Add transducer slot" button above and
        by load_protocol() below, once per already-loaded or failed-to-load slot."""

        already_chosen = {
            editor.transducer_combo.currentData().serial
            for editor in self._slot_editors
            if editor.transducer_combo.currentData() is not None
        }
        title = f"Slot {len(self._slot_editors) + 1}"
        editor = SlotEditor(self.builder, excluded_transducer_serials=already_chosen,
                            existing_slot=existing_slot, failed_slot=failed_slot, title=title)
        editor.set_advanced_mode(self.advanced_mode_checkbox.isChecked())
        editor.applied.connect(self._on_slot_applied)
        editor.changed.connect(self._mark_dirty)
        editor.transducer_selection_changed.connect(self._refresh_transducer_exclusions)
        self._slot_editors.append(editor)
        self.slots_layout.addWidget(editor)
        self._update_add_button_enabled()
        self._refresh_transducer_exclusions()

    def load_protocol(self, load_result):
        """
        Replaces the protocol currently under construction with load_result's own, e.g. one
        just returned by protocol_io.load(). Rebuilds every widget from its already-resolved
        state: one pre-filled SlotEditor per successfully-loaded slot, one more pre-filled
        SlotEditor per slot that failed to load (its own raw values shown together with the
        failure itself, right in that editor's own inline error_label, rather than losing the
        whole file over it, see protocol_io.load()'s own docstring), and a TimingPanel reading
        the protocol's own timing fields directly, the same way it already does for a
        freshly-constructed one.

        Parameters:
            load_result (protocol_io.LoadResult): The result of protocol_io.load().

        Raises:
            FDSConfigError: If load_result.protocol.driving_sys isn't offered in the Planning
                tab's own equipment dropdown (e.g. it's a CITRUS one, filtered out entirely, or
                has since become inactive in ds_config.ini). Loading it would otherwise silently
                leave whatever was previously selected in place.
        """

        protocol = load_result.protocol
        if not self.equipment_panel.select_driving_system(protocol.driving_sys):
            message = (f"Cannot load this protocol: '{protocol.driving_sys.serial}' isn't "
                       "available in the Planning tab (a CITRUS driving system, or one that's "
                       "no longer active in ds_config.ini, isn't offered here).")
            get_logger().error(message)
            raise FDSConfigError(message)

        # select_driving_system() above already rebuilt self.builder/self._slot_editors/
        # self.timing_panel from scratch for the matching driving system (via
        # _on_driving_system_changed()), for a fresh, empty protocol. Swap the actual loaded
        # one in now, then rebuild around it instead.
        self.builder.protocol = protocol
        self._clear_slot_editors()
        self._clear_timing_panel()

        # seed_demo_defaults=False: this protocol's own pulse_dur/pulse_rep_int are real,
        # already-chosen values, not an untouched cascade to replace with a demo example.
        self.timing_panel = TimingPanel(self.builder, seed_demo_defaults=False)
        self.timing_panel.set_advanced_mode(self.advanced_mode_checkbox.isChecked())
        self.timing_panel.applied.connect(self._refresh_validation)
        self.timing_panel.changed.connect(self._mark_dirty)
        self.timing_layout.addWidget(self.timing_panel)

        for slot in protocol.slots:
            self._build_slot_editor(existing_slot=slot)
        for failed_slot in load_result.failed_slots:
            self._build_slot_editor(failed_slot=failed_slot)

        self._refresh_validation()
        # A slot that failed to load still shows its own inline error, so can_save() (see its
        # own docstring) correctly refuses to lock a partial load, the same way it refuses a
        # partial Apply.
        self._set_locked(self.can_save())

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

    def _on_advanced_mode_toggled(self, advanced):
        """Propagates the toggle to every panel that currently exists; a panel created later
        (see _build_slot_editor()/_on_driving_system_changed()/load_protocol()) reads the
        checkbox's own current state directly instead of waiting for this signal."""

        if self.timing_panel is not None:
            self.timing_panel.set_advanced_mode(advanced)
        for editor in self._slot_editors:
            editor.set_advanced_mode(advanced)

    def _on_apply_clicked(self):
        """Applies every panel that currently exists via its own try_apply(), continuing past
        any individual failure: a mistake in one slot must not block a correctly-configured
        sibling slot or the timing panel from being applied too. Each panel's own error_label
        already shows its own failure inline; _refresh_validation() at the end reflects
        whatever combination of successes/failures resulted, even if nothing succeeded at all.
        Locks (see is_locked()'s own docstring) only if every panel succeeded and the result is
        valid, i.e. can_save(): a partial or failed Apply must never leave Send available."""

        if self.timing_panel is not None:
            self.timing_panel.try_apply()
        for editor in self._slot_editors:
            editor.try_apply()
        self._refresh_validation()
        self._set_locked(self.can_save())

    def _refresh_validation(self):
        if self.builder is None:
            self.validation_label.setStyleSheet("")
            self.validation_label.setText("Select a driving system above to begin.")
            self.validation_changed.emit()
            return

        # Called even before any transducer slot has been added: ProtocolBuilder.validate()'s
        # own timing checks don't need one, so a timing problem is reported right away rather
        # than only after Apply has also been clicked.
        errors = self.builder.validate()
        if errors and self._has_unresolved_panel_error():
            # A slot editor's own error_label already explains the real problem (e.g. an
            # out-of-range value); a failed slot is never added to protocol.slots (see
            # SlotEditor._apply()), so validate()'s own errors here (e.g. IGT's channel-count
            # mismatch, expecting every configured slot's channels) are just a downstream
            # symptom of that same slot, not a separate "add another slot" problem. Repeating
            # them as if a slot were simply missing is confusing rather than helpful.
            self.validation_label.setStyleSheet("color: red;")
            self.validation_label.setText(
                "Resolve the error(s) shown above the transducer slot(s) below, then click "
                "Apply again.")
        elif errors:
            self.validation_label.setStyleSheet("color: red;")
            self.validation_label.setText("\n".join(f"- {error}" for error in errors))
        elif not self.builder.protocol.slots:
            # Distinct from "No problems found." below: nothing has actually been added to the
            # protocol yet, even though timing itself checks out so far.
            self.validation_label.setStyleSheet("")
            self.validation_label.setText(
                "Configure a transducer slot below and click Apply to begin.")
        else:
            self.validation_label.setStyleSheet("")
            self.validation_label.setText("No problems found.")

        self.validation_changed.emit()

    def _has_unresolved_panel_error(self):
        """
        Returns:
            bool: True if any slot editor or the timing panel is currently showing its own
            inline error_label (ApplyPanel), meaning that panel's own try_apply() never
            actually succeeded (or, for a loaded slot, never even ran, see
            SlotEditor._load_failed_slot()). Folded into can_save() itself; see its own
            docstring.
        """

        panels = list(self._slot_editors)
        if self.timing_panel is not None:
            panels.append(self.timing_panel)
        return any(not panel.error_label.isHidden() for panel in panels)
