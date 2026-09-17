# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from fus_ds_gui.planning.apply_panel import ApplyPanel
from fus_ds_gui.planning.form_alignment import align_form_labels

_DEMO_DEFAULT_DUTY_CYCLE_PERCENT = 10
_DEMO_PRESET_FREQUENCIES_HZ = (5, 1000)
_DEMO_DEFAULT_TOTAL_DURATION = 60.0  # seconds


def _ms_spinbox(initial):
    spin = QDoubleSpinBox()
    spin.setDecimals(3)
    spin.setRange(0.0, 1_000_000.0)
    spin.setSuffix(' ms')
    spin.setValue(initial)
    return spin


def _is_inherited(field_a, source_a, field_b, source_b):
    """True if field_a == source_a and field_b == source_b: this level's own two fields are
    still exactly what plain inheritance from the level below would already produce, so nothing
    was actually set explicitly here. Used at construction time to decide whether a level (Pulse
    Train, Pulse Train Repetition) should start collapsed or already expanded; see TimingPanel's
    own docstring."""

    return field_a == source_a and field_b == source_b


class _TimingLevel(QWidget):
    """
    One named group of timing fields, mirrors the TUS calculator's own Pulse/Pulse Train (PT)/
    Pulse Train Repetition (PTR) levels (https://www.socsci.ru.nl/fusinitiative/tuscalculator/).
    "Pulse" always shows the same toggle-button styling as PT/PTR (see locked below), but,
    unlike them, is never actually collapsible: it's always shown.

    More than a visibility toggle: TimingPanel treats "collapsed" as "inherit from the level
    below" (see its own docstring). A collapsed level's own field(s) are kept in sync with that
    inherited value, and reset to it the moment the level collapses, so what's shown never goes
    stale just because it isn't currently visible.
    """

    def __init__(self, title, collapsed=False, locked=False, parent=None):
        super().__init__(parent)

        self._locked = locked

        self.content = QWidget()
        self.content_form = QFormLayout(self.content)
        self.content.setVisible(not collapsed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        if locked:
            # Same look as an ordinary expandable level (icon + text, always expanded), but not
            # checkable at all: nothing toggles it, so unlike setEnabled(False) it never renders
            # greyed out either.
            self._set_arrow(True)
        else:
            self.toggle_button.setCheckable(True)
            self.toggle_button.setChecked(not collapsed)
            self._set_arrow(not collapsed)
            self.toggle_button.toggled.connect(self._on_toggled)
        layout.addWidget(self.toggle_button)

        layout.addWidget(self.content)

    def add_row(self, label, widget):
        """Adds one labeled field to this level's collapsible content area."""

        self.content_form.addRow(label, widget)

    def is_expanded(self):
        """
        Returns:
            bool: True if this level's own content is currently visible; always True for a
            locked level (there's no way to actually collapse one).
        """

        return self._locked or self.toggle_button.isChecked()

    def _on_toggled(self, expanded):
        self.content.setVisible(expanded)
        self._set_arrow(expanded)

    def _set_arrow(self, expanded):
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)


class TimingPanel(ApplyPanel):
    """
    The protocol's shared timing parameters; see TUSProtocol.configure_timing(), the only way
    to set any of them, which is exactly why this panel funnels every field through one "Apply"
    that calls it once with all of them together, rather than calling it per field.

    Grouped into the same three collapsible levels as the TUS calculator (see _TimingLevel):
    Pulse Train and Pulse Train Repetition each start collapsed only if their own values are
    still exactly what plain inheritance from the level below would already show (see
    _is_inherited() below); most fresh protocols never need to open them, but a loaded one whose
    file actually set either level explicitly starts with that level already expanded, so a
    researcher never has to go hunting for values that are already sitting there, just hidden.

    A collapsed level means "inherit from the level below", the same thing leaving that
    parameter out of configure_timing() means: _apply() passes None for a collapsed level's own
    field(s), rather than the value still sitting in its (hidden) spinbox, so
    configure_timing() itself resolves the real inherited value instead of this class trying to
    duplicate that logic. What each collapsed field visibly shows is kept in sync with that same
    inheritance chain regardless (_refresh_cascaded_values()) purely so it's never stale or
    misleading if the researcher does look, and is refreshed once more from the protocol's own,
    now-authoritative values right after a successful Apply.

    pulse_train_rep_dur is the one field in seconds, not milliseconds. configure_timing()'s
    own documented parameter contract, not a choice made here (its docstring: "Pulse train
    repetiton duration [s]"). Labeled accordingly so this doesn't quietly become a unit bug.
    """

    def __init__(self, builder, seed_demo_defaults=True, parent=None):
        super().__init__(parent)

        # _seed_demo_defaults is False for a loaded protocol (see PlanningTab.load_protocol()):
        # its own pulse_dur/pulse_rep_int are real, already-chosen values, not just an
        # untouched cascade, even if they happen to still satisfy the same "nothing set beyond
        # pulse_dur" check set_advanced_mode() otherwise uses to seed a fresh one.
        self.builder, self._seed_demo_defaults = builder, seed_demo_defaults
        protocol = builder.protocol

        self.pulse_dur_spin = _ms_spinbox(protocol.pulse_dur)

        self.ramp_shape_combo = QComboBox()
        self.ramp_shape_combo.addItems(builder.ramp_shapes())
        index = self.ramp_shape_combo.findText(protocol.pulse_ramp_shape)
        if index >= 0:
            self.ramp_shape_combo.setCurrentIndex(index)
        self.ramp_shape_combo.currentTextChanged.connect(self._update_ramp_dur_enabled)

        self.ramp_dur_spin = _ms_spinbox(protocol.pulse_ramp_dur)
        self._update_ramp_dur_enabled(self.ramp_shape_combo.currentText())

        self.pulse_rep_int_spin = _ms_spinbox(protocol.pulse_rep_int)
        self.pulse_train_dur_spin = _ms_spinbox(protocol.pulse_train_dur)

        self.pulse_train_rep_int_spin = _ms_spinbox(protocol.pulse_train_rep_int)

        self.pulse_train_rep_dur_spin = self._build_pulse_train_rep_dur_spin(protocol)

        self.duty_cycle_spin = self._build_duty_cycle_spin()
        self.preset_widget = self._build_preset_widget()
        self.pulse_info_label = self._build_pulse_info_label()

        self.pulse_level = _TimingLevel("Pulse", locked=True)
        self.pulse_level.add_row("Duty cycle:", self.duty_cycle_spin)
        self.pulse_level.add_row("Pulse repetition frequency:", self.preset_widget)
        self.pulse_level.add_row("Pulse duration / Pulse repetition interval:",
                                 self.pulse_info_label)
        self.pulse_level.add_row("Pulse duration:", self.pulse_dur_spin)
        self.pulse_level.add_row("Ramp shape:", self.ramp_shape_combo)
        self.pulse_level.add_row("Ramp duration:", self.ramp_dur_spin)

        train_inherited = _is_inherited(protocol.pulse_rep_int, protocol.pulse_dur,
                                        protocol.pulse_train_dur, protocol.pulse_rep_int)
        self.pulse_train_level = _TimingLevel("Pulse Train", collapsed=train_inherited)
        self.pulse_train_level.add_row("Pulse repetition interval:", self.pulse_rep_int_spin)
        self.pulse_train_level.add_row("Pulse train duration:", self.pulse_train_dur_spin)

        train_rep_inherited = _is_inherited(
            protocol.pulse_train_rep_int, protocol.pulse_train_dur,
            protocol.pulse_train_rep_dur, protocol.pulse_train_rep_int)
        self.pulse_train_rep_level = _TimingLevel("Pulse Train Repetition",
                                                  collapsed=train_rep_inherited)
        self.pulse_train_rep_level.add_row("Pulse train repetition interval:",
                                           self.pulse_train_rep_int_spin)
        self.pulse_train_rep_level.add_row("Pulse train repetition duration:",
                                           self.pulse_train_rep_dur_spin)
        self._train_rep_dur_label = self.pulse_train_rep_level.content_form.labelForField(
            self.pulse_train_rep_dur_spin)
        for level in (self.pulse_level, self.pulse_train_level, self.pulse_train_rep_level):
            align_form_labels(level.content_form)

        self.title_label = QLabel("Timing")
        self.title_label.setStyleSheet("font-weight: bold;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.pulse_level)
        layout.addWidget(self.pulse_train_level)
        layout.addWidget(self.pulse_train_rep_level)
        layout.addWidget(self.error_label)

        self._connect_cascade_refresh_signals()

        # Always starts in Demo mode; PlanningTab's own toggle calls set_advanced_mode() right
        # after construction if Advanced mode is already active.
        self._advanced_mode = False
        self.set_advanced_mode(False)

    def _connect_cascade_refresh_signals(self):
        """Whatever a collapsed level's own field(s) show must track the value they'd actually
        inherit, live. pulse_rep_int_spin/pulse_train_dur_spin feed pulse_train_rep_level's own
        inheritance in turn, so they're included here too; pulse_train_rep_int_spin/
        pulse_train_rep_dur_spin have nothing further downstream to feed, so aren't. Extracted
        out of __init__ purely to keep its own statement count under pylint's limit."""

        self.pulse_dur_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_rep_int_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_train_dur_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_train_level.toggle_button.toggled.connect(self._refresh_cascaded_values)
        self.pulse_train_rep_level.toggle_button.toggled.connect(self._refresh_cascaded_values)

    def _build_pulse_train_rep_dur_spin(self, protocol):
        """Extracted out of __init__ purely to keep its own statement count under pylint's
        limit."""

        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setRange(0.0, 1_000_000.0)
        spin.setSuffix(' s')
        spin.setValue(protocol.pulse_train_rep_dur / 1e3)
        return spin

    def _build_preset_widget(self):
        """One button per _DEMO_PRESET_FREQUENCIES_HZ entry, each filling in Pulse duration/
        Pulse repetition interval for duty_cycle_spin's own duty cycle (see
        _apply_frequency_preset()): demos commonly use one of a couple of fixed frequencies
        rather than typing pulse timing in by hand. Kept on its own row, separate from
        duty_cycle_spin's own (see __init__): cramming both into one row left too little width
        for either to render properly."""

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Checkable and mutually exclusive, so whichever frequency is currently active stays
        # visibly highlighted rather than looking like a one-off action button.
        self._freq_button_group = QButtonGroup(widget)
        self._freq_buttons = {}
        for freq_hz in _DEMO_PRESET_FREQUENCIES_HZ:
            button = QPushButton(f"{freq_hz} Hz")
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton:checked { background-color: rgba(0, 0, 0, 60); "
                "border-radius: 4px; }")
            button.clicked.connect(lambda _checked, f=freq_hz: self._apply_frequency_preset(f))
            self._freq_button_group.addButton(button)
            self._freq_buttons[freq_hz] = button
            layout.addWidget(button)
        return widget

    def _build_duty_cycle_spin(self):
        """The duty cycle used by both frequency preset buttons; see
        _recompute_pulse_dur_from_duty_cycle()."""

        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setSuffix('%')
        # Without this, the spinbox's own initial width (before anything has ever been typed
        # into it) can render too narrow to show "100%" once the value actually gets that
        # large, clipping it until the window is manually resized.
        spin.setMinimumWidth(60)
        spin.setValue(_DEMO_DEFAULT_DUTY_CYCLE_PERCENT)
        # Recomputes Pulse duration right away, not just when a preset button is next clicked:
        # adjusting the duty cycle is itself an action, not merely a setting for later.
        spin.valueChanged.connect(self._recompute_pulse_dur_from_duty_cycle)
        return spin

    def _apply_frequency_preset(self, freq_hz):
        """Fills in Pulse repetition interval for freq_hz, then Pulse duration for
        duty_cycle_spin's own current duty cycle at that interval, and marks freq_hz's own
        button as the currently active one."""

        self.pulse_rep_int_spin.setValue(1000.0 / freq_hz)
        self._recompute_pulse_dur_from_duty_cycle()
        self._freq_buttons[freq_hz].setChecked(True)

    def _recompute_pulse_dur_from_duty_cycle(self):
        """Fills in Pulse duration for duty_cycle_spin's own current duty cycle, at whatever
        Pulse repetition interval is currently showing; changing the duty cycle alone updates
        Pulse duration immediately, without needing to click a preset button again first."""

        self.pulse_dur_spin.setValue(
            self.pulse_rep_int_spin.value() * self.duty_cycle_spin.value() / 100.0)

    def _build_pulse_info_label(self):
        """Read-only display of Pulse duration/Pulse repetition interval together, shown only
        in Demo mode (see set_advanced_mode()): these two are only ever meant to be set there
        via the frequency presets/duty cycle, not typed in directly, which could otherwise
        silently disagree with whatever duty_cycle_spin still shows."""

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.pulse_dur_spin.valueChanged.connect(self._refresh_pulse_info_label)
        self.pulse_rep_int_spin.valueChanged.connect(self._refresh_pulse_info_label)
        self.pulse_info_label = label
        self._refresh_pulse_info_label()
        return label

    def _refresh_pulse_info_label(self, _value=None):
        self.pulse_info_label.setText(
            f"{self.pulse_dur_spin.value():.3f} ms / {self.pulse_rep_int_spin.value():.3f} ms")

    def set_advanced_mode(self, advanced):
        """Advanced mode shows the normal collapsible Pulse/Pulse Train/Pulse Train Repetition
        levels, each field editable directly. Demo mode hides all three headers and flattens
        them into the frequency presets/duty cycle, a read-only Pulse duration/Pulse
        repetition interval display (see _build_pulse_info_label()), and an editable total
        duration (see _apply())."""

        self._advanced_mode = advanced
        for level in (self.pulse_level, self.pulse_train_level, self.pulse_train_rep_level):
            level.toggle_button.setVisible(advanced)
            level.content.setVisible(level.is_expanded() if advanced else True)

        # In Advanced mode, a driving system without uses_pulse_train_repetition() (Sonic
        # Concepts) never reads either of this level's own fields at all, so showing it there
        # would only offer parameters that silently do nothing. Demo mode still needs this
        # level's own Total duration field regardless (see _apply()'s own routing for it), so
        # this only ever hides the level in Advanced mode, never in Demo mode.
        self.pulse_train_rep_level.setVisible(
            not (advanced and not self.builder.uses_pulse_train_repetition()))

        self.pulse_level.content_form.setRowVisible(self.duty_cycle_spin, not advanced)
        self.pulse_level.content_form.setRowVisible(self.preset_widget, not advanced)
        self.pulse_level.content_form.setRowVisible(self.pulse_info_label, not advanced)
        self.pulse_level.content_form.setRowVisible(self.pulse_dur_spin, advanced)
        self.pulse_train_level.content_form.setRowVisible(self.pulse_rep_int_spin, advanced)
        self.pulse_level.content_form.setRowVisible(self.ramp_shape_combo, advanced)
        self.pulse_level.content_form.setRowVisible(self.ramp_dur_spin, advanced)
        self.pulse_train_level.content_form.setRowVisible(self.pulse_train_dur_spin, advanced)
        self.pulse_train_rep_level.content_form.setRowVisible(
            self.pulse_train_rep_int_spin, advanced)
        self._train_rep_dur_label.setText(
            "Pulse train repetition duration:" if advanced else "Total duration:")

        # A fresh protocol's own cascaded default is a fraction of a millisecond, which rounds
        # to a confusing "0.000 s" here; give Demo mode a usable starting point instead.
        if not advanced and self.pulse_train_rep_dur_spin.value() < 0.001:
            self.pulse_train_rep_dur_spin.setValue(_DEMO_DEFAULT_TOTAL_DURATION)

        # Same idea for Pulse duration/Pulse repetition interval: while they still look like
        # the untouched cascade from pulse_dur (never explicitly set), seed a recognizable
        # example frequency instead. Not for a loaded protocol though (see
        # self._seed_demo_defaults's own docstring): its values are real even if they happen
        # to satisfy that same check. Naturally never re-fires once genuinely set (by this or
        # the researcher), since the values then no longer match that cascade.
        if (not advanced and self._seed_demo_defaults and _is_inherited(
                self.pulse_rep_int_spin.value(), self.pulse_dur_spin.value(),
                self.pulse_train_dur_spin.value(), self.pulse_rep_int_spin.value())):
            self._apply_frequency_preset(_DEMO_PRESET_FREQUENCIES_HZ[0])

    def _refresh_cascaded_values(self):
        """
        Mirrors configure_timing()'s own cascading defaults (pulse_dur -> pulse_rep_int ->
        pulse_train_dur -> pulse_train_rep_int -> pulse_train_rep_dur), purely for display: a
        collapsed level's own field(s) are kept showing what _apply() will actually end up
        sending as None for it (see this class's own docstring), including right at the moment a
        level collapses, so a value typed while it was open doesn't linger on screen looking
        like it still applies once the level no longer does.

        An expanded level's own field(s) are never touched here: they're the researcher's own
        explicit input, not something to overwrite out from under them.

        In Demo mode, collapse state is frozen and meaningless (see set_advanced_mode()): every
        Demo-mode-visible field is its own explicit input, so this cascade sync is skipped
        entirely rather than clobbering pulse_rep_int/pulse_train_rep_dur out from under it.
        """

        if not self._advanced_mode:
            return

        if not self.pulse_train_level.is_expanded():
            self.pulse_rep_int_spin.setValue(self.pulse_dur_spin.value())
            self.pulse_train_dur_spin.setValue(self.pulse_rep_int_spin.value())

        if not self.pulse_train_rep_level.is_expanded():
            self.pulse_train_rep_int_spin.setValue(self.pulse_train_dur_spin.value())
            self.pulse_train_rep_dur_spin.setValue(self.pulse_train_rep_int_spin.value() / 1e3)

    def _update_ramp_dur_enabled(self, ramp_shape):
        """Disables the ramp duration field whenever the selected shape is the configured
        rectangular ("no ramping") option, see ProtocolBuilder.rectangular_ramp_shape(). Also
        resets it to 0 in that case, so a value left over from a previously selected ramp shape
        doesn't keep sitting there looking like it still applies."""

        is_rectangular = ramp_shape == self.builder.rectangular_ramp_shape()
        self.ramp_dur_spin.setEnabled(not is_rectangular)
        if is_rectangular:
            self.ramp_dur_spin.setValue(0.0)

    def _apply(self):
        if self._advanced_mode:
            train_expanded = self.pulse_train_level.is_expanded()
            train_rep_expanded = self.pulse_train_rep_level.is_expanded()
            pulse_rep_int = self.pulse_rep_int_spin.value() if train_expanded else None
            pulse_train_dur = self.pulse_train_dur_spin.value() if train_expanded else None
            pulse_ramp_shape = self.ramp_shape_combo.currentText()
            pulse_ramp_dur = self.ramp_dur_spin.value()
            pulse_train_rep_int = (self.pulse_train_rep_int_spin.value()
                                   if train_rep_expanded else None)
            pulse_train_rep_dur = (self.pulse_train_rep_dur_spin.value()
                                   if train_rep_expanded else None)
        else:
            train_expanded = train_rep_expanded = False
            pulse_rep_int = self.pulse_rep_int_spin.value()
            pulse_ramp_shape = None
            pulse_ramp_dur = None
            if self.builder.uses_pulse_train_repetition():
                # IGT: send the minimal 1-pulse-per-train pattern (see
                # ProtocolBuilder.uses_pulse_train_repetition()'s own docstring on the 64-pulse
                # hardware limit) and let Total duration drive the repeated train instead.
                pulse_train_dur = None
                pulse_train_rep_int = None
                pulse_train_rep_dur = self.pulse_train_rep_dur_spin.value()
            else:
                # Sonic Concepts has no train-repetition concept at all: Total duration must
                # be pulse_train_dur itself (its own device "TIMER", the actual total
                # sonication duration), converted from seconds to milliseconds.
                pulse_train_dur = self.pulse_train_rep_dur_spin.value() * 1e3
                pulse_train_rep_int = None
                pulse_train_rep_dur = None

        self.builder.configure_timing(
            pulse_dur=self.pulse_dur_spin.value(),
            pulse_rep_int=pulse_rep_int,
            pulse_train_dur=pulse_train_dur,
            pulse_ramp_shape=pulse_ramp_shape,
            pulse_ramp_dur=pulse_ramp_dur,
            pulse_train_rep_int=pulse_train_rep_int,
            pulse_train_rep_dur=pulse_train_rep_dur,
        )

        # Refreshes a collapsed level's own display from the protocol's own, now-authoritative
        # resolved values, rather than this class's own _refresh_cascaded_values() mirror:
        # configure_timing() is the single source of truth for what "inherited" actually
        # resolves to, this only ever approximates it for live display before Apply is clicked.
        protocol = self.builder.protocol
        if not train_expanded:
            self.pulse_rep_int_spin.setValue(protocol.pulse_rep_int)
            self.pulse_train_dur_spin.setValue(protocol.pulse_train_dur)
        if not train_rep_expanded:
            self.pulse_train_rep_int_spin.setValue(protocol.pulse_train_rep_int)
            self.pulse_train_rep_dur_spin.setValue(protocol.pulse_train_rep_dur / 1e3)
