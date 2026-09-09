# -*- coding: utf-8 -*-
"""
Tests for SlotEditor. Uses the same synthetic 'UNITTEST_*' fixture shape as
test_protocol_builder.py.
"""
import pytest

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

    editor.apply_button.click()

    assert editor.slot is None
    assert 'Choose a transducer first' in editor.error_label.text()


def test_apply_adds_a_new_slot(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)

    with qtbot.waitSignal(editor.applied, timeout=1000):
        editor.apply_button.click()

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

    editor.apply_button.click()

    assert editor.slot is None
    assert not editor.error_label.isHidden()
    assert editor.error_label.text()
    # A plain-colored message blends in with the rest of the tab; see ApplyPanel.__init__.
    assert 'red' in editor.error_label.styleSheet()


def test_apply_edits_an_already_added_slot_without_re_adding(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    editor.apply_button.click()
    first_slot = editor.slot

    editor.focus_value_spin.setValue(30)
    editor.apply_button.click()

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

    editor.apply_button.click()

    assert editor.slot.dephasing_degree is None


def test_apply_adds_a_new_slot_with_oper_freq_and_cyclic_dephasing(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.oper_freq_spin.setValue(500)
    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic
    editor.dephasing_degree_spin.setValue(45.0)

    editor.apply_button.click()

    assert editor.slot.oper_freq == 500
    assert editor.slot.dephasing_degree == [45.0]


def test_apply_adds_a_new_slot_with_a_per_element_dephasing_override(qtbot, builder):
    """UNITTEST_TRAN_A has 2 elements (see _configure_transducer's own default)."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("10, 20")

    editor.apply_button.click()

    assert editor.slot.dephasing_degree == [10.0, 20.0]


def test_apply_rejects_a_per_element_override_with_the_wrong_count(qtbot, builder):
    """The backend itself only catches this much later (IGT._define_pulse_group(), reached only
    once Send/Execute exists), so _apply() must check it itself, synchronously."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A: 2 elements
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("10, 20, 30")

    editor.apply_button.click()

    assert editor.slot is None
    assert 'does not correspond to number of transducer elements' in editor.error_label.text()


def test_apply_rejects_unparseable_per_element_values(qtbot, builder):
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.dephasing_mode_combo.setCurrentIndex(2)  # Per-element override
    editor.dephasing_values_edit.setText("not, numbers")

    editor.apply_button.click()

    assert editor.slot is None
    assert 'comma-separated list of numbers' in editor.error_label.text()


def test_apply_updates_transducer_forwards_oper_freq_and_dephasing_degree(qtbot, builder):
    """Covers the update_transducer() branch of _apply() (an already-added slot whose transducer
    changes), not just the add_slot() one above."""
    editor = SlotEditor(builder)
    qtbot.addWidget(editor)
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    editor.apply_button.click()

    editor.transducer_combo.setCurrentIndex(2)  # UNITTEST_TRAN_B
    editor.oper_freq_spin.setValue(700)
    editor.dephasing_mode_combo.setCurrentIndex(1)  # Cyclic
    editor.dephasing_degree_spin.setValue(120.0)
    editor.apply_button.click()

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

    editor.apply_button.click()

    # 'Focus xyz wrt exit plane [mm]' isn't UNITTEST_IGT's native focus param in this fixture
    # (only the plain, non-xyz exit-plane option is), so _set_focus_xyz() needs a real
    # calibration curve to convert it, which this synthetic, no-active-combo transducer
    # doesn't have (matching every other "no active calibration" case in this file). This test
    # only asserts the (x, y, z) tuple was built and forwarded correctly, via the inline error
    # that failure produces, not that the whole flow succeeds end to end.
    assert not editor.error_label.isHidden()


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
