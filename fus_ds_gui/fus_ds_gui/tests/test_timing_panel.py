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

    assert panel.pulse_train_level.content.isVisible() is True
    assert panel.pulse_train_level.is_expanded() is True


def test_pulse_train_rep_level_starts_expanded_when_already_set_explicitly(qtbot, builder):
    builder.protocol.configure_timing(pulse_dur=1.0, pulse_train_rep_int=5.0,
                                      pulse_train_rep_dur=2.0)

    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

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

    assert panel.pulse_train_level.content.isVisible() is False


def test_toggling_a_level_shows_its_fields(qtbot, builder):
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.show()

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
    level for the first time, let alone clicks Apply."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(panel.pulse_dur_spin.value())
    assert panel.pulse_train_dur_spin.value() == pytest.approx(panel.pulse_dur_spin.value())
    assert panel.pulse_train_rep_int_spin.value() == pytest.approx(panel.pulse_dur_spin.value())
    # abs=1e-3: pulse_train_rep_dur_spin only has 3 decimals (it's in seconds), so
    # pulse_dur_spin's own real, shipped default (0.25 ms -> 0.00025 s) rounds to 0.000 there,
    # a display-precision limit of the widget itself, not a cascading mismatch.
    assert panel.pulse_train_rep_dur_spin.value() == pytest.approx(
        panel.pulse_dur_spin.value() / 1e3, abs=1e-3)


def test_collapsed_pulse_train_level_tracks_pulse_duration_live(qtbot, builder):
    """The whole point of tracking live: a researcher who never opens Pulse Train can still see
    (without opening it) what it would actually resolve to, right as they type Pulse Duration,
    not a value left over from construction."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)

    panel.pulse_dur_spin.setValue(7.0)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(7.0)
    assert panel.pulse_train_dur_spin.value() == pytest.approx(7.0)


def test_expanded_pulse_train_level_is_not_overwritten_by_pulse_duration_changes(qtbot, builder):
    """Once a level is open, its own field(s) are the researcher's explicit input; changing
    Pulse Duration afterward must not silently clobber a value they already chose."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
    panel.pulse_train_level.toggle_button.click()
    panel.pulse_rep_int_spin.setValue(9.0)

    panel.pulse_dur_spin.setValue(3.0)

    assert panel.pulse_rep_int_spin.value() == pytest.approx(9.0)


def test_collapsing_a_level_resets_its_fields_to_the_cascaded_value(qtbot, builder):
    """Closing the toggle means giving up the override: a value typed while it was open must not
    linger on screen looking like it still applies once the level no longer does."""
    panel = TimingPanel(builder)
    qtbot.addWidget(panel)
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
