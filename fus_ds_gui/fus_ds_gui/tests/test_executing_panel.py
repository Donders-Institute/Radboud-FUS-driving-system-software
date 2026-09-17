# -*- coding: utf-8 -*-
"""
Tests for ExecutingPanel. Most of these call its own _on_*() callback methods directly rather
than driving them through a real QThread round-trip (see test_connect_click_runs_the_real_worker
for the one test that does exercise the real thread, proving the wiring itself works): a real
worker thread is timing-sensitive and adds little for testing this panel's own state-management
logic, which is what these tests are actually about.
"""
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QMessageBox

from fus_driving_systems.exceptions import FDSHardwareError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts

from fus_ds_gui.executing.executing_panel import ExecutingPanel
from fus_ds_gui.planning.planning_tab import PlanningTab


def _configure_igt(patch_config, serial='UNITTEST_IGT'):
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
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
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')


def _configure_sonic_concepts(patch_config, serial='UNITTEST_SC'):
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


def _select_first_driving_system(planning_tab):
    planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(1)


def _apply_a_valid_slot(planning_tab):
    editor = planning_tab._slot_editors[0]
    editor.transducer_combo.setCurrentIndex(1)
    editor.focus_value_spin.setValue(20)
    editor.power_value_spin.setValue(0.5)
    planning_tab.apply_button.click()


@pytest.fixture
def planning_tab_igt(qtbot, patch_config):
    _configure_igt(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def planning_tab_sc(qtbot, patch_config):
    # Sonic Concepts, not IGT: IGT.validate_protocol() also requires slot.ampl, only ever
    # derived from a real, active calibration combo that these synthetic fixtures can't produce
    # (see test_planning_tab.py's own _configure_driving_system() for the same reasoning). Tests
    # that only care about the generic lock/connect/send wiring, not IGT-vs-SC specifics, use
    # this fixture so Apply can actually succeed.
    _configure_sonic_concepts(patch_config)
    tab = PlanningTab()
    qtbot.addWidget(tab)
    return tab


def test_connect_button_disabled_without_a_driving_system(qtbot, planning_tab_igt):
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)

    assert panel.connection_panel.connect_button.isEnabled() is False
    assert panel.connection_panel.driving_system_label.text() == "No driving system selected"


def test_connect_button_enabled_once_a_driving_system_is_chosen(qtbot, planning_tab_igt):
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)

    _select_first_driving_system(planning_tab_igt)

    assert panel.connection_panel.connect_button.isEnabled() is True
    assert "Test IGT" in panel.connection_panel.driving_system_label.text()


def test_send_disabled_until_both_connected_and_locked(qtbot, planning_tab_sc):
    _select_first_driving_system(planning_tab_sc)
    panel = ExecutingPanel(planning_tab_sc)
    qtbot.addWidget(panel)
    panel.show()
    panel.execution_panel.show()

    assert panel.execution_panel.send_button.isEnabled() is False
    assert panel.execution_panel.lock_hint_label.isVisible() is True

    _apply_a_valid_slot(planning_tab_sc)  # locked, but still not connected

    assert panel.execution_panel.send_button.isEnabled() is False
    assert panel.execution_panel.lock_hint_label.isVisible() is False

    panel._worker = MagicMock()  # simulate "connected" without a real worker/thread
    panel._on_connected(True)

    assert panel.execution_panel.send_button.isEnabled() is True


def test_a_later_edit_disables_send_again(qtbot, planning_tab_sc):
    """is_locked() itself already unlocks on any edit (see PlanningTab's own lock/unlock
    tests); this only confirms ExecutingPanel is actually listening for that."""
    _select_first_driving_system(planning_tab_sc)
    _apply_a_valid_slot(planning_tab_sc)
    panel = ExecutingPanel(planning_tab_sc)
    qtbot.addWidget(panel)
    panel.show()
    panel.execution_panel.show()
    panel._worker = MagicMock()
    panel._on_connected(True)
    assert panel.execution_panel.send_button.isEnabled() is True

    planning_tab_sc._slot_editors[0].power_value_spin.setValue(0.6)

    assert panel.execution_panel.send_button.isEnabled() is False
    assert panel.execution_panel.lock_hint_label.isVisible() is True


def test_on_sent_shows_the_sent_protocol_summary_and_enables_execute(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._sent_protocol = planning_tab_igt.current_protocol()

    panel._on_sent()

    assert panel.execution_panel.sent_protocol_label.text() == str(panel._sent_protocol)
    assert panel.execution_panel.execute_button.isEnabled() is True


def test_start_countdown_uses_pulse_train_rep_dur_for_igt(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    planning_tab_igt.builder.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)

    panel._start_countdown(planning_tab_igt.current_protocol())

    assert panel.execution_panel.countdown_label.text() == "Estimated time remaining: 5 s"


def test_start_countdown_uses_pulse_train_dur_for_sonic_concepts(qtbot, patch_config):
    _configure_sonic_concepts(patch_config)
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    _select_first_driving_system(planning_tab)
    _apply_a_valid_slot(planning_tab)
    planning_tab.builder.configure_timing(pulse_dur=1, pulse_train_dur=3000)
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)

    panel._start_countdown(planning_tab.current_protocol())

    assert panel.execution_panel.countdown_label.text() == "Estimated time remaining: 3 s"


def _start_execution(panel, planning_tab):
    """Mimics a real Send-then-Execute click without a real worker/thread: enables
    execute_button (_on_sent()'s job), then disables it again and starts the countdown
    (_on_execute_clicked()'s job). The realistic starting point for the tests below, rather
    than asserting against execute_button's already-disabled construction-time default."""
    panel._sent_protocol = planning_tab.current_protocol()
    panel._on_sent()
    panel._on_execute_clicked()


def test_on_executed_finishes_immediately_for_igt(qtbot, planning_tab_igt):
    """IGT's own execute_protocol() genuinely blocks until the sonication is done, so its
    executed() signal is authoritative."""
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    planning_tab_igt.builder.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    _start_execution(panel, planning_tab_igt)

    panel._on_executed()

    assert panel.execution_panel.countdown_label.isHidden() is True
    assert panel.execution_panel.execute_button.isEnabled() is True
    assert panel._countdown_timer.isActive() is False


def test_on_executed_is_a_noop_for_sonic_concepts(qtbot, patch_config):
    """Sonic Concepts' own execute_protocol() returns almost instantly, well before the
    sonication itself actually finishes, so its executed() signal must not end execution on
    its own; _on_countdown_tick() does that instead, once the estimate itself runs out."""
    _configure_sonic_concepts(patch_config)
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    _select_first_driving_system(planning_tab)
    _apply_a_valid_slot(planning_tab)
    planning_tab.builder.configure_timing(pulse_dur=1, pulse_train_dur=3000)
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    _start_execution(panel, planning_tab)

    panel._on_executed()

    assert panel.execution_panel.countdown_label.isHidden() is False
    assert panel.execution_panel.execute_button.isEnabled() is False


def test_countdown_reaching_zero_finishes_execution_for_sonic_concepts(qtbot, patch_config):
    _configure_sonic_concepts(patch_config)
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    _select_first_driving_system(planning_tab)
    _apply_a_valid_slot(planning_tab)
    planning_tab.builder.configure_timing(pulse_dur=1, pulse_train_dur=1000)  # 1s estimate
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    _start_execution(panel, planning_tab)

    panel._on_countdown_tick()  # reaches 0

    assert panel.execution_panel.countdown_label.isHidden() is True
    assert panel.execution_panel.execute_button.isEnabled() is True


def test_countdown_reaching_zero_does_not_finish_execution_for_igt(qtbot, planning_tab_igt):
    """See _on_countdown_tick()/_on_executed()'s own docstrings: IGT's own executed() signal,
    not this client-side estimate, is what actually ends execution."""
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    planning_tab_igt.builder.configure_timing(pulse_dur=1, pulse_train_rep_dur=1)  # 1s estimate
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    _start_execution(panel, planning_tab_igt)

    panel._on_countdown_tick()  # reaches 0

    assert panel.execution_panel.countdown_label.isHidden() is False
    assert panel.execution_panel.execute_button.isEnabled() is False
    assert panel._countdown_timer.isActive() is False

    panel._on_executed()

    assert panel.execution_panel.countdown_label.isHidden() is True
    assert panel.execution_panel.execute_button.isEnabled() is True


def test_worker_error_shows_a_dialog_and_resets_connection_state(
        qtbot, planning_tab_igt, monkeypatch):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._worker = MagicMock()
    panel._thread = MagicMock()
    shown = []
    monkeypatch.setattr('fus_ds_gui.executing.executing_panel.show_fds_error',
                        lambda parent, exc: shown.append(exc))

    exc = FDSHardwareError("connection lost")
    panel._on_worker_error(exc)

    assert shown == [exc]
    assert panel._worker is None
    assert panel.connection_panel.status_label.text() == "Not connected"


def test_sonic_concepts_confirmation_declined_disconnects_and_shows_a_safety_error(
        qtbot, patch_config, monkeypatch):
    _configure_sonic_concepts(patch_config)
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    _select_first_driving_system(planning_tab)
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    panel._worker = MagicMock(ds_instance=MagicMock(spec=SonicConcepts))
    panel._thread = MagicMock()
    monkeypatch.setattr(QMessageBox, 'question',
                        lambda *a, **kw: QMessageBox.StandardButton.Cancel)
    shown = []
    monkeypatch.setattr('fus_ds_gui.executing.executing_panel.show_fds_error',
                        lambda parent, exc: shown.append(exc))
    disconnect_requests = []
    panel._disconnect_requested.connect(lambda: disconnect_requests.append(True))

    panel._on_connected(True)

    assert len(shown) == 1
    assert 'not confirmed' in str(shown[0])
    assert disconnect_requests == [True]


def test_sonic_concepts_confirmation_accepted_proceeds_to_connected(
        qtbot, patch_config, monkeypatch):
    _configure_sonic_concepts(patch_config)
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    _select_first_driving_system(planning_tab)
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    panel._worker = MagicMock(ds_instance=MagicMock(spec=SonicConcepts))
    monkeypatch.setattr(QMessageBox, 'question',
                        lambda *a, **kw: QMessageBox.StandardButton.Ok)

    panel._on_connected(True)

    assert panel.connection_panel.status_label.text() == "Connected"


def test_connect_click_runs_the_real_worker(qtbot, planning_tab_igt, monkeypatch):
    """The one test exercising the real QThread/DrivingSystemWorker round-trip, to prove the
    wiring itself (not just this panel's own callback logic, covered above) is correct."""
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    mock_ds = MagicMock(spec=IGT)
    mock_ds.is_connected.return_value = True
    monkeypatch.setattr(planning_tab_igt.builder, 'create_control_instance', lambda: mock_ds)

    panel.connection_panel.connect_button.click()
    qtbot.waitUntil(
        lambda: panel.connection_panel.status_label.text() == "Connected", timeout=2000)

    mock_ds.connect.assert_called_once_with('COM1')

    panel.connection_panel.disconnect_button.click()
    qtbot.waitUntil(lambda: panel._worker is None, timeout=2000)
