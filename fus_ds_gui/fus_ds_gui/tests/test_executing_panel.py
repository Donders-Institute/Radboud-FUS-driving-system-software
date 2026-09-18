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
from fus_ds_gui.executing.trigger_panel import WHOLE_PROTOCOL
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


def test_on_sent_shows_a_plain_confirmation_and_enables_execute(qtbot, planning_tab_igt):
    """Deliberately just a plain confirmation, not the protocol's own field values: see
    ExecutionPanel's own docstring for why those belong to the console log instead (the driving
    system's own send_protocol()/execute_protocol() already log them there)."""
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._sent_protocol = planning_tab_igt.current_protocol()

    panel._on_sent()

    assert panel.execution_panel.sent_protocol_label.text() == (
        "Protocol sent. See the console below for details.")
    assert panel.execution_panel.execute_button.isEnabled() is True


def test_on_sent_disables_send_until_something_changes(qtbot, planning_tab_sc):
    """Nothing changed since this exact send, so Send staying enabled would just invite
    resending the same, unmodified protocol again for no reason."""
    _select_first_driving_system(planning_tab_sc)
    _apply_a_valid_slot(planning_tab_sc)
    panel = ExecutingPanel(planning_tab_sc)
    qtbot.addWidget(panel)
    panel._worker = MagicMock()
    panel._on_connected(True)
    assert panel.execution_panel.send_button.isEnabled() is True  # sanity check
    panel._sent_protocol = planning_tab_sc.current_protocol()

    panel._on_sent()

    assert panel.execution_panel.send_button.isEnabled() is False

    planning_tab_sc._slot_editors[0].power_value_spin.setValue(0.6)  # unlocks
    _apply_a_valid_slot(planning_tab_sc)  # re-applying re-locks

    assert panel.execution_panel.send_button.isEnabled() is True


def test_editing_after_send_disables_execute_again(qtbot, planning_tab_sc):
    """PlanningTab.builder.protocol is mutated in place on every Apply, never replaced, so
    self._sent_protocol (the same object) would otherwise keep reflecting whatever was edited
    and re-applied after it was actually sent, with Execute still wrongly enabled from that
    earlier send (see ExecutingPanel._invalidate_sent_protocol()'s own docstring). Needs a real
    is_locked() transition (not just directly calling _on_sent()), so planning_tab_sc, not
    planning_tab_igt: only Apply against a Sonic-Concepts-manufactured config can actually lock,
    see that fixture's own docstring."""
    _select_first_driving_system(planning_tab_sc)
    _apply_a_valid_slot(planning_tab_sc)
    assert planning_tab_sc.is_locked() is True  # sanity check
    panel = ExecutingPanel(planning_tab_sc)
    qtbot.addWidget(panel)
    panel._sent_protocol = planning_tab_sc.current_protocol()
    panel._on_sent()
    assert panel.execution_panel.execute_button.isEnabled() is True  # sanity check

    planning_tab_sc._slot_editors[0].power_value_spin.setValue(0.6)

    assert panel._sent_protocol is None
    assert panel.execution_panel.execute_button.isEnabled() is False
    assert panel.execution_panel.sent_protocol_label.text() == (
        "Protocol changed since it was sent. Send it again before executing.")


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

    assert panel.execution_panel.countdown_label.text() == "Execution complete."
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

    assert panel.execution_panel.countdown_label.text() == "Execution complete."
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

    assert panel.execution_panel.countdown_label.text() == "Execution complete."
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


def test_worker_error_is_suppressed_when_it_follows_a_successful_abort(
        qtbot, planning_tab_igt, monkeypatch):
    """A successful abort makes the blocked call it interrupted raise too, once it unwinds,
    already reflected by _on_aborted(), so this must not also pop a confusing second dialog and
    tear the connection down."""
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._worker = MagicMock()
    panel._thread = MagicMock()
    shown = []
    monkeypatch.setattr('fus_ds_gui.executing.executing_panel.show_fds_error',
                        lambda parent, exc: shown.append(exc))
    panel._on_abort_clicked()

    panel._on_worker_error(FDSHardwareError("aborted before completion"))

    assert shown == []
    assert panel._worker is not None
    assert panel._abort_pending is False


def test_abort_pending_self_clears_after_the_grace_period(qtbot, planning_tab_igt, monkeypatch):
    """Sonic Concepts' own non-blocking calls never raise a follow-up error after a successful
    abort at all, so the suppression flag must not stay stuck forever, or a genuinely
    unrelated later error would be wrongly swallowed too."""
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._on_abort_clicked()
    panel._on_aborted()
    assert panel._abort_pending is True  # sanity check: still within the grace period

    qtbot.wait(1100)

    assert panel._abort_pending is False


def test_abort_command_itself_failing_is_never_suppressed(qtbot, planning_tab_igt, monkeypatch):
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel._worker = MagicMock()
    panel._thread = MagicMock()
    shown = []
    monkeypatch.setattr('fus_ds_gui.executing.executing_panel.show_fds_error',
                        lambda parent, exc: shown.append(exc))
    panel._on_abort_clicked()

    exc = FDSHardwareError("abort itself failed")
    panel._on_abort_command_failed(exc)

    assert shown == [exc]
    assert panel._worker is None


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


def test_switching_driving_system_while_connected_disconnects_the_stale_worker(
        qtbot, patch_config, monkeypatch):
    """Without this, switching equipment while still connected would leave the old worker
    connected underneath a Planning tab now showing a different driving system entirely.
    Applying and sending a new protocol for it would silently go through that stale connection
    instead (see ExecutingPanel._on_driving_system_changed()'s own docstring)."""
    _configure_igt(patch_config, 'UNITTEST_IGT')
    _configure_sonic_concepts(patch_config, 'UNITTEST_SC')
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT\nUNITTEST_SC')
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(1)  # UNITTEST_IGT
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    mock_ds = MagicMock(spec=IGT)
    mock_ds.is_connected.return_value = True
    monkeypatch.setattr(planning_tab.builder, 'create_control_instance', lambda: mock_ds)
    panel.connection_panel.connect_button.click()
    qtbot.waitUntil(
        lambda: panel.connection_panel.status_label.text() == "Connected", timeout=2000)

    planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(2)  # UNITTEST_SC

    qtbot.waitUntil(lambda: panel._worker is None, timeout=2000)
    assert panel.connection_panel.status_label.text() == "Not connected"
    assert panel.connection_panel.connect_button.isEnabled() is True


def test_switching_driving_system_resets_the_sent_protocol_status(qtbot, patch_config):
    """A protocol sent for a previously selected driving system belongs to that driving
    system, not the newly chosen one; leaving it shown (and Execute enabled for it) would be
    just as misleading as the stale worker above."""
    _configure_igt(patch_config, 'UNITTEST_IGT')
    _configure_sonic_concepts(patch_config, 'UNITTEST_SC')
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT\nUNITTEST_SC')
    planning_tab = PlanningTab()
    qtbot.addWidget(planning_tab)
    planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(1)  # UNITTEST_IGT
    panel = ExecutingPanel(planning_tab)
    qtbot.addWidget(panel)
    panel._sent_protocol = planning_tab.current_protocol()
    panel._on_sent()
    assert panel.execution_panel.execute_button.isEnabled() is True  # sanity check

    planning_tab.equipment_panel._driving_system_combo.setCurrentIndex(2)  # UNITTEST_SC

    assert panel._sent_protocol is None
    assert panel.execution_panel.sent_protocol_label.text() == "Nothing sent yet."
    assert panel.execution_panel.execute_button.isEnabled() is False


def test_execute_button_relabels_to_arm_when_trigger_checked(qtbot, planning_tab_igt):
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    assert panel.execution_panel.execute_button.text() == "Execute"  # sanity check

    panel.trigger_panel.use_trigger_checkbox.setChecked(True)

    assert panel.execution_panel.execute_button.text() == "Arm"


def test_trigger_mode_controls_shown_only_for_igt(qtbot, planning_tab_igt, patch_config):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.show()
    assert panel.trigger_panel.trigger_mode_combo.isVisible() is True

    _configure_sonic_concepts(patch_config)
    sc_tab = PlanningTab()
    qtbot.addWidget(sc_tab)
    _select_first_driving_system(sc_tab)
    sc_panel = ExecutingPanel(sc_tab)
    qtbot.addWidget(sc_panel)
    sc_panel.show()

    assert sc_panel.trigger_panel.trigger_mode_combo.isVisible() is False


def test_execute_clicked_while_triggered_arms_instead_of_executing(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    planning_tab_igt.builder.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.show()
    panel.trigger_panel.use_trigger_checkbox.setChecked(True)
    panel._sent_protocol = planning_tab_igt.current_protocol()
    armed = []
    panel._arm_requested.connect(lambda *a: armed.append(a))

    panel._on_execute_clicked()

    assert armed == [(panel._sent_protocol, WHOLE_PROTOCOL, None)]
    assert panel.trigger_panel.waiting_label.isVisible() is True
    assert panel.execution_panel.execute_button.isEnabled() is False
    assert panel.execution_panel.abort_button.isEnabled() is True


def test_armed_updates_the_waiting_label(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.trigger_panel.use_trigger_checkbox.setChecked(True)
    panel._sent_protocol = planning_tab_igt.current_protocol()
    panel._on_execute_clicked()

    panel._on_armed()

    assert "Waiting for external trigger" in panel.trigger_panel.waiting_label.text()


def test_executed_after_triggered_igt_run_finishes_via_waiting_label(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.trigger_panel.use_trigger_checkbox.setChecked(True)
    panel._sent_protocol = planning_tab_igt.current_protocol()
    panel._on_execute_clicked()
    panel._on_armed()

    panel._on_executed()

    assert panel.trigger_panel.waiting_label.text() == "Triggered protocol executed successfully."
    assert panel.execution_panel.execute_button.isEnabled() is True
    assert panel.execution_panel.abort_button.isEnabled() is False


def test_abort_clicked_emits_abort_requested(qtbot, planning_tab_igt):
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    requested = []
    panel._abort_requested.connect(lambda: requested.append(True))

    panel._on_abort_clicked()

    assert requested == [True]


def test_on_aborted_resets_ui_but_keeps_sent_protocol(qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.show()
    panel.trigger_panel.use_trigger_checkbox.setChecked(True)  # avoids needing timing configured
    panel._sent_protocol = planning_tab_igt.current_protocol()
    panel._on_execute_clicked()

    panel._on_aborted()

    assert panel._sent_protocol is not None
    assert panel.execution_panel.execute_button.isEnabled() is True
    assert panel.execution_panel.abort_button.isEnabled() is False
    # The triggered run's own label shows "Aborted." and stays visible, same reasoning as
    # _finish_execution(): a label that just disappears looks identical to one still running.
    assert panel.trigger_panel.waiting_label.isVisible() is True
    assert panel.trigger_panel.waiting_label.text() == "Aborted."
    assert panel.execution_panel.countdown_label.isVisible() is False


def test_on_aborted_shows_aborted_on_the_countdown_label_for_a_plain_execute(
        qtbot, planning_tab_igt):
    _select_first_driving_system(planning_tab_igt)
    _apply_a_valid_slot(planning_tab_igt)
    planning_tab_igt.builder.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    panel.show()
    panel._sent_protocol = planning_tab_igt.current_protocol()
    panel._on_execute_clicked()  # trigger checkbox left unchecked

    panel._on_aborted()

    assert panel.execution_panel.countdown_label.isVisible() is True
    assert panel.execution_panel.countdown_label.text() == "Aborted."
    assert panel.trigger_panel.waiting_label.isVisible() is False


def test_connect_creates_a_second_abort_worker_and_thread(qtbot, planning_tab_igt, monkeypatch):
    _select_first_driving_system(planning_tab_igt)
    panel = ExecutingPanel(planning_tab_igt)
    qtbot.addWidget(panel)
    mock_ds = MagicMock(spec=IGT)
    mock_ds.is_connected.return_value = True
    monkeypatch.setattr(planning_tab_igt.builder, 'create_control_instance', lambda: mock_ds)

    panel.connection_panel.connect_button.click()
    qtbot.waitUntil(
        lambda: panel.connection_panel.status_label.text() == "Connected", timeout=2000)

    assert panel._abort_worker is not None
    assert panel._abort_thread is not None
    assert panel._abort_worker is not panel._worker
    assert panel._abort_thread is not panel._thread
    assert panel._abort_worker.ds_instance is mock_ds

    panel.connection_panel.disconnect_button.click()
    qtbot.waitUntil(lambda: panel._abort_worker is None, timeout=2000)
