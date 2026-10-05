# -*- coding: utf-8 -*-
"""Tests for TimingPanel."""
import pytest

from fus_ds_gui.models.protocol_builder import ProtocolBuilder
from fus_ds_gui.planning.timing_panel import TimingPanel


@pytest.fixture
def builder(patch_config):
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT')
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '2')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return ProtocolBuilder(ds)


@pytest.fixture
def sonic_concepts_builder(patch_config):
    """A synthetic Sonic Concepts driving system: no train-repetition concept at all (see
    ProtocolBuilder.uses_pulse_train_repetition()'s own docstring)."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_SC')
    section = 'Equipment.Driving system.UNITTEST_SC'
    patch_config.set(section, 'Name', 'Test Sonic Concepts')
    patch_config.set(section, 'Manufacturer', 'Sonic Concepts')
    patch_config.set(section, 'Available channels', '1')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Global power [mW]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Global power [mW]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')
    return ProtocolBuilder(ds)


def test_panel_has_a_timing_title(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    assert panel.title_label.text() == "Timing"


def test_pulse_level_is_not_collapsible_and_always_visible(qtbot, builder):
    """Matches the TUS calculator's own layout: "Pulse" is never actually collapsible, only
    Pulse Train and Pulse Train Repetition are (see _TimingLevel's own docstring). It still
    shows the same toggle-button styling as those two, just locked, not a plain heading."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()  # isVisible() reflects real, effective visibility, not just the widget's own
    # setVisible() policy: it's always False for a widget whose top-level parent was never
    # shown, regardless of that policy, so these visibility assertions need a shown panel.

    assert panel.pulse_level.toggle_button is not None
    assert panel.pulse_level.toggle_button.isCheckable() is False
    assert panel.pulse_level.is_expanded() is True
    assert panel.pulse_level.content.isVisible() is True


def test_pulse_train_levels_start_collapsed(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)  # collapsible content only reflects state in Advanced mode

    assert panel.pulse_train_level.content.isVisible() is False
    assert panel.pulse_train_rep_level.content.isVisible() is False


def test_pulse_train_level_starts_expanded_when_already_set_explicitly(qtbot, builder):
    """A loaded protocol whose file set pulse_rep_int/pulse_train_dur explicitly (different
    from what pulse_dur alone would cascade to) must show that immediately, not hide it behind
    a collapsed level the researcher would have to think to open."""
    builder.protocol.configure_timing(pulse_dur=1.0, pulse_rep_int=5.0, pulse_train_dur=20.0)

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)

    assert panel.pulse_train_level.content.isVisible() is True
    assert panel.pulse_train_level.is_expanded() is True


def test_pulse_train_rep_level_starts_expanded_when_already_set_explicitly(qtbot, builder):
    builder.protocol.configure_timing(pulse_dur=1.0, pulse_train_rep_int=5.0,
                                      pulse_train_rep_dur=2.0)

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)

    assert panel.pulse_train_rep_level.content.isVisible() is True


def test_pulse_train_level_stays_collapsed_when_values_match_the_cascade(qtbot, builder):
    """Not "any explicit configure_timing() call expands it": only when the level's own two
    fields aren't already exactly what plain inheritance from pulse_dur would produce. A
    protocol whose pulse_rep_int/pulse_train_dur genuinely still both equal pulse_dur (the
    common, freshly-constructed case) stays collapsed."""
    builder.protocol.configure_timing(pulse_dur=3.0, pulse_rep_int=3.0, pulse_train_dur=3.0)

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)

    assert panel.pulse_train_level.content.isVisible() is False


def test_toggling_a_level_shows_its_fields(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)

    panel.pulse_train_level.toggle_button.click()

    assert panel.pulse_train_level.content.isVisible() is True
    # Toggling one level must not affect the other.
    assert panel.pulse_train_rep_level.content.isVisible() is False


def test_apply_ignores_a_collapsed_levels_stale_value_and_inherits_instead(qtbot, builder):
    """A collapsed level means "inherit from the level below" (see TimingPanel's own docstring):
    whatever value happens to be sitting in a hidden field is never sent; a researcher who never
    opened Pulse Train gets pulse_train_dur == pulse_rep_int == pulse_dur, regardless of what
    pulse_train_dur_spin itself shows."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.set_advanced_mode(True)
    assert panel.pulse_train_level.content.isVisible() is False  # never expanded in this test
    panel.pulse_dur_spin.setValue(3.0)
    # A value manually poked into the (hidden) spinbox without ever opening its own level: not
    # achievable through the actual UI, but confirms _apply() itself ignores it rather than
    # relying on _refresh_cascaded_values() having already overwritten it.
    panel.pulse_train_dur_spin.setValue(15.0)

    with qtbot.waitSignal(panel.applied, timeout=1000):
        panel.try_apply()

    assert builder.protocol.pulse_train_dur == pytest.approx(3.0)
    assert builder.protocol.pulse_rep_int == pytest.approx(3.0)


def test_collapsed_levels_show_the_cascaded_value_right_from_construction(qtbot, builder):
    """TUSProtocol.__init__() itself cascades every timing field from pulse_dur (see its own
    docstring), so a fresh protocol is already self-consistent before a researcher ever opens a
    level for the first time, let alone clicks Apply. Checked against the protocol's own raw
    values, not pulse_dur_spin/pulse_rep_int_spin: Demo mode's own frequency default (see
    test_demo_mode_seeds_a_default_frequency_for_a_fresh_protocol) changes what those two show
    without touching the protocol itself, since nothing is actually applied yet.
    pulse_train_rep_dur_spin is the one GUI-level exception: its own cascaded default is a
    near-zero fraction of a second, which Demo mode replaces with a usable one instead (see
    set_advanced_mode())."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    protocol = builder.protocol

    assert protocol.pulse_rep_int == pytest.approx(protocol.pulse_dur)
    assert protocol.pulse_train_dur == pytest.approx(protocol.pulse_dur)
    assert protocol.pulse_train_rep_int == pytest.approx(protocol.pulse_dur)
    assert panel.pulse_train_rep_dur_spin.value() == pytest.approx(60.0)


def test_demo_mode_seeds_a_default_frequency_for_a_fresh_protocol(qtbot, builder):
    """A fresh, unconfigured protocol starts with a recognizable example frequency in Demo
    mode (see set_advanced_mode()), rather than showing whatever pulse_dur alone happens to
    cascade to; the matching preset button is marked as the active one too."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(200.0)  # 1000 / 5 Hz
    assert panel.pulse_dur_spin.value() == pytest.approx(20.0)  # default 10% duty cycle
    assert panel._freq_buttons[5].isChecked() is True
    assert panel._freq_buttons[1000].isChecked() is False


def test_demo_mode_does_not_override_an_already_configured_frequency(qtbot, builder):
    """Only a genuinely fresh, untouched cascade gets the default frequency seeded in; a
    protocol whose pulse_rep_int was already explicitly set differently from pulse_dur must
    keep showing that real value instead."""
    builder.protocol.configure_timing(pulse_dur=1.0, pulse_rep_int=5.0, pulse_train_dur=20.0)

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(5.0)
    assert panel.pulse_dur_spin.value() == pytest.approx(1.0)


def test_seed_demo_defaults_false_never_seeds_even_when_the_cascade_still_matches(
        qtbot, builder):
    """A loaded protocol (see PlanningTab.load_protocol()'s own seed_demo_defaults=False) can
    legitimately have pulse_dur/pulse_rep_int/pulse_train_dur all equal, e.g. one saved with
    only pulse_dur ever given, without that being an untouched, still-needs-a-default cascade;
    seed_demo_defaults=False must never seed a default over it regardless."""
    panel = TimingPanel(builder, seed_demo_defaults=False)
    qtbot.addWidget(panel)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(panel.pulse_dur_spin.value())
    assert panel._freq_buttons[5].isChecked() is False
    assert panel._freq_buttons[1000].isChecked() is False


def test_frequency_preset_buttons_are_mutually_exclusive(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    panel._apply_frequency_preset(1000)

    assert panel._freq_buttons[1000].isChecked() is True
    assert panel._freq_buttons[5].isChecked() is False


def test_collapsed_pulse_train_level_tracks_pulse_duration_live(qtbot, builder):
    """The whole point of tracking live: a researcher who never opens Pulse Train can still see
    (without opening it) what it would actually resolve to, right as they type Pulse Duration,
    not a value left over from construction. Advanced-mode-only: Demo mode's own fields are
    plain explicit input, not part of this cascade (see _refresh_cascaded_values())."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.set_advanced_mode(True)

    panel.pulse_dur_spin.setValue(7.0)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(7.0)
    assert panel.pulse_train_dur_spin.value() == pytest.approx(7.0)


def test_expanded_pulse_train_level_is_not_overwritten_by_pulse_duration_changes(qtbot, builder):
    """Once a level is open, its own field(s) are the researcher's explicit input; changing
    Pulse Duration afterward must not silently clobber a value they already chose."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.set_advanced_mode(True)
    panel.pulse_train_level.toggle_button.click()
    panel.pulse_rep_int_spin.setValue(9.0)

    panel.pulse_dur_spin.setValue(3.0)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(9.0)


def test_collapsing_a_level_resets_its_fields_to_the_cascaded_value(qtbot, builder):
    """Closing the toggle means giving up the override: a value typed while it was open must not
    linger on screen looking like it still applies once the level no longer does."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.set_advanced_mode(True)
    panel.pulse_dur_spin.setValue(3.0)
    panel.pulse_train_level.toggle_button.click()  # expand
    panel.pulse_rep_int_spin.setValue(9.0)

    panel.pulse_train_level.toggle_button.click()  # collapse again

    assert panel.pulse_rep_int_spin.value() == pytest.approx(3.0)


def test_collapsed_pulse_train_rep_level_tracks_pulse_train_level_in_turn(qtbot, builder):
    """The second level of inheritance: Pulse Train Repetition, left collapsed, must track
    whatever Pulse Train's own currently-effective value is, itself either inherited (Pulse
    Train also collapsed) or an explicit override (Pulse Train expanded)."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.set_advanced_mode(True)
    panel.pulse_train_level.toggle_button.click()  # expand
    panel.pulse_train_dur_spin.setValue(12.0)

    assert panel.pulse_train_rep_int_spin.value() == pytest.approx(12.0)
    assert panel.pulse_train_rep_dur_spin.value() == pytest.approx(12.0 / 1e3)


def test_ramp_dur_disabled_when_rectangular_selected(qtbot, patch_config, builder):
    patch_config.set('Ramp', 'Options', 'Rectangular - no ramping\nLinear')
    patch_config.set('Ramp', 'option.rect', 'Rectangular - no ramping')

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    index = panel.ramp_shape_combo.findText('Rectangular - no ramping')
    panel.ramp_shape_combo.setCurrentIndex(index)

    assert panel.ramp_dur_spin.isEnabled() is False


def test_ramp_dur_enabled_for_a_real_ramp_shape(qtbot, patch_config, builder):
    patch_config.set('Ramp', 'Options', 'Rectangular - no ramping\nLinear')
    patch_config.set('Ramp', 'option.rect', 'Rectangular - no ramping')

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    index = panel.ramp_shape_combo.findText('Linear')
    panel.ramp_shape_combo.setCurrentIndex(index)

    assert panel.ramp_dur_spin.isEnabled() is True


def test_ramp_dur_resets_to_zero_when_switched_back_to_rectangular(qtbot, patch_config, builder):
    """A value typed in while a real ramp shape was selected must not linger, disabled but
    still nonzero, once the shape is switched back to rectangular ("no ramping"): that would
    look like it still applies even though ramping is off."""
    patch_config.set('Ramp', 'Options', 'Rectangular - no ramping\nLinear')
    patch_config.set('Ramp', 'option.rect', 'Rectangular - no ramping')
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    linear_index = panel.ramp_shape_combo.findText('Linear')
    panel.ramp_shape_combo.setCurrentIndex(linear_index)
    panel.ramp_dur_spin.setValue(5.0)

    rect_index = panel.ramp_shape_combo.findText('Rectangular - no ramping')
    panel.ramp_shape_combo.setCurrentIndex(rect_index)

    assert panel.ramp_dur_spin.value() == pytest.approx(0.0)


def test_apply_configures_timing_on_the_protocol(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.set_advanced_mode(True)
    # Both levels must actually be opened for their own field values to become explicit
    # overrides rather than being ignored in favor of the cascaded value from below (see
    # test_apply_ignores_a_collapsed_levels_stale_value_and_inherits_instead).
    panel.pulse_train_level.toggle_button.click()
    panel.pulse_train_rep_level.toggle_button.click()
    panel.pulse_dur_spin.setValue(1.0)
    panel.pulse_rep_int_spin.setValue(2.0)
    panel.pulse_train_dur_spin.setValue(10.0)
    panel.pulse_train_rep_dur_spin.setValue(0.5)  # seconds

    with qtbot.waitSignal(panel.applied, timeout=1000):
        panel.try_apply()

    assert builder.protocol.pulse_dur == pytest.approx(1.0)
    assert builder.protocol.pulse_rep_int == pytest.approx(2.0)
    # pulse_train_rep_dur is stored internally in ms: 0.5 s given above -> 500 ms.
    assert builder.protocol.pulse_train_rep_dur == pytest.approx(500.0)


def test_apply_shows_inline_error_on_fds_error(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.pulse_dur_spin.setValue(0.0)  # invalid: must be > 0

    panel.try_apply()

    assert not panel.error_label.isHidden()
    assert panel.error_label.text()


def test_demo_mode_hides_the_three_level_headers(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

    assert panel.pulse_level.toggle_button.isVisible() is False
    assert panel.pulse_train_level.toggle_button.isVisible() is False
    assert panel.pulse_train_rep_level.toggle_button.isVisible() is False
    assert panel.pulse_level.content.isVisible() is True
    assert panel.pulse_train_level.content.isVisible() is True
    assert panel.pulse_train_rep_level.content.isVisible() is True


def test_demo_mode_hides_ramp_and_pulse_train_and_pulse_train_rep_int_rows(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

    assert panel.ramp_shape_combo.isVisible() is False
    assert panel.ramp_dur_spin.isVisible() is False
    assert panel.pulse_train_dur_spin.isVisible() is False
    assert panel.pulse_train_rep_int_spin.isVisible() is False
    # Pulse duration/Pulse repetition interval are combined into one read-only display in
    # Demo mode instead (see
    # test_demo_mode_shows_a_read_only_pulse_display_instead_of_the_editable_spinboxes).
    assert panel.pulse_dur_spin.isVisible() is False
    assert panel.pulse_rep_int_spin.isVisible() is False
    assert panel.pulse_info_label.isVisible() is True
    assert panel.pulse_train_rep_dur_spin.isVisible() is True


def test_demo_mode_shows_a_read_only_pulse_display_instead_of_the_editable_spinboxes(
        qtbot, builder):
    """Demo mode's own Pulse duration/Pulse repetition interval are only ever meant to be set
    via the frequency presets/duty cycle, not typed in directly there (see
    _build_pulse_info_label()'s own docstring); Advanced mode shows the real, editable
    spinboxes instead."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()
    panel.pulse_dur_spin.setValue(3.0)
    panel.pulse_rep_int_spin.setValue(6.0)

    assert panel.pulse_info_label.text() == "3.000 ms / 6.000 ms"

    panel.set_advanced_mode(True)
    panel.pulse_train_level.toggle_button.setChecked(True)  # expand, see its own row's gating

    assert panel.pulse_dur_spin.isVisible() is True
    assert panel.pulse_rep_int_spin.isVisible() is True
    assert panel.pulse_info_label.isVisible() is False


def test_demo_mode_relabels_total_duration(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    label = panel.pulse_train_rep_level.content_form.labelForField(
        panel.pulse_train_rep_dur_spin)

    assert label.text() == "Total duration:"

    panel.set_advanced_mode(True)

    assert label.text() == "Pulse train repetition duration:"


def test_demo_mode_defaults_total_duration_to_a_usable_value(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    assert panel.pulse_train_rep_dur_spin.value() == pytest.approx(60.0)


def test_demo_mode_keeps_an_explicitly_set_total_duration(qtbot, builder):
    """Only the near-zero cascaded default is replaced (see set_advanced_mode()'s own comment
    on this); a value the researcher already set must never be silently clobbered by switching
    modes back and forth."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.pulse_train_rep_dur_spin.setValue(10.0)

    panel.set_advanced_mode(True)
    panel.set_advanced_mode(False)

    assert panel.pulse_train_rep_dur_spin.value() == pytest.approx(10.0)


def test_preset_buttons_visible_only_in_demo_mode(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

    assert panel.pulse_level.content_form.isRowVisible(panel.preset_widget) is True
    assert panel.pulse_level.content_form.isRowVisible(panel.duty_cycle_spin) is True

    panel.set_advanced_mode(True)

    assert panel.pulse_level.content_form.isRowVisible(panel.preset_widget) is False
    assert panel.pulse_level.content_form.isRowVisible(panel.duty_cycle_spin) is False


def test_frequency_preset_fills_in_pulse_duration_and_repetition_interval(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    panel._apply_frequency_preset(5)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(200.0)  # 1000 / 5 Hz
    assert panel.pulse_dur_spin.value() == pytest.approx(20.0)  # default 10% duty cycle

    panel._apply_frequency_preset(1000)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(1.0)  # 1000 / 1000 Hz
    assert panel.pulse_dur_spin.value() == pytest.approx(0.1)  # default 10% duty cycle


def test_frequency_preset_uses_the_adjusted_duty_cycle(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.duty_cycle_spin.setValue(25)

    panel._apply_frequency_preset(5)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(200.0)  # 1000 / 5 Hz
    assert panel.pulse_dur_spin.value() == pytest.approx(50.0)  # 25% duty cycle


def test_advanced_mode_shows_the_three_level_headers_and_every_row(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

    panel.set_advanced_mode(True)
    # Row visibility also requires the level itself to be expanded; a fresh protocol's Pulse
    # Train/Pulse Train Repetition levels start collapsed (see _is_inherited()).
    panel.pulse_train_level.toggle_button.setChecked(True)
    panel.pulse_train_rep_level.toggle_button.setChecked(True)

    assert panel.pulse_level.toggle_button.isVisible() is True
    assert panel.pulse_train_level.toggle_button.isVisible() is True
    assert panel.pulse_train_rep_level.toggle_button.isVisible() is True
    assert panel.ramp_shape_combo.isVisible() is True
    assert panel.ramp_dur_spin.isVisible() is True
    assert panel.pulse_train_dur_spin.isVisible() is True
    assert panel.pulse_train_rep_int_spin.isVisible() is True


def test_apply_in_demo_mode_sends_the_minimal_one_pulse_per_train_pattern(qtbot, builder):
    """Demo mode's own field selection for an IGT-backed builder (see
    TimingPanel.set_advanced_mode()'s own docstring and
    ProtocolBuilder.uses_pulse_train_repetition()): pulse_train_dur/pulse_train_rep_int are
    always left unset so configure_timing() resolves them to a single pulse per train, and
    Total duration drives the repeated train via pulse_train_rep_dur instead."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.pulse_dur_spin.setValue(1.0)
    panel.pulse_rep_int_spin.setValue(2.0)
    panel.pulse_train_rep_dur_spin.setValue(0.5)  # seconds

    with qtbot.waitSignal(panel.applied, timeout=1000):
        panel.try_apply()

    assert builder.protocol.pulse_dur == pytest.approx(1.0)
    assert builder.protocol.pulse_rep_int == pytest.approx(2.0)
    assert builder.protocol.pulse_train_dur == pytest.approx(2.0)  # inherited, 1 pulse/train
    assert builder.protocol.pulse_train_rep_dur == pytest.approx(500.0)
    assert builder.protocol.pulse_ramp_shape == builder.rectangular_ramp_shape()


def test_apply_in_demo_mode_sends_total_duration_as_pulse_train_dur_for_sonic_concepts(
        qtbot, sonic_concepts_builder):
    """Sonic Concepts has no train-repetition concept at all (see
    ProtocolBuilder.uses_pulse_train_repetition()'s own docstring): its own send_protocol()
    only ever reads pulse_train_dur as the device's total sonication duration, so Demo mode's
    Total duration must be sent as pulse_train_dur there, not pulse_train_rep_dur (which would
    be silently ignored, truncating the actual sonication to a single pulse)."""
    panel = TimingPanel(sonic_concepts_builder)
    qtbot.addWidget(panel)
    panel.pulse_dur_spin.setValue(1.0)
    panel.pulse_rep_int_spin.setValue(2.0)
    panel.pulse_train_rep_dur_spin.setValue(0.5)  # seconds

    with qtbot.waitSignal(panel.applied, timeout=1000):
        panel.try_apply()

    assert sonic_concepts_builder.protocol.pulse_train_dur == pytest.approx(500.0)  # 0.5s->500ms


def test_advanced_mode_hides_pulse_train_repetition_for_sonic_concepts(
        qtbot, sonic_concepts_builder):
    """Sonic Concepts never reads pulse_train_rep_int/pulse_train_rep_dur at all (see
    ProtocolBuilder.uses_pulse_train_repetition()'s own docstring), so offering that whole
    level in Advanced mode would only show parameters that silently do nothing."""
    panel = TimingPanel(sonic_concepts_builder)
    qtbot.addWidget(panel)
    panel.show()

    panel.set_advanced_mode(True)

    assert panel.pulse_train_rep_level.isVisible() is False


def test_advanced_mode_shows_pulse_train_repetition_for_igt(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

    panel.set_advanced_mode(True)

    assert panel.pulse_train_rep_level.isVisible() is True


def test_demo_mode_still_shows_pulse_train_repetition_for_sonic_concepts(
        qtbot, sonic_concepts_builder):
    """The level itself must stay visible in Demo mode even for Sonic Concepts: Total
    duration (pulse_train_rep_dur_spin) lives inside it, and Demo mode still needs that field
    regardless of which backend field it actually gets routed to (see _apply())."""
    panel = TimingPanel(sonic_concepts_builder)
    qtbot.addWidget(panel)
    panel.show()

    panel.set_advanced_mode(True)
    panel.set_advanced_mode(False)

    assert panel.pulse_train_rep_level.isVisible() is True
