# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QToolButton,
                               QVBoxLayout, QWidget)

from fus_ds_gui.planning.apply_panel import ApplyPanel


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
    One named group of timing fields, collapsible or not, mirrors the TUS calculator's own
    Pulse/Pulse Train (PT)/Pulse Train Repetition (PTR) levels
    (https://www.socsci.ru.nl/fusinitiative/tuscalculator/), including that only the latter two
    carry a collapse toggle there; "Pulse" is always shown.

    More than a visibility toggle: TimingPanel treats "collapsed" as "inherit from the level
    below" (see its own docstring). A collapsed level's own field(s) are kept in sync with that
    inherited value, and reset to it the moment the level collapses, so what's shown never goes
    stale just because it isn't currently visible.
    """

    def __init__(self, title, collapsible=True, collapsed=False, parent=None):
        super().__init__(parent)

        self.content = QWidget()
        self.content_form = QFormLayout(self.content)
        self.content.setVisible(not collapsed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if collapsible:
            self.toggle_button = QToolButton()
            self.toggle_button.setText(title)
            self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.toggle_button.setCheckable(True)
            self.toggle_button.setChecked(not collapsed)
            self._set_arrow(not collapsed)
            self.toggle_button.toggled.connect(self._on_toggled)
            layout.addWidget(self.toggle_button)
        else:
            self.toggle_button = None
            heading = QLabel(f"<b>{title}</b>")
            layout.addWidget(heading)

        layout.addWidget(self.content)

    def add_row(self, label, widget):
        """Adds one labeled field to this level's collapsible content area."""

        self.content_form.addRow(label, widget)

    def is_expanded(self):
        """
        Returns:
            bool: True if this level's own content is currently visible; always True for a
            non-collapsible level (there's no toggle_button to check at all).
        """

        return self.toggle_button is None or self.toggle_button.isChecked()

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

    def __init__(self, builder, parent=None):
        super().__init__(parent)

        self.builder = builder
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

        self.pulse_train_rep_dur_spin = QDoubleSpinBox()
        self.pulse_train_rep_dur_spin.setDecimals(3)
        self.pulse_train_rep_dur_spin.setRange(0.0, 1_000_000.0)
        self.pulse_train_rep_dur_spin.setSuffix(' s')
        self.pulse_train_rep_dur_spin.setValue(protocol.pulse_train_rep_dur / 1e3)

        self.pulse_level = _TimingLevel("Pulse", collapsible=False)
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

        layout = QVBoxLayout(self)
        layout.addWidget(self.pulse_level)
        layout.addWidget(self.pulse_train_level)
        layout.addWidget(self.pulse_train_rep_level)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.error_label)

        # Whatever a collapsed level's own field(s) show must track the value they'd actually
        # inherit, live. pulse_rep_int_spin/pulse_train_dur_spin feed pulse_train_rep_level's
        # own inheritance in turn, so they're included here too; pulse_train_rep_int_spin/
        # pulse_train_rep_dur_spin have nothing further downstream to feed, so aren't.
        self.pulse_dur_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_rep_int_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_train_dur_spin.valueChanged.connect(self._refresh_cascaded_values)
        self.pulse_train_level.toggle_button.toggled.connect(self._refresh_cascaded_values)
        self.pulse_train_rep_level.toggle_button.toggled.connect(self._refresh_cascaded_values)

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
        """

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
        train_expanded = self.pulse_train_level.is_expanded()
        train_rep_expanded = self.pulse_train_rep_level.is_expanded()

        self.builder.configure_timing(
            pulse_dur=self.pulse_dur_spin.value(),
            pulse_rep_int=self.pulse_rep_int_spin.value() if train_expanded else None,
            pulse_train_dur=self.pulse_train_dur_spin.value() if train_expanded else None,
            pulse_ramp_shape=self.ramp_shape_combo.currentText(),
            pulse_ramp_dur=self.ramp_dur_spin.value(),
            pulse_train_rep_int=(self.pulse_train_rep_int_spin.value()
                                 if train_rep_expanded else None),
            pulse_train_rep_dur=(self.pulse_train_rep_dur_spin.value()
                                 if train_rep_expanded else None),
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
