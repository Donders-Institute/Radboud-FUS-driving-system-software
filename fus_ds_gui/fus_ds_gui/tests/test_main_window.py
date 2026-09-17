# -*- coding: utf-8 -*-
"""Smoke tests for MainWindow: launches with exactly the two documented tabs, plus its own File
menu (Load/Save/Approve). Every QFileDialog call is monkeypatched to return a controlled path
directly, rather than actually shown: a real modal dialog would block the test suite waiting
for a pick that never comes."""
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from fus_ds_gui.executing.executing_tab import ExecutingTab
from fus_ds_gui.main_window import MainWindow
from fus_ds_gui.models import protocol_io
from fus_ds_gui.planning.planning_tab import PlanningTab


def _configure_driving_system(patch_config, serial='UNITTEST_IGT'):
    # Sonic Concepts, not IGT: IGT.validate_protocol() also requires slot.ampl to be set, which
    # is only ever derived from a *real*, active calibration combo (a genuine hardware fact:
    # IGT's native power parameter is always amplitude, whatever power option was chosen), not
    # something these no-active-combo synthetic fixtures can produce. SC's own
    # validate_protocol() only requires global_power, so a clean (no-problems) protocol, and
    # therefore a save-able one, is reachable here without needing real calibration curve files
    # (see test_protocol_builder.py/test_planning_tab.py for the same reasoning).
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', 'Test Sonic Concepts')
    patch_config.set(section, 'Manufacturer', 'Sonic Concepts')
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Global power [mW]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Global power [mW]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')


def _select_first_driving_system(window):
    """PlanningTab starts on EquipmentPanel's own 'no driving system selected' placeholder (see
    EquipmentPanel.reload_driving_systems()'s own docstring), not auto-picking the first
    configured one; most tests below need a real one actually selected first."""
    window.planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(1)


def _build_protocol_file(tmp_path, patch_config):
    from fus_driving_systems.tus_protocol import TUSProtocol

    _configure_driving_system(patch_config)
    protocol = TUSProtocol('UNITTEST_IGT')
    protocol.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 40,
                      'Global power [mW]', 0.5)
    path = str(tmp_path / 'protocol.yaml')
    protocol_io.save(protocol, path)
    return path


def test_launches_with_planning_and_executing_tabs(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    tabs = window.centralWidget()

    assert tabs.count() == 2
    assert tabs.tabText(0) == "Planning"
    assert tabs.tabText(1) == "Executing"
    assert isinstance(tabs.widget(0), PlanningTab)
    assert isinstance(tabs.widget(1), ExecutingTab)


def test_approve_action_disabled_until_a_file_is_known(qtbot, patch_config):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window._approve_action.isEnabled() is False


def test_load_action_populates_the_planning_tab(qtbot, tmp_path, patch_config, monkeypatch):
    path = _build_protocol_file(tmp_path, patch_config)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: (path, '')))
    window = MainWindow()
    qtbot.addWidget(window)

    window._load_action.trigger()

    protocol = window.planning_tab.current_protocol()
    assert protocol.driving_sys.serial == 'UNITTEST_IGT'
    assert len(protocol.slots) == 1
    assert window._approve_action.isEnabled() is True


def test_load_action_does_nothing_when_the_dialog_is_cancelled(qtbot, patch_config, monkeypatch):
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: ('', '')))
    window = MainWindow()
    qtbot.addWidget(window)

    window._load_action.trigger()  # must not raise

    assert window._approve_action.isEnabled() is False


def test_load_action_shows_an_error_dialog_on_a_malformed_file(qtbot, tmp_path, patch_config,
                                                               monkeypatch):
    bad_path = tmp_path / 'bad.yaml'
    bad_path.write_text('not: [valid, protocol, structure', encoding='utf-8')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: (str(bad_path), '')))
    shown = []
    monkeypatch.setattr('fus_ds_gui.main_window.show_fds_error',
                        lambda parent, exc: shown.append(exc))
    window = MainWindow()
    qtbot.addWidget(window)

    window._load_action.trigger()

    assert len(shown) == 1
    assert window._approve_action.isEnabled() is False  # unchanged, load never succeeded


def test_load_action_recovers_a_slot_exceeding_the_safety_limit_without_a_dialog(
        qtbot, tmp_path, patch_config, monkeypatch):
    """The main scenario protocol_io.load()/PlanningTab.load_protocol() were built for: a slot
    whose own power value exceeds the configured safety limit still loads the rest of the file,
    with that one slot's own SlotEditor pre-filled and its failure shown inline, rather than
    blocking the whole load behind a modal dialog. IGT specifically, not this file's own
    Sonic-Concepts-flavored _configure_driving_system(): the safety limit being exercised here
    (get_max_pressure()) only applies to IGT's own 'Max. pressure in free water [MPa]', which
    Sonic Concepts doesn't even offer as a power option."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT')
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')
    path = tmp_path / 'protocol.yaml'
    path.write_text("""
driving_sys_serial: UNITTEST_IGT
protocols:
  - slots:
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 40
        power_option: Max. pressure in free water [MPa]
        power_value: 2
    timing:
      pulse_dur: 10
""", encoding='utf-8')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: (str(path), '')))
    shown = []
    monkeypatch.setattr('fus_ds_gui.main_window.show_fds_error',
                        lambda parent, exc: shown.append(exc))
    window = MainWindow()
    qtbot.addWidget(window)

    window._load_action.trigger()

    assert shown == []
    editor = window.planning_tab._slot_editors[0]
    assert editor.slot is None
    assert editor.power_value_spin.value() == pytest.approx(2)
    assert not editor.error_label.isHidden()
    # Approve hashes exactly this file on disk; it must stay disabled while that file is known
    # to contain a slot that failed to construct.
    assert window._approve_action.isEnabled() is False


def test_load_action_defaults_to_the_example_protocols_directory(
        qtbot, patch_config, monkeypatch):
    """Defaults to example_protocols/ (the shipped examples) so a researcher can still
    navigate elsewhere from there for a real one."""
    from fus_ds_gui.main_window import _EXAMPLE_PROTOCOLS_DIR

    seen_start_dirs = []

    def fake_dialog(self, title, start_dir, file_filter):
        seen_start_dirs.append(start_dir)
        return '', ''

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', staticmethod(fake_dialog))
    window = MainWindow()
    qtbot.addWidget(window)

    window._load_action.trigger()

    assert seen_start_dirs == [str(_EXAMPLE_PROTOCOLS_DIR)]


def test_save_action_does_nothing_when_the_dialog_is_cancelled(qtbot, patch_config, monkeypatch):
    _configure_driving_system(patch_config)
    window = MainWindow()
    qtbot.addWidget(window)
    _select_first_driving_system(window)
    editor = window.planning_tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN
    editor.try_apply()
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        staticmethod(lambda *args, **kwargs: ('', '')))

    window._save_action.trigger()  # must not raise

    assert window._approve_action.isEnabled() is False


def test_save_action_shows_an_error_dialog_on_failure(qtbot, tmp_path, patch_config, monkeypatch):
    """A nonexistent parent directory makes protocol_loader.save_protocol()'s own file write
    raise FDSValidationError (see its own docstring)."""
    _configure_driving_system(patch_config)
    window = MainWindow()
    qtbot.addWidget(window)
    _select_first_driving_system(window)
    editor = window.planning_tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN
    editor.try_apply()
    save_path = str(tmp_path / 'nested' / 'does' / 'not' / 'exist' / 'saved.yaml')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        staticmethod(lambda *args, **kwargs: (save_path, '')))
    shown = []
    monkeypatch.setattr('fus_ds_gui.main_window.show_fds_error',
                        lambda parent, exc: shown.append(exc))

    window._save_action.trigger()

    assert len(shown) == 1
    assert window._approve_action.isEnabled() is False


def test_approve_action_shows_an_error_dialog_on_failure(
        qtbot, tmp_path, patch_config, monkeypatch):
    path = _build_protocol_file(tmp_path, patch_config)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: (path, '')))
    window = MainWindow()
    qtbot.addWidget(window)
    window._load_action.trigger()
    # The approved file gets removed from under it, so approve_protocol() itself now fails to
    # read it back.
    (tmp_path / 'protocol.yaml').unlink()
    shown = []
    monkeypatch.setattr('fus_ds_gui.main_window.show_fds_error',
                        lambda parent, exc: shown.append(exc))

    window._approve_action.trigger()

    assert len(shown) == 1


def test_save_action_writes_the_current_protocol(qtbot, tmp_path, patch_config, monkeypatch):
    _configure_driving_system(patch_config)
    window = MainWindow()
    qtbot.addWidget(window)
    _select_first_driving_system(window)
    editor = window.planning_tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN
    editor.try_apply()
    save_path = str(tmp_path / 'saved.yaml')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        staticmethod(lambda *args, **kwargs: (save_path, '')))

    window._save_action.trigger()

    reloaded = protocol_io.load(save_path)
    assert reloaded.protocol.driving_sys.serial == 'UNITTEST_IGT'
    assert window._approve_action.isEnabled() is True


def test_save_action_disabled_when_nothing_to_save(qtbot, patch_config):
    """No slot applied yet: protocol.slots is empty, matching PlanningTab.can_save()'s own
    guard (mirroring save_protocol()'s own guard against writing an unloadable file, see its
    docstring). The Save action is disabled outright, rather than only caught after a click."""
    _configure_driving_system(patch_config)
    window = MainWindow()
    qtbot.addWidget(window)

    assert window._save_action.isEnabled() is False


def test_save_action_disabled_while_validation_has_problems(qtbot, patch_config):
    """A protocol failing its own validation (e.g. IGT's "Amplitude is None" check, unreachable
    here since no calibration combo exists) must not be save-able either, same reasoning as the
    empty-protocol case above: see PlanningTab.can_save()'s own docstring."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT')
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')
    window = MainWindow()
    qtbot.addWidget(window)
    _select_first_driving_system(window)
    editor = window.planning_tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)  # UNITTEST_TRAN

    editor.try_apply()

    assert window.planning_tab.builder.validate()  # sanity check: genuinely still invalid
    assert window._save_action.isEnabled() is False


def test_on_save_protocol_warns_if_called_despite_being_disabled(
        qtbot, patch_config, monkeypatch):
    """Defends _on_save_protocol() itself, not just the disabled action around it, in case
    something ever forces a trigger despite the UI (see its own comment)."""
    _configure_driving_system(patch_config)
    window = MainWindow()
    qtbot.addWidget(window)
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(lambda *args: warnings.append(args)))

    window._on_save_protocol()

    assert len(warnings) == 1


def test_approve_action_writes_a_hash_sidecar(qtbot, tmp_path, patch_config, monkeypatch):
    path = _build_protocol_file(tmp_path, patch_config)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *args, **kwargs: (path, '')))
    monkeypatch.setattr(QMessageBox, 'information', staticmethod(lambda *args: None))
    window = MainWindow()
    qtbot.addWidget(window)
    window._load_action.trigger()

    window._approve_action.trigger()

    assert (tmp_path / 'protocol.yaml.sha256').exists()
