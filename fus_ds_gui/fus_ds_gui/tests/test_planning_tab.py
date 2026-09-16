# -*- coding: utf-8 -*-
"""
Integration tests for PlanningTab: wiring between EquipmentPanel, SlotEditor(s), TimingPanel,
and the validation label. Not re-testing what each widget's own test module already covers in
isolation.
"""
import pytest
from PySide6.QtWidgets import QApplication

from fus_ds_gui.models.protocol_io import LoadResult
from fus_ds_gui.planning.planning_tab import PlanningTab


def _configure_driving_system(patch_config, serial, max_tran_slots=1, manufacturer='Sonic '
                              'Concepts', power_option='Global power [mW]'):
    # Sonic Concepts by default, not IGT: IGT.validate_protocol() also requires slot.ampl to be
    # set, which is only ever derived from a *real*, active calibration combo (a genuine
    # hardware fact: IGT's native power parameter is always amplitude, whatever power option
    # was chosen), not something these no-active-combo synthetic fixtures can produce. SC's own
    # validate_protocol() only requires global_power, so "no problems found" is reachable here
    # without needing real calibration curve files (see test_protocol_builder.py for the same
    # reasoning).
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', f'Test {manufacturer}')
    patch_config.set(section, 'Manufacturer', manufacturer)
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', power_option)
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', power_option)
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', str(max_tran_slots))
    patch_config.set(section, 'Active?', 'True')


def _configure_transducer(patch_config, serial='UNITTEST_TRAN'):
    section = f'Equipment.Transducer.{serial}'
    patch_config.set(section, 'Elements', '2')
    patch_config.set(section, 'Fund. freq.', '300')
    patch_config.set(section, 'Min. focus', '10')
    patch_config.set(section, 'Max. focus', '80')
    patch_config.set(section, 'Exit plane - first element dist.', '5')
    patch_config.set(section, 'Steer information', '')
    patch_config.set(section, 'Active?', 'True')


def _transducer_serials(combo):
    """Item 0 is always the 'no transducer selected' placeholder (itemData None, see
    SlotEditor._populate_transducer_combo()'s own docstring); every real item has a Transducer
    with its own .serial."""
    return [combo.itemData(i).serial if combo.itemData(i) is not None else None
            for i in range(combo.count())]


def _select_first_driving_system(tab):
    """PlanningTab starts on EquipmentPanel's own 'no driving system selected' placeholder (see
    EquipmentPanel.reload_driving_systems()'s own docstring), not auto-picking the first
    configured one; most tests below need a real one actually selected first."""
    tab.equipment_panel._driving_system_combo.setCurrentIndex(1)


@pytest.fixture
def single_slot_setup(patch_config):
    """One driving system with max_tran_slots=1 and one compatible transducer, so the "Add
    transducer slot" button must never become enabled."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=1)
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)


def test_starts_with_no_driving_system_selected(qtbot, single_slot_setup):
    """A researcher must deliberately choose a driving system, never build a protocol for
    whichever one happens to be listed first in ds_config.ini without having picked it
    themselves (see EquipmentPanel.reload_driving_systems()'s own docstring)."""
    tab = PlanningTab()
    qtbot.addWidget(tab)

    assert tab.builder is None
    assert tab._slot_editors == []
    assert tab.timing_panel is None
    assert tab.add_slot_button.isEnabled() is False
    assert tab.validation_label.text() == "Select a driving system above to begin."


def test_validation_label_shows_placeholder_before_any_slot(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    assert tab.validation_label.text() == (
        "Configure a transducer slot below and click its Apply button to begin.")
    assert tab.validation_label.styleSheet() == ""


def test_validation_label_reports_a_timing_error_before_any_slot_is_applied(
        qtbot, single_slot_setup):
    """A researcher must see a timing problem right away, without first needing to apply a
    transducer slot just to unlock validation at all (see ProtocolBuilder.validate()'s own
    docstring)."""
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    tab.builder.configure_timing(pulse_dur=10, pulse_rep_int=5)
    tab._refresh_validation()

    assert 'Pulse Duration' in tab.validation_label.text()
    assert 'red' in tab.validation_label.styleSheet()


def test_builds_one_slot_editor_and_timing_panel_on_startup(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    assert len(tab._slot_editors) == 1
    assert tab.timing_panel is not None
    assert tab.builder is not None


def test_add_slot_button_disabled_at_max_tran_slots(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    assert tab.add_slot_button.isEnabled() is False


def test_add_slot_button_enabled_when_room_for_more(qtbot, patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2)
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)

    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    assert tab.add_slot_button.isEnabled() is True

    tab.add_slot_button.click()

    assert len(tab._slot_editors) == 2
    assert tab.add_slot_button.isEnabled() is False  # now at the limit


def test_choosing_a_transducer_excludes_it_from_other_slot_editors(qtbot, patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2)
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Transducer compatibility',
                     'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')

    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    tab.add_slot_button.click()
    editor_1, editor_2 = tab._slot_editors
    # Both editors start on the "no transducer selected" placeholder (see SlotEditor.
    # _populate_transducer_combo()'s own docstring), so an explicit pick is needed here to
    # trigger the exclusion in the first place.
    editor_1.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A

    assert _transducer_serials(editor_2.transducer_combo) == [None, 'UNITTEST_TRAN_B']

    # editor_1's own dropdown must still offer its own current pick.
    assert 'UNITTEST_TRAN_A' in _transducer_serials(editor_1.transducer_combo)


def test_switching_a_transducer_frees_it_up_for_other_slot_editors(qtbot, patch_config):
    """Three transducers, not two: with exactly as many transducers as slots, editor_1 can only
    ever switch to whatever editor_2 doesn't already have; there's nothing left to prove about
    "freeing up" a serial in that case (see the previous test's own comment). A third, still-
    unclaimed transducer isolates the actual behavior under test: switching editor_1 *away from*
    UNITTEST_TRAN_A makes that serial available to editor_2 again."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2)
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Transducer compatibility',
                     'UNITTEST_TRAN_A\nUNITTEST_TRAN_B\nUNITTEST_TRAN_C')
    patch_config.set('Equipment', 'Transducers',
                     'UNITTEST_TRAN_A\nUNITTEST_TRAN_B\nUNITTEST_TRAN_C')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_C')

    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    tab.add_slot_button.click()
    editor_1, editor_2 = tab._slot_editors
    editor_1.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN_A
    # UNITTEST_TRAN_A is now excluded from editor_2's own dropdown (see the previous test), so
    # look B up by serial rather than a fixed index.
    b_index = next(i for i in range(editor_2.transducer_combo.count())
                   if editor_2.transducer_combo.itemData(i) is not None
                   and editor_2.transducer_combo.itemData(i).serial == 'UNITTEST_TRAN_B')
    editor_2.transducer_combo.setCurrentIndex(b_index)
    assert editor_2.transducer_combo.currentData().serial != 'UNITTEST_TRAN_A'

    combo = editor_1.transducer_combo
    tran_c_index = next(i for i in range(combo.count())
                        if combo.itemData(i) is not None
                        and combo.itemData(i).serial == 'UNITTEST_TRAN_C')
    combo.setCurrentIndex(tran_c_index)

    assert 'UNITTEST_TRAN_A' in _transducer_serials(editor_2.transducer_combo)


def test_validation_label_updates_after_applying_a_slot(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    editor = tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)

    editor.apply_button.click()

    assert tab.validation_label.text() == "No problems found."
    assert tab.validation_label.styleSheet() == ""


def test_validation_label_turns_red_when_there_are_problems(
        qtbot, single_slot_setup, monkeypatch):
    """A plain-colored message blends in with the rest of the tab; see this label's own use
    alongside SlotEditor/TimingPanel's identically-styled error_label (ApplyPanel). Fakes
    validate() itself rather than constructing a real invalid protocol: this test is only about
    _refresh_validation()'s own styling logic, not about which backend rule actually fires, so a
    real slot/timing setup would only couple it to that rule's own wording/existence."""
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    monkeypatch.setattr(tab.builder, 'validate', lambda: ['Something is wrong.'])
    tab._refresh_validation()

    assert tab.validation_label.text() == "- Something is wrong."
    assert 'red' in tab.validation_label.styleSheet()


def test_validation_label_shows_a_neutral_hint_while_more_slots_are_still_needed(
        qtbot, patch_config, monkeypatch):
    """IGT's own channel-count-mismatch message is expected, not a real problem, for as long as
    a multi-slot driving system genuinely still has room for more: a researcher who just
    correctly applied slot 1 of 2 shouldn't see a red error about slot 2 not existing yet (see
    _refresh_validation()'s own comment)."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2, manufacturer='IGT',
                              power_option='Max. pressure in free water [MPa]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    editor = tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    editor.apply_button.click()
    monkeypatch.setattr(tab.builder, 'validate', lambda: [
        'Number of available channels (4) does not match the combined elements of the 1 '
        'transducer slot(s) (2). Configure the remaining transducer slot(s), or choose a '
        'driving system whose available channels match how many transducers you intend to use.'
    ])

    tab._refresh_validation()

    assert tab.validation_label.text() == (
        "Configure 1 more transducer slot(s) below and click Apply to continue.")
    assert tab.validation_label.styleSheet() == ""


def test_validation_label_still_shows_a_real_error_while_more_slots_are_needed(
        qtbot, patch_config, monkeypatch):
    """A genuine problem with a slot already applied (e.g. "Amplitude is None") must still show,
    even while the driving system still has room for more slots: only the channel-count-mismatch
    message itself is treated as expected in that case, not every other error too."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2, manufacturer='IGT',
                              power_option='Max. pressure in free water [MPa]')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    editor = tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    editor.apply_button.click()
    monkeypatch.setattr(tab.builder, 'validate', lambda: [
        'Number of available channels (4) does not match the combined elements of the 1 '
        'transducer slot(s) (2). Configure the remaining transducer slot(s), or choose a '
        'driving system whose available channels match how many transducers you intend to use.',
        'Amplitude is None.',
    ])

    tab._refresh_validation()

    assert tab.validation_label.text() == "- Amplitude is None."
    assert 'red' in tab.validation_label.styleSheet()


def test_changing_driving_system_rebuilds_slot_editors_and_timing_panel(qtbot, patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_A', max_tran_slots=1)
    _configure_driving_system(patch_config, 'UNITTEST_B', max_tran_slots=1)
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A\nUNITTEST_B')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)

    tab = PlanningTab()
    qtbot.addWidget(tab)
    first_builder = tab.builder
    first_timing_panel = tab.timing_panel

    tab.equipment_panel._driving_system_combo.setCurrentIndex(1)

    assert tab.builder is not first_builder
    assert tab.timing_panel is not first_timing_panel
    assert len(tab._slot_editors) == 1


def _build_protocol(driving_sys_serial, slot_defs, pulse_dur=5, **timing_kwargs):
    """One TUSProtocol built directly via the Python API (not through a YAML file), for
    load_protocol() tests below: PlanningTab.load_protocol() itself doesn't care where the
    protocol came from, only that it's already fully configured."""
    from fus_driving_systems.tus_protocol import TUSProtocol

    protocol = TUSProtocol(driving_sys_serial)
    for serial, focus_value, power_value in slot_defs:
        protocol.add_slot(serial, 'Focus wrt exit plane [mm]', focus_value,
                          'Global power [mW]', power_value)
    protocol.configure_timing(pulse_dur, **timing_kwargs)
    return protocol


def test_load_protocol_does_not_leave_the_previous_slot_editor_as_a_stray_window(
        qtbot, single_slot_setup):
    """_clear_slot_editors()/_clear_timing_panel() must never setParent(None) a widget that was
    already shown as part of a layout: Qt would then treat it as its own, still-visible
    top-level window (a stray, empty OS window that lingers even after the whole app is closed)
    instead of making it disappear -- see PlanningTab._clear_slot_editors()'s own comment on why
    removeWidget()+deleteLater() is used instead."""
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)
    original_editor = tab._slot_editors[0]
    original_timing_panel = tab.timing_panel
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)])

    tab.load_protocol(LoadResult(protocol, []))

    assert original_editor.parent() is tab
    assert original_editor not in QApplication.topLevelWidgets()
    assert original_timing_panel.parent() is tab
    assert original_timing_panel not in QApplication.topLevelWidgets()


def test_load_protocol_selects_the_matching_driving_system(qtbot, patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_A', max_tran_slots=1)
    _configure_driving_system(patch_config, 'UNITTEST_B', max_tran_slots=1)
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A\nUNITTEST_B')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_B', [('UNITTEST_TRAN', 40, 0.5)])

    tab.load_protocol(LoadResult(protocol, []))

    assert tab.equipment_panel.selected_driving_system().serial == 'UNITTEST_B'


def test_load_protocol_builds_one_slot_editor_per_existing_slot(qtbot, patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=2)
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Transducer compatibility',
                     'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN_A\nUNITTEST_TRAN_B')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_A')
    _configure_transducer(patch_config, 'UNITTEST_TRAN_B')
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT',
                               [('UNITTEST_TRAN_A', 40, 0.5), ('UNITTEST_TRAN_B', 60, 0.3)])

    tab.load_protocol(LoadResult(protocol, []))

    assert len(tab._slot_editors) == 2
    assert tab._slot_editors[0].slot.transducer.serial == 'UNITTEST_TRAN_A'
    assert tab._slot_editors[0].focus_value_spin.value() == pytest.approx(40)
    assert tab._slot_editors[1].slot.transducer.serial == 'UNITTEST_TRAN_B'
    assert tab._slot_editors[1].focus_value_spin.value() == pytest.approx(60)


def test_load_protocol_timing_panel_reflects_loaded_values(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)], pulse_dur=7)

    tab.load_protocol(LoadResult(protocol, []))

    assert tab.timing_panel.pulse_dur_spin.value() == pytest.approx(7)


def test_load_protocol_expands_timing_levels_set_explicitly_by_the_file(qtbot, single_slot_setup):
    """A loaded protocol whose own pulse train/pulse train repetition values were explicitly
    set (not just inherited from pulse_dur) must show those levels already expanded, not leave
    a researcher unaware they're even set."""
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)], pulse_dur=1,
                               pulse_rep_int=5, pulse_train_dur=20,
                               pulse_train_rep_int=40, pulse_train_rep_dur=2)

    tab.load_protocol(LoadResult(protocol, []))

    assert tab.timing_panel.pulse_train_level.is_expanded() is True
    assert tab.timing_panel.pulse_train_rep_level.is_expanded() is True


def test_load_protocol_refreshes_validation(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)])

    tab.load_protocol(LoadResult(protocol, []))

    assert tab.validation_label.text() == "No problems found."


def test_load_protocol_raises_when_driving_system_not_offered(qtbot, patch_config):
    """E.g. a CITRUS driving system, filtered out of the Planning tab's own equipment dropdown
    entirely; see EquipmentPanel.select_driving_system()'s own docstring."""
    from fus_driving_systems.exceptions import FDSConfigError

    _configure_driving_system(patch_config, 'UNITTEST_IGT', max_tran_slots=1)
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    _configure_transducer(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)])
    # Simulate a protocol built for a driving system this tab doesn't offer, by pointing its
    # own driving_sys at one absent from config entirely (rather than genuinely configuring and
    # then excluding a CITRUS one, which needs a real manufacturer round-trip).
    protocol.driving_sys.serial = 'UNITTEST_NOT_OFFERED'

    with pytest.raises(FDSConfigError, match='UNITTEST_NOT_OFFERED'):
        tab.load_protocol(LoadResult(protocol, []))


def test_load_protocol_builds_an_extra_editor_per_failed_slot(qtbot, single_slot_setup):
    """A slot that failed to load (see protocol_io.load()'s own failed_slots) still gets its
    own SlotEditor, pre-filled with the raw values and the failure shown inline, alongside one
    editor per slot that did load successfully."""
    from fus_driving_systems.exceptions import FDSSafetyError

    tab = PlanningTab()
    qtbot.addWidget(tab)
    protocol = _build_protocol('UNITTEST_IGT', [('UNITTEST_TRAN', 40, 0.5)])
    failed_slot_def = {
        'transducer_serial': 'UNITTEST_TRAN',
        'focus_option': 'Focus wrt exit plane [mm]',
        'focus_value': 60,
        'power_option': 'Global power [mW]',
        'power_value': 999,
    }
    load_result = LoadResult(protocol, [(failed_slot_def, FDSSafetyError('too high'))])

    tab.load_protocol(load_result)

    assert len(tab._slot_editors) == 2
    assert tab._slot_editors[0].slot is not None
    assert tab._slot_editors[1].slot is None
    assert not tab._slot_editors[1].error_label.isHidden()
    assert 'too high' in tab._slot_editors[1].error_label.text()


def test_current_protocol_returns_the_builder_protocol(qtbot, single_slot_setup):
    tab = PlanningTab()
    qtbot.addWidget(tab)
    _select_first_driving_system(tab)

    assert tab.current_protocol() is tab.builder.protocol


def test_current_protocol_returns_none_without_a_driving_system(qtbot, patch_config):
    patch_config.set('Equipment', 'Driving systems', '')

    tab = PlanningTab()
    qtbot.addWidget(tab)

    assert tab.current_protocol() is None
