# -*- coding: utf-8 -*-
"""
Tests for SlotEditor. Uses the same synthetic 'UNITTEST_*' fixture shape as
test_protocol_builder.py.
"""
from types import SimpleNamespace

import pytest

from fus_driving_systems.exceptions import FDSSafetyError, FDSValidationError

from fus_ds_gui.models.protocol_builder import ProtocolBuilder
from fus_ds_gui.planning.slot_editor import SlotEditor


def _configure_driving_system(patch_config, serial, max_tran_slots=2):
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', str(max_tran_slots))
    patch_config.set(section, 'Active?', 'True')


def _configure_transducer(patch_config, serial, elements=2, min_foc=10, max_foc=80):
    section = f'Equipment.Transducer.{serial}'
    patch_config.set(section, 'Elements', str(elements))
    patch_config.set(section, 'Fund. freq.', '300')
    patch_config.set(section, 'Min. focus', str(min_foc))
    patch_config.set(section, 'Max. focus', str(max_foc))
    patch_config.set(section, 'Exit plane - first element dist.', '5')
    patch_config.set(section, 'Steer information', '')
    patch_config.set(section, 'Active?', 'True')


def _transducer_serials(combo):
    """Item 0 is always the 'no transducer selected' placeholder (itemData None, see
    SlotEditor._populate_transducer_combo()'s own docstring); every real item has a Transducer
    with its own .serial."""
    return [combo.itemData(i).serial if combo.itemData(i) is not None else None
            for i in range(combo.count())]


@pytest.fixture
def builder(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A', min_foc=10, max_foc=80)
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B', min_foc=5, max_foc=50)

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return ProtocolBuilder(ds)


def test_no_title_shown_by_default(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    assert editor._title_label.isVisible() is False


def test_title_shown_when_given(qtbot, builder):
    editor = SlotEditor(builder, title="Slot 1")
    qtbot.addWidget(editor)
    editor.show()

    assert editor._title_label.text() == "Slot 1"
    assert editor._title_label.isVisible() is True


def test_set_title_updates_the_label(qtbot, builder):
    editor = SlotEditor(builder, title="Slot 1")
    qtbot.addWidget(editor)

    editor.set_title("Slot 2")

    assert editor._title_label.text() == "Slot 2"


def test_populates_transducer_and_option_dropdowns(qtbot, builder):
    """A fresh editor starts on the 'no transducer selected' placeholder (see
    SlotEditor._populate_transducer_combo()'s own docstring), not auto-picking the first
    compatible transducer."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    assert _transducer_serials(editor.transducer_combo) == [
        None, 'UNITTEST_TRAN_A', 'UNITTEST_TRAN_B']
    assert editor.transducer_combo.currentData() is None
    assert editor.focus_option_combo.currentText() == 'Focus wrt exit plane [mm]'
    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'


def test_other_fields_hidden_until_a_transducer_is_chosen(qtbot, builder):
    """Focus/power ranges, calibration availability, and dephasing element counts all depend
    on which transducer is picked, so showing these fields with meaningless defaults before
    that choice is made would look like something already worth configuring (see
    _update_transducer_dependent_visibility()'s own docstring)."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.show()

    assert editor.focus_option_combo.isVisible() is False
    assert editor.focus_value_spin.isVisible() is False
    assert editor.focus_value_xyz_widget.isVisible() is False
    assert editor.power_option_combo.isVisible() is False
    assert editor.power_value_spin.isVisible() is False
    assert editor.oper_freq_spin.isVisible() is False
    assert editor.dephasing_mode_combo.isVisible() is False


def test_other_fields_shown_once_a_transducer_is_chosen_in_advanced_mode(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.show()
    editor.set_advanced_mode(True)

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    assert editor.focus_option_combo.isVisible() is True
    assert editor.focus_option_combo.isEnabled() is True
    assert editor.focus_value_spin.isVisible() is True
    assert editor.power_option_combo.isVisible() is True
    assert editor.power_option_combo.isEnabled() is True
    assert editor.power_value_spin.isVisible() is True
    assert editor.oper_freq_spin.isVisible() is True
    assert editor.dephasing_mode_combo.isVisible() is True


def test_demo_mode_still_shows_the_option_pickers_once_a_transducer_is_chosen(qtbot, builder):
    """Demo mode (the default, see set_advanced_mode()'s own docstring) only hides oper_freq/
    dephasing: the focus/power option pickers stay visible and editable in either mode, since
    every offered option is already non-engineering-only."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.show()

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    assert editor.focus_option_combo.isVisible() is True
    assert editor.focus_option_combo.isEnabled() is True
    assert editor.focus_option_combo.currentText() == 'Focus wrt exit plane [mm]'
    assert editor.focus_value_spin.isVisible() is True
    assert editor.power_option_combo.isVisible() is True
    assert editor.power_option_combo.isEnabled() is True
    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'
    assert editor.power_value_spin.isVisible() is True
    assert editor.oper_freq_spin.isVisible() is False
    assert editor.dephasing_mode_combo.isVisible() is False


def test_demo_mode_shows_a_non_pressure_power_option_too(qtbot, patch_config):
    """A driving system whose only power option is global power (e.g. Sonic Concepts) must
    show that correctly too, not just IGT's own pressure option."""
    _configure_driving_system(patch_config, 'UNITTEST_SC')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Manufacturer', 'Sonic Concepts')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Power options', 'Global power [mW]')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Native power parameters',
                     'Global power [mW]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')
    builder = ProtocolBuilder(ds)
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(1)

    assert editor.power_option_combo.currentText() == 'Global power [mW]'
    assert editor.power_option_combo.isEnabled() is True


def test_other_fields_hide_again_when_switching_back_to_the_placeholder(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.show()
    editor.set_advanced_mode(True)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    editor.transducer_combo.setCurrentIndex(0)  # back to "-- Select a transducer --"

    assert editor.focus_option_combo.isVisible() is False
    assert editor.power_option_combo.isVisible() is False
    assert editor.dephasing_mode_combo.isVisible() is False


def test_focus_range_follows_selected_transducer(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B: min_foc=5, max_foc=50

    assert editor.focus_value_spin.minimum() == pytest.approx(5)
    assert editor.focus_value_spin.maximum() == pytest.approx(50)


def test_focus_range_is_shown_in_the_row_label_and_tooltip(qtbot, builder):
    """QDoubleSpinBox silently clamps an out-of-range typed value with no visual cue at all, so
    the valid range needs to be visible up front rather than discovered by trial and error."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B: min_foc=5, max_foc=50

    # A whole-number bound must still show a decimal (5.0, not 5): otherwise it reads as a
    # rounded display value rather than the actual, exact bound.
    assert '5.0' in editor._focus_value_label.text()
    assert '50.0' in editor._focus_value_label.text()
    assert '5.0' in editor.focus_value_spin.toolTip()
    assert '50.0' in editor.focus_value_spin.toolTip()


def _build_editor_with_mid_bowl_focus_option(patch_config, focus_options=(
        'Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]')):
    """Doesn't use the `builder` fixture above, same reasoning as
    _build_editor_with_xyz_focus_option's own docstring further below: the 'Focus options'
    override here must be in place *before* ProtocolBuilder is constructed."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT')
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Focus options',
                     '\n'.join(focus_options))
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    # exit_plane_dist=5 for both, see _configure_transducer.
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A', min_foc=10, max_foc=80)
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B', min_foc=5, max_foc=50)

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return SlotEditor(ProtocolBuilder(ds))


def test_focus_range_is_offset_by_exit_plane_dist_for_mid_bowl_option(qtbot, patch_config):
    """transducer.min_foc/max_foc are wrt-exit-plane bounds; the scalar 'wrt mid bowl' option's
    actual valid range is offset by exit_plane_dist (see SlotEditor._focus_range_offset()'s own
    docstring, and TransducerSlot._set_focus_wrt_mid_bowl()'s own conversion this mirrors)."""
    editor = _build_editor_with_mid_bowl_focus_option(patch_config)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: min_foc=10, max_foc=80
    index = editor.focus_option_combo.findText('Focus wrt mid bowl [mm]')

    editor.focus_option_combo.setCurrentIndex(index)

    assert editor.focus_value_spin.minimum() == pytest.approx(15)  # 10 + 5
    assert editor.focus_value_spin.maximum() == pytest.approx(85)  # 80 + 5
    # Derived via exit_plane_dist, not read directly from config: labeled as an estimate,
    # since an active calibration curve's own range could differ from this.
    assert 'estimate' in editor._focus_value_label.text()
    assert 'estimate' in editor.focus_value_spin.toolTip().lower()


def test_focus_range_reverts_when_switching_back_to_wrt_exit_plane(qtbot, patch_config):
    editor = _build_editor_with_mid_bowl_focus_option(patch_config)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: min_foc=10, max_foc=80
    bowl_index = editor.focus_option_combo.findText('Focus wrt mid bowl [mm]')
    editor.focus_option_combo.setCurrentIndex(bowl_index)
    exit_index = editor.focus_option_combo.findText('Focus wrt exit plane [mm]')

    editor.focus_option_combo.setCurrentIndex(exit_index)

    assert editor.focus_value_spin.minimum() == pytest.approx(10)
    assert editor.focus_value_spin.maximum() == pytest.approx(80)
    # No offset applied here, so no estimate caveat either: this is the transducer's own
    # directly-configured range, not a derived one.
    assert 'estimate' not in editor._focus_value_label.text()


def test_default_focus_value_is_offset_when_mid_bowl_is_the_only_option(qtbot, patch_config):
    """When a driving system's own focus_options don't even include the plain exit-plane option
    (e.g. the Clover-compatible 256-ch driving systems), the mid-bowl option is the only one
    available, so selecting a transducer must reset to the offset-aware default, not just the
    plain min_foc (see _on_transducer_changed()'s own docstring)."""
    editor = _build_editor_with_mid_bowl_focus_option(
        patch_config, focus_options=('Focus wrt mid bowl [mm]',))
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: min_foc=10, exit_plane_dist=5

    assert editor.focus_value_spin.value() == pytest.approx(15)  # 10 + 5


def test_apply_raises_when_no_transducer_is_selected(qtbot, builder):
    """The placeholder is itself a valid, expected state (not achievable through the old
    'auto-picks the first transducer' default, see _populate_transducer_combo()'s own
    docstring), so Apply must still give a clear, actionable error rather than crash."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.try_apply()

    assert editor.slot is None
    assert 'Choose a transducer first' in editor.error_label.text()


def test_apply_adds_a_new_slot(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)

    with qtbot.waitSignal(editor.applied, timeout=1000):
        editor.try_apply()

    assert editor.slot is not None
    assert len(builder.protocol.slots) == 1
    assert editor.error_label.isHidden()


def test_apply_shows_inline_error_on_fds_error(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    # A pressure far above the configured safety limit; see FDSSafetyError in
    # transducer_slot.py's _enforce_max_pressure().
    editor.power_value_spin.setValue(999.0)

    editor.try_apply()

    assert editor.slot is None
    assert not editor.error_label.isHidden()
    assert editor.error_label.text()
    # A plain-colored message blends in with the rest of the tab; see ApplyPanel.__init__.
    assert 'red' in editor.error_label.styleSheet()


def test_apply_refuses_pressure_above_the_demo_cap_in_demo_mode(qtbot, builder, patch_config):
    patch_config.set('Power', 'Demo maximum pressure allowed in free water [MPa]', '0.5')
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.power_value_spin.setValue(0.6)  # above the demo cap, below the backend's own limit

    editor.try_apply()

    assert editor.slot is None
    assert 'Demo mode' in editor.error_label.text()


def test_apply_allows_pressure_above_the_demo_cap_in_advanced_mode(qtbot, builder, patch_config):
    patch_config.set('Power', 'Demo maximum pressure allowed in free water [MPa]', '0.5')
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.set_advanced_mode(True)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.6)  # above the demo cap, still below the backend's limit

    editor.try_apply()

    assert editor.slot is not None
    assert editor.error_label.isHidden()


def test_apply_allows_pressure_at_the_demo_cap_in_demo_mode(qtbot, builder, patch_config):
    patch_config.set('Power', 'Demo maximum pressure allowed in free water [MPa]', '0.5')
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)  # exactly at the cap: strict '>', not '>='

    editor.try_apply()

    assert editor.slot is not None
    assert editor.error_label.isHidden()


def test_apply_edits_an_already_added_slot_without_re_adding(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    editor.try_apply()
    first_slot = editor.slot

    editor.focus_value_spin.setValue(30)
    editor.try_apply()

    assert editor.slot is first_slot
    assert len(builder.protocol.slots) == 1
    assert editor.slot.focus_wrt_exit_plane == pytest.approx(30)


def test_oper_freq_starts_at_zero_before_a_transducer_is_selected(qtbot, builder):
    """Matches focus_value_spin/power_value_spin's own resting value while nothing is selected
    yet; Apply already blocks on "Choose a transducer first." before oper_freq is ever read, so
    the range briefly allowing 0 here is never actually reachable at Apply."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    assert editor.oper_freq_spin.value() == 0


def test_oper_freq_defaults_to_the_transducers_fundamental_frequency(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: fund_freq=300

    assert editor.oper_freq_spin.value() == 300
    assert editor.oper_freq_spin.minimum() == 1


def test_oper_freq_resets_to_zero_when_deselecting_the_transducer(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    editor.transducer_combo.setCurrentIndex(0)  # -- Select a transducer --

    assert editor.oper_freq_spin.value() == 0
    assert editor.oper_freq_spin.minimum() == 0


def test_dephasing_value_rows_toggle_with_the_selected_mode(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    assert editor._form.isRowVisible(editor.dephasing_degree_spin) is False
    assert editor._form.isRowVisible(editor.dephasing_values_edit) is False

    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic

    assert editor._form.isRowVisible(editor.dephasing_degree_spin) is True
    assert editor._form.isRowVisible(editor.dephasing_values_edit) is False

    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override

    assert editor._form.isRowVisible(editor.dephasing_degree_spin) is False
    assert editor._form.isRowVisible(editor.dephasing_values_edit) is True


def test_apply_defaults_dephasing_degree_to_none(qtbot, builder):
    """Matches TransducerSlot.dephasing_degree's own default ("None = no dephasing"); the mode
    combo starts on "No dephasing", so a researcher who never touches it gets exactly that."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    editor.try_apply()

    assert editor.slot.dephasing_degree is None


def test_apply_adds_a_new_slot_with_oper_freq_and_cyclic_dephasing(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.oper_freq_spin.setValue(500)
    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic
    editor.dephasing_degree_spin.setValue(45.0)

    editor.try_apply()

    assert editor.slot.oper_freq == 500
    assert editor.slot.dephasing_degree == [45.0]


def test_apply_adds_a_new_slot_with_a_per_element_dephasing_override(qtbot, builder):
    """UNITTEST_TRAN_A has 2 elements (see _configure_transducer's own default)."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("10, 20")

    editor.try_apply()

    assert editor.slot.dephasing_degree == [10.0, 20.0]


def test_apply_rejects_a_per_element_override_with_the_wrong_count(qtbot, builder):
    """The backend itself only catches this much later (IGT._define_pulse_group(), reached only
    once Send/Execute exists), so _apply() must check it itself, synchronously."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: 2 elements
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("10, 20, 30")

    editor.try_apply()

    assert editor.slot is None
    assert 'does not correspond to number of transducer elements' in editor.error_label.text()


def test_apply_rejects_unparseable_per_element_values(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("not, numbers")

    editor.try_apply()

    assert editor.slot is None
    assert 'comma-separated list of numbers' in editor.error_label.text()


def test_apply_updates_transducer_forwards_oper_freq_and_dephasing_degree(qtbot, builder):
    """Covers the update_transducer() branch of _apply() (an already-added slot whose transducer
    changes), not just the add_slot() one above."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.try_apply()

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B
    editor.oper_freq_spin.setValue(700)
    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic
    editor.dephasing_degree_spin.setValue(120.0)
    editor.try_apply()

    assert editor.slot.transducer.serial == 'UNITTEST_TRAN_B'
    assert editor.slot.oper_freq == 700
    assert editor.slot.dephasing_degree == [120.0]


def test_changing_transducer_resets_value_fields(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    editor.oper_freq_spin.setValue(999)
    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B: min_foc=5, max_foc=50

    # Resets to the new transducer's own min_foc, not a hardcoded 0: 0 isn't necessarily even
    # a valid focus value for every transducer.
    assert editor.focus_value_spin.value() == pytest.approx(5.0)
    assert editor.power_value_spin.value() == 0.0
    # Mirrors TransducerSlot.update_transducer()'s own documented reset behavior: oper_freq
    # falls back to the new transducer's own fund_freq, dephasing always resets to "no
    # dephasing".
    assert editor.oper_freq_spin.value() == 300
    assert editor.dephasing_mode_combo.currentText() == 'No dephasing'


def test_changing_transducer_updates_the_per_element_values_tooltip(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: 2 elements

    assert 'exactly 2' in editor.dephasing_values_edit.toolTip()


def test_changing_transducer_emits_selection_changed(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    with qtbot.waitSignal(editor.transducer_selection_changed, timeout=1000):
        editor.transducer_combo.setCurrentIndex(1)


def test_set_excluded_transducers_removes_it_from_the_dropdown(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)

    editor.set_excluded_transducers({'UNITTEST_TRAN_B'})

    assert _transducer_serials(editor.transducer_combo) == [None, 'UNITTEST_TRAN_A']


def test_set_excluded_transducers_never_excludes_its_own_current_selection(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B

    # Excluding UNITTEST_TRAN_B here represents another editor's own selection, not this one's
    # own: PlanningTab never asks an editor to exclude its own current pick (see
    # PlanningTab._refresh_transducer_exclusions()), but even if it did, this must not blank out
    # the field the researcher is actively looking at.
    editor.set_excluded_transducers({'UNITTEST_TRAN_B'})

    assert editor.transducer_combo.currentData().serial == 'UNITTEST_TRAN_B'


def test_clearing_exclusion_restores_the_transducer(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.set_excluded_transducers({'UNITTEST_TRAN_B'})

    editor.set_excluded_transducers(set())

    assert _transducer_serials(editor.transducer_combo) == [
        None, 'UNITTEST_TRAN_A', 'UNITTEST_TRAN_B']


def test_existing_slot_prefills_every_field(qtbot, builder):
    """Matches PlanningTab.load_protocol()'s own use: one SlotEditor per already-configured
    TransducerSlot, e.g. one from protocol_io.load(), pre-filled rather than blank."""
    slot = builder.add_slot('UNITTEST_TRAN_A', 'Focus wrt exit plane [mm]', 20,
                            'Max. pressure in free water [MPa]', 0.5, oper_freq=500,
                            dephasing_degree=[90.0])

    editor = SlotEditor(builder, existing_slot=slot)
    qtbot.addWidget(editor)

    assert editor.slot is slot
    assert editor.transducer_combo.currentData().serial == 'UNITTEST_TRAN_A'
    assert editor.focus_option_combo.currentText() == 'Focus wrt exit plane [mm]'
    assert editor.focus_value_spin.value() == pytest.approx(20)
    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'
    assert editor.power_value_spin.value() == pytest.approx(0.5)
    assert editor.oper_freq_spin.value() == 500
    assert editor.dephasing_mode_combo.currentText() == 'Cyclic (one degree, applied to every ' \
                                                        'element)'
    assert editor.dephasing_degree_spin.value() == pytest.approx(90.0)


def test_existing_slot_with_no_dephasing_selects_that_mode(qtbot, builder):
    slot = builder.add_slot('UNITTEST_TRAN_A', 'Focus wrt exit plane [mm]', 20,
                            'Max. pressure in free water [MPa]', 0.5)

    editor = SlotEditor(builder, existing_slot=slot)
    qtbot.addWidget(editor)

    assert editor.dephasing_mode_combo.currentText() == 'No dephasing'


def test_existing_slot_with_per_element_dephasing_prefills_the_text_field(qtbot, builder):
    """UNITTEST_TRAN_A has 2 elements (see _configure_transducer's own default)."""
    slot = builder.add_slot('UNITTEST_TRAN_A', 'Focus wrt exit plane [mm]', 20,
                            'Max. pressure in free water [MPa]', 0.5,
                            dephasing_degree=[10.0, 20.0])

    editor = SlotEditor(builder, existing_slot=slot)
    qtbot.addWidget(editor)

    assert editor.dephasing_mode_combo.currentText() == (
        'Per-element override (one phase value per element)')
    assert editor.dephasing_values_edit.text() == '10.0, 20.0'


def test_editing_and_reapplying_an_existing_slot_configures_it_in_place(qtbot, builder):
    slot = builder.add_slot('UNITTEST_TRAN_A', 'Focus wrt exit plane [mm]', 20,
                            'Max. pressure in free water [MPa]', 0.5)
    editor = SlotEditor(builder, existing_slot=slot)
    qtbot.addWidget(editor)
    editor.focus_value_spin.setValue(30)

    editor.try_apply()

    assert editor.slot is slot
    assert len(builder.protocol.slots) == 1
    assert slot.focus_wrt_exit_plane == pytest.approx(30)


def test_existing_slot_with_a_list_power_value_shows_the_first_entry(qtbot, builder):
    """See _load_existing_slot()'s own comment on the same list case (Amplitude [%]/
    Voltage [V]): power_value_spin only ever shows/sends a single, shared value."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    tran_a = editor.transducer_combo.itemData(1)  # UNITTEST_TRAN_A
    stand_in_slot = SimpleNamespace(
        transducer=tran_a, chosen_focus='Focus wrt exit plane [mm]', chosen_focus_value=20,
        chosen_power='Amplitude [%]', chosen_power_value=[70.0, 80.0], oper_freq=300,
        dephasing_degree=None)

    editor._load_existing_slot(stand_in_slot)

    assert editor.power_value_spin.value() == pytest.approx(70.0)


def test_existing_slot_with_a_list_power_value_flags_it_immediately(qtbot, builder):
    """Matches how a failed slot_def's own problem is shown right away (see
    _load_failed_slot()): a researcher shouldn't have to click Apply first just to discover
    that editing this slot's power value isn't supported yet."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    tran_a = editor.transducer_combo.itemData(1)  # UNITTEST_TRAN_A
    stand_in_slot = SimpleNamespace(
        transducer=tran_a, chosen_focus='Focus wrt exit plane [mm]', chosen_focus_value=20,
        chosen_power='Amplitude [%]', chosen_power_value=[70.0, 80.0], oper_freq=300,
        dephasing_degree=None)

    editor._load_existing_slot(stand_in_slot)

    assert not editor.error_label.isHidden()
    assert 'per element' in editor.error_label.text()


def test_reapplying_an_existing_slot_with_a_list_power_value_is_refused(qtbot, builder):
    """Editing/re-applying such a slot isn't supported yet (see _apply()'s own comment): Apply
    must refuse it rather than silently collapse the per-element list into power_value_spin's
    own single, shared value."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    tran_a = editor.transducer_combo.itemData(1)  # UNITTEST_TRAN_A
    stand_in_slot = SimpleNamespace(
        transducer=tran_a, chosen_focus='Focus wrt exit plane [mm]', chosen_focus_value=20,
        chosen_power='Amplitude [%]', chosen_power_value=[70.0, 80.0], oper_freq=300,
        dephasing_degree=None)
    editor._load_existing_slot(stand_in_slot)

    editor.try_apply()

    assert not editor.error_label.isHidden()
    assert 'per element' in editor.error_label.text()
    assert stand_in_slot.chosen_power_value == [70.0, 80.0]  # untouched


def test_reapplying_an_existing_slot_allows_a_genuinely_different_power_value(qtbot, builder):
    """Typing a genuinely different value into power_value_spin -- even for the very same
    per-element power option the slot already had -- is a deliberate choice of one shared value
    for every element, not the accidental resend the guard above exists for."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    tran_a = editor.transducer_combo.itemData(1)  # UNITTEST_TRAN_A
    calls = []
    stand_in_slot = SimpleNamespace(
        transducer=tran_a, chosen_focus='Focus wrt exit plane [mm]', chosen_focus_value=20,
        chosen_power='Amplitude [%]', chosen_power_value=[70.0, 80.0], oper_freq=300,
        dephasing_degree=None, configure=lambda *args: calls.append(args))
    editor._load_existing_slot(stand_in_slot)
    editor.power_value_spin.setValue(50)  # genuinely different from the pre-filled 70.0

    editor.try_apply()

    assert len(calls) == 1
    assert editor.error_label.isHidden()


def test_reapplying_an_existing_slot_allows_switching_to_another_power_option(qtbot, builder):
    """Deliberately choosing a different, real power option (not just leaving the slot's own
    per-element one in place) is a legitimate, explicit edit, not the silent flattening the
    guard above exists for -- it must be allowed to configure() the slot in place."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    tran_a = editor.transducer_combo.itemData(1)  # UNITTEST_TRAN_A
    calls = []
    stand_in_slot = SimpleNamespace(
        transducer=tran_a, chosen_focus='Focus wrt exit plane [mm]', chosen_focus_value=20,
        chosen_power='Amplitude [%]', chosen_power_value=[70.0, 80.0], oper_freq=300,
        dephasing_degree=None, configure=lambda *args: calls.append(args))
    editor._load_existing_slot(stand_in_slot)
    index = editor.power_option_combo.findText('Max. pressure in free water [MPa]')
    editor.power_option_combo.setCurrentIndex(index)
    editor.power_value_spin.setValue(0.5)

    editor.try_apply()

    assert calls == [('Focus wrt exit plane [mm]', 20.0, 'Max. pressure in free water [MPa]',
                      0.5)]
    assert editor.error_label.isHidden()


def test_failed_slot_with_an_out_of_range_focus_value_shows_it_unclamped(qtbot, builder):
    """A focus_value past the selected transducer's own min/max (10-80 here, see the builder
    fixture) must not be silently clamped by focus_value_spin's own normal range: the whole
    point of showing a failed slot's raw values is to let the researcher see exactly what was
    wrong, not a plausible-looking value the widget quietly substituted instead (see
    _widen_range_to_fit())."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 200,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 0.5,
    }

    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('too far')))
    qtbot.addWidget(editor)

    assert editor.focus_value_spin.value() == pytest.approx(200)


def test_choosing_a_real_focus_option_flags_rather_than_overwrites_an_out_of_range_value(
        qtbot, builder):
    """Reported scenario: a failed slot_def named an unrecognized focus_option alongside a
    focus_value that's out of range for this transducer (200, vs. 10-80, see the builder
    fixture). Picking a real focus_option afterward must not silently narrow
    focus_value_spin's own range back down and clamp that value away -- it must stay visible,
    flagged via error_label instead (see _update_focus_range()'s own docstring)."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Not A Real Focus Option',
        'focus_value': 200,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 0.5,
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('unrecognized')))
    qtbot.addWidget(editor)
    index = editor.focus_option_combo.findText('Focus wrt exit plane [mm]')

    editor.focus_option_combo.setCurrentIndex(index)

    assert editor.focus_value_spin.value() == pytest.approx(200)
    assert not editor.error_label.isHidden()
    assert 'outside' in editor.error_label.text()


def test_changing_transducer_stops_flagging_a_failed_slots_raw_focus_value(qtbot, builder):
    """A different transducer already resets focus_value_spin to its own default a few lines
    later in _on_transducer_changed() regardless, so the raw-value flag must be cleared first,
    not linger and get (re-)shown against a value that's already on its way out."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Not A Real Focus Option',
        'focus_value': 200,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 0.5,
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('unrecognized')))
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B

    assert editor._raw_focus_value is None
    assert editor.focus_value_spin.value() != pytest.approx(200)


def test_failed_slot_with_an_unrecognized_power_option_shows_it_verbatim(qtbot, builder):
    """A power_option string this driving system doesn't currently offer must be shown exactly
    as the file gave it, not silently replaced by whichever real option the combo already
    happens to default to (see _select_or_show_raw())."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Not A Real Power Option',
        'power_value': 0.5,
    }

    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('bad option')))
    qtbot.addWidget(editor)

    assert editor.power_option_combo.currentText() == 'Not A Real Power Option'


def test_raw_power_option_is_removed_once_a_real_one_is_deliberately_chosen(qtbot, builder):
    """The one-off raw item _select_or_show_raw() inserts must not linger in the combo forever:
    once the researcher deliberately picks a real option instead, _prune_raw_option() must drop
    it, so it can't be mistaken for a real, still-available choice later."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Not A Real Power Option',
        'power_value': 0.5,
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('bad option')))
    qtbot.addWidget(editor)
    assert editor.power_option_combo.findText('Not A Real Power Option') >= 0
    index = editor.power_option_combo.findText('Max. pressure in free water [MPa]')

    editor.power_option_combo.setCurrentIndex(index)
    editor.power_option_combo.activated.emit(index)  # only a real interaction prunes it

    assert editor.power_option_combo.findText('Not A Real Power Option') == -1
    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'


def test_raw_power_option_stays_if_reselected_via_the_dropdown(qtbot, builder):
    """Re-picking the very same raw item (a no-op reselection) must not prune it -- only moving
    away from it should."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Not A Real Power Option',
        'power_value': 0.5,
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('bad option')))
    qtbot.addWidget(editor)
    raw_index = editor.power_option_combo.findText('Not A Real Power Option')

    editor.power_option_combo.activated.emit(raw_index)

    assert editor.power_option_combo.findText('Not A Real Power Option') == raw_index


def test_failed_slot_prefills_every_field_and_shows_the_error(qtbot, builder):
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 2.0,
        'oper_freq': 310,
        'dephasing_degree': None,
    }
    exc = FDSSafetyError('Maximum pressure exceeded.')

    editor = SlotEditor(builder, failed_slot=(slot_def, exc))
    qtbot.addWidget(editor)

    assert editor.slot is None
    assert editor.transducer_combo.currentData().serial == 'UNITTEST_TRAN_A'
    assert editor.focus_option_combo.currentText() == 'Focus wrt exit plane [mm]'
    assert editor.focus_value_spin.value() == pytest.approx(20)
    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'
    assert editor.power_value_spin.value() == pytest.approx(2.0)
    assert editor.oper_freq_spin.value() == 310
    assert not editor.error_label.isHidden()
    assert 'Maximum pressure exceeded' in editor.error_label.text()


def test_failed_slot_with_a_missing_power_option_leaves_the_combo_untouched(qtbot, builder):
    """slot_def.get('power_option') can come back None (the key was missing entirely, as opposed
    to naming an unrecognized option): _select_or_show_raw() must not insert a blank/None item
    for that, it should just leave the combo at whatever it already defaulted to."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_value': 0.5,
    }

    exc = FDSValidationError('missing power_option')
    editor = SlotEditor(builder, failed_slot=(slot_def, exc))
    qtbot.addWidget(editor)

    assert editor.power_option_combo.currentText() == 'Max. pressure in free water [MPa]'


def test_failed_slot_with_unknown_transducer_leaves_the_placeholder_selected(qtbot, builder):
    """A slot_def naming a transducer this driving system doesn't even offer (or that failed on
    the transducer step itself) still shows every other field, rather than crashing looking one
    up that was never there. This is the one case _update_transducer_dependent_visibility()'s
    own "nothing to show without a transducer" default must NOT apply to (see
    _load_failed_slot()'s own docstring): the raw values still need reviewing regardless."""

    slot_def = {
        'transducer_serial': 'NOT_A_REAL_TRANSDUCER',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 0.5,
    }
    exc = FDSValidationError('Unknown transducer serial.')

    editor = SlotEditor(builder, failed_slot=(slot_def, exc))
    qtbot.addWidget(editor)
    editor.show()

    assert editor.transducer_combo.currentData() is None
    assert 'Unknown transducer serial' in editor.error_label.text()
    assert editor.focus_option_combo.isVisible() is True
    assert editor.power_option_combo.isVisible() is True
    assert editor.power_value_spin.isVisible() is True


def test_failed_slot_can_still_be_applied_as_a_new_slot(qtbot, builder):
    """Never edited in place (unlike existing_slot): this slot was never actually added, so a
    successful Apply after fixing the value goes through the normal "add a new slot" path."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 2.0,
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSSafetyError('too high')))
    qtbot.addWidget(editor)
    editor.power_value_spin.setValue(0.5)  # fix the value that failed

    editor.try_apply()

    assert editor.slot is not None
    assert len(builder.protocol.slots) == 1
    assert editor.error_label.isHidden()


def test_failed_slot_with_an_untouched_list_power_value_cannot_silently_apply_a_flattened_one(
        qtbot, builder):
    """Clicking Apply without ever touching power_value_spin -- it still shows exactly the
    file's own per-element list's first entry, unchanged -- must not silently add a new slot
    with a flattened scalar in place of that list. This is checked directly
    (_per_element_power_option/_per_element_power_first_value), not left to whatever each
    backend power setter's own engineering-mode gate happens to enforce: which options require
    engineering_mode is itself config-driven per institution (see
    TransducerSlot._requires_engineering_mode()'s own docstring), so it can't be relied on as an
    implicit safety net here."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Amplitude [%]',
        'power_value': [999.0, 999.0],
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('boom')))
    qtbot.addWidget(editor)

    editor.try_apply()  # power_value_spin left exactly as pre-filled

    assert editor.slot is None
    assert 'per element' in editor.error_label.text()


def test_failed_slot_with_a_list_power_value_allows_a_genuinely_different_value(qtbot, builder):
    """Typing a genuinely different value into power_value_spin -- even for the very same
    per-element power option the file gave -- is a deliberate choice of one shared value for
    every element, not the accidental resend the guard above exists for. Apply must be allowed
    to proceed (a different, real validation problem may still turn up, but that's the
    backend's own concern, not this guard's)."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Amplitude [%]',
        'power_value': [999.0, 999.0],
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('boom')))
    qtbot.addWidget(editor)
    editor.power_value_spin.setValue(50)  # genuinely different from the pre-filled 999.0

    editor.try_apply()

    assert 'per element' not in editor.error_label.text()


def test_failed_slot_with_a_list_power_value_allows_switching_to_another_power_option(
        qtbot, builder):
    """Deliberately choosing a different, real power option (not just leaving the file's own
    per-element one in place) is a legitimate, explicit edit, not the silent flattening
    _per_element_power_option guards against -- it must be allowed to add a new slot."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Amplitude [%]',
        'power_value': [999.0, 999.0],
    }
    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('boom')))
    qtbot.addWidget(editor)
    index = editor.power_option_combo.findText('Max. pressure in free water [MPa]')
    editor.power_option_combo.setCurrentIndex(index)
    editor.power_value_spin.setValue(0.5)

    editor.try_apply()

    assert editor.slot is not None
    assert editor.error_label.isHidden()


def test_failed_slot_with_a_list_power_value_shows_the_first_entry(qtbot, builder):
    """See _load_existing_slot()'s own comment on the same list case (Amplitude [%]/
    Voltage [V]): power_value_spin only ever shows/sends a single, shared value."""
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_A',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 20,
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': [0.7],
    }

    editor = SlotEditor(builder, failed_slot=(slot_def, FDSValidationError('boom')))
    qtbot.addWidget(editor)

    assert editor.power_value_spin.value() == pytest.approx(0.7)


def test_failed_slot_with_xyz_focus_prefills_the_xyz_fields(qtbot, patch_config):
    """Mirrors test_existing_slot_with_xyz_focus_prefills_the_xyz_fields, for the failed_slot
    pre-fill path instead."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT')
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Focus options',
                     'Focus wrt exit plane [mm]\nFocus xyz wrt exit plane [mm]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')
    patch_config.set('Equipment.Transducer.UNITTEST_TRAN_B', 'Can 3D steer?', 'True')
    patch_config.set('Equipment.Transducer.UNITTEST_TRAN_B', 'Steer information',
                     'unittest_steer.ini')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    slot_def = {
        'transducer_serial': 'UNITTEST_TRAN_B',
        'focus_option': 'Focus xyz wrt exit plane [mm]',
        'focus_value': [1.0, 2.0, 30.0],
        'power_option': 'Max. pressure in free water [MPa]',
        'power_value': 0.5,
    }

    editor = SlotEditor(ProtocolBuilder(ds), failed_slot=(slot_def, FDSValidationError('boom')))
    qtbot.addWidget(editor)

    assert editor.focus_value_x_spin.value() == pytest.approx(1.0)
    assert editor.focus_value_y_spin.value() == pytest.approx(2.0)
    assert editor.focus_value_z_spin.value() == pytest.approx(30.0)


def _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=False):
    """Doesn't use the `builder` fixture above: ProtocolBuilder.__init__ re-reads
    DrivingSystem/focus_options fresh from config at construction time (see TUSProtocol.
    __init__), so the 'Focus options' override here must be in place *before* ProtocolBuilder is
    constructed, not applied to an already-built one."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT')
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Focus options',
                     'Focus wrt exit plane [mm]\nFocus xyz wrt exit plane [mm]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')
    if tran_b_can_3d_steer:
        patch_config.set('Equipment.Transducer.UNITTEST_TRAN_B', 'Can 3D steer?', 'True')
        patch_config.set('Equipment.Transducer.UNITTEST_TRAN_B', 'Steer information',
                         'unittest_steer.ini')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return SlotEditor(ProtocolBuilder(ds))


def test_focus_xyz_option_hidden_for_a_non_3d_steering_transducer(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config)
    qtbot.addWidget(editor)

    options = [editor.focus_option_combo.itemText(i)
               for i in range(editor.focus_option_combo.count())]
    assert options == ['Focus wrt exit plane [mm]']


def test_focus_xyz_option_appears_for_a_3d_steering_capable_transducer(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B, now 3D-steering-capable

    options = [editor.focus_option_combo.itemText(i)
               for i in range(editor.focus_option_combo.count())]
    assert options == ['Focus wrt exit plane [mm]', 'Focus xyz wrt exit plane [mm]']


def test_single_focus_field_shown_by_default(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)
    editor.show()
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: no xyz option unlocked

    assert editor.focus_value_spin.isVisible() is True
    assert editor.focus_value_xyz_widget.isVisible() is False


def test_xyz_fields_shown_when_xyz_option_selected(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)
    editor.show()
    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B: unlocks the xyz option

    index = editor.focus_option_combo.findText('Focus xyz wrt exit plane [mm]')
    editor.focus_option_combo.setCurrentIndex(index)

    assert editor.focus_value_spin.isVisible() is False
    assert editor.focus_value_xyz_widget.isVisible() is True


def test_switching_transducer_away_from_3d_steering_reverts_to_single_field(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)
    editor.show()
    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B
    index = editor.focus_option_combo.findText('Focus xyz wrt exit plane [mm]')
    editor.focus_option_combo.setCurrentIndex(index)
    assert editor.focus_value_xyz_widget.isVisible() is True

    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: not 3D-steering-capable

    assert editor.focus_value_spin.isVisible() is True
    assert editor.focus_value_xyz_widget.isVisible() is False


def test_apply_passes_an_x_y_z_tuple_for_the_xyz_focus_option(qtbot, patch_config):
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B
    index = editor.focus_option_combo.findText('Focus xyz wrt exit plane [mm]')
    editor.focus_option_combo.setCurrentIndex(index)
    editor.focus_value_x_spin.setValue(1.0)
    editor.focus_value_y_spin.setValue(2.0)
    editor.focus_value_z_spin.setValue(30.0)
    editor.power_value_spin.setValue(0.5)

    editor.try_apply()

    # 'Focus xyz wrt exit plane [mm]' isn't UNITTEST_IGT's native focus param in this fixture
    # (only the plain, non-xyz exit-plane option is), so _set_focus_xyz() needs a real
    # calibration curve to convert it, which this synthetic, no-active-combo transducer
    # doesn't have (matching every other "no active calibration" case in this file). This test
    # only asserts the (x, y, z) tuple was built and forwarded correctly, via the inline error
    # that failure produces, not that the whole flow succeeds end to end.
    assert not editor.error_label.isHidden()


def test_existing_slot_with_xyz_focus_prefills_the_xyz_fields(qtbot, patch_config):
    """A lightweight stand-in slot, not one built via add_slot(): the xyz focus option needs an
    active calibration combo to actually go through the public API, unrelated to what
    _load_existing_slot() itself needs here (it only reads chosen_focus/chosen_focus_value
    directly, never calls _set_focus_xyz())."""
    editor = _build_editor_with_xyz_focus_option(patch_config, tran_b_can_3d_steer=True)
    qtbot.addWidget(editor)
    tran_b = editor.transducer_combo.itemData(2)
    stand_in_slot = SimpleNamespace(
        transducer=tran_b, chosen_focus='Focus xyz wrt exit plane [mm]',
        chosen_focus_value=(1.0, 2.0, 30.0), chosen_power='Max. pressure in free water [MPa]',
        chosen_power_value=0.5, oper_freq=300, dephasing_degree=None)

    editor._load_existing_slot(stand_in_slot)

    assert editor.focus_value_x_spin.value() == pytest.approx(1.0)
    assert editor.focus_value_y_spin.value() == pytest.approx(2.0)
    assert editor.focus_value_z_spin.value() == pytest.approx(30.0)


def test_dephasing_section_hidden_for_a_sonic_concepts_backed_builder(qtbot, patch_config):
    """sonic_concepts_ds.py never reads TransducerSlot.dephasing_degree at all (see
    ProtocolBuilder.supports_dephasing()'s own docstring), so configuring it would silently do
    nothing on this driving system; the whole section is hidden rather than let a researcher
    configure a no-op."""
    _configure_driving_system(patch_config, 'UNITTEST_SC')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Manufacturer', 'Sonic Concepts')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Power options',
                     'Global power [mW]')
    patch_config.set('Equipment.Driving system.UNITTEST_SC', 'Native power parameters',
                     'Global power [mW]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')
    editor = SlotEditor(ProtocolBuilder(ds))
    qtbot.addWidget(editor)

    assert editor._form.isRowVisible(editor.dephasing_mode_combo) is False
    assert editor._form.isRowVisible(editor.dephasing_degree_spin) is False
    assert editor._form.isRowVisible(editor.dephasing_values_edit) is False
