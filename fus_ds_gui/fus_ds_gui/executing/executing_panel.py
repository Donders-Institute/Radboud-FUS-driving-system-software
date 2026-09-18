# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSSafetyError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.utils import get_config_value

from fus_ds_gui.error_dialogs import show_fds_error
from fus_ds_gui.executing.connection_panel import ConnectionPanel
from fus_ds_gui.executing.console_panel import ConsolePanel
from fus_ds_gui.executing.execution_panel import ExecutionPanel
from fus_ds_gui.executing.trigger_panel import TriggerPanel
from fus_ds_gui.workers.hardware_worker import DrivingSystemWorker

_COUNTDOWN_INTERVAL_MS = 1000

# How long a worker error is still attributed to an abort that just succeeded (see
# _on_worker_error()'s own docstring), rather than treated as a new, unrelated problem.
_ABORT_ERROR_GRACE_MS = 1000


class ExecutingPanel(QWidget):
    """
    Connects to real hardware and sends/executes the Planning tab's own current protocol.
    Always visible next to Planning (see MainWindow), not something you switch to: Send is only
    ever available while the Planning tab is locked (see PlanningTab.is_locked()'s own
    docstring), so what this panel would send always exactly matches what the Planning tab is
    currently showing.

    Two DrivingSystemWorker/QThread pairs are created per connection (see hardware_worker.py's
    own docstring): the main one for connect/send/execute/trigger, and a second, abort-only one,
    so Abort can reach the hardware even while the main one is stuck inside a blocking call. Both
    are torn down together on Disconnect or on a connection-level error.
    """

    _connect_requested = Signal(str)
    _disconnect_requested = Signal()
    _send_requested = Signal(object)
    _execute_requested = Signal(object)
    _arm_requested = Signal(object, object, object)
    _abort_requested = Signal()

    def __init__(self, planning_tab, parent=None):
        super().__init__(parent)

        self._planning_tab = planning_tab
        self._worker = None
        self._thread = None
        self._abort_worker = None
        self._abort_thread = None
        self._sent_protocol = None
        self._busy = False
        self._abort_pending = False
        self._triggered_run = False
        self._countdown_remaining_s = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._wait_elapsed_s = 0
        self._wait_timer = QTimer(self)
        self._wait_timer.timeout.connect(self._on_wait_tick)

        self.connection_panel = ConnectionPanel()
        self.connection_panel.connect_clicked.connect(self._on_connect_clicked)
        self.connection_panel.disconnect_clicked.connect(self._on_disconnect_clicked)

        self.execution_panel = ExecutionPanel()
        self.execution_panel.send_clicked.connect(self._on_send_clicked)
        self.execution_panel.execute_clicked.connect(self._on_execute_clicked)
        self.execution_panel.abort_clicked.connect(self._on_abort_clicked)

        self.trigger_panel = TriggerPanel()
        self.trigger_panel.settings_changed.connect(self._refresh_trigger_controls)

        self.console_panel = ConsolePanel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.connection_panel)
        layout.addWidget(self.execution_panel)
        layout.addWidget(self.trigger_panel)
        layout.addWidget(self.console_panel)
        layout.addStretch()

        planning_tab.lock_changed.connect(self._refresh_send_enabled)
        planning_tab.equipment_panel.driving_system_changed.connect(
            self._on_driving_system_changed)
        self._refresh_driving_system_label()
        self._refresh_send_enabled()
        self._refresh_trigger_controls()

    def _on_driving_system_changed(self):
        """Switching equipment while still connected would otherwise leave a stale worker
        connected to the driving system that's no longer selected: building and applying a new
        protocol for the newly chosen one, then clicking Send, would silently go through that
        old connection instead. Disconnects first (asynchronously, like clicking Disconnect
        would) if a connection is active; _on_disconnected() refreshes the label itself once
        that completes, so the immediate call below only matters while still connected. Also
        clears whatever was last sent, for the same reason: it belonged to the driving system
        that's no longer selected."""

        if self._worker is not None:
            self._on_disconnect_clicked()
        self._reset_sent_state()
        self._refresh_driving_system_label()
        self._refresh_trigger_controls()

    def _reset_sent_state(self):
        self._reset_execution_state()
        self._sent_protocol = None
        self.execution_panel.sent_protocol_label.setText("Nothing sent yet.")
        self.execution_panel.execute_button.setEnabled(False)

    def _reset_execution_state(self):
        self._countdown_timer.stop()
        self._wait_timer.stop()
        self._busy = False
        self._triggered_run = False
        self.execution_panel.countdown_label.setVisible(False)
        self.trigger_panel.waiting_label.setVisible(False)
        self.execution_panel.abort_button.setEnabled(False)

    def _refresh_trigger_controls(self):
        builder = self._planning_tab.builder
        supports_trigger_options = builder is not None and builder.supports_trigger_options()
        self.trigger_panel.trigger_mode_combo.setVisible(supports_trigger_options)
        self.trigger_panel.n_triggers_spin.setVisible(
            supports_trigger_options and self.trigger_panel.n_triggers() is not None)
        self.execution_panel.execute_button.setText(
            "Arm" if self.trigger_panel.use_trigger_checkbox.isChecked() else "Execute")

    def _refresh_driving_system_label(self):
        builder = self._planning_tab.builder
        if builder is None:
            self.connection_panel.driving_system_label.setText("No driving system selected")
            self.connection_panel.connect_button.setEnabled(False)
        else:
            self.connection_panel.driving_system_label.setText(
                f"Driving system: {builder.driving_system.name}")
            self.connection_panel.connect_button.setEnabled(self._worker is None)

    def _refresh_send_enabled(self):
        locked = self._planning_tab.is_locked()
        self.execution_panel.lock_hint_label.setVisible(not locked)
        self.execution_panel.send_button.setEnabled(locked and self._worker is not None)
        if not locked:
            self._invalidate_sent_protocol()

    def _invalidate_sent_protocol(self):
        """PlanningTab.builder.protocol is mutated in place on every Apply, never replaced (see
        its own docstring), so self._sent_protocol, the same object, would otherwise keep
        reflecting whatever was edited and re-applied after it was actually sent, with Execute
        still enabled from that earlier send. IGT's own execute_protocol() already refuses this
        (_assert_not_reconfigured_since_send(), a real FDSSafetyError, not just a log message),
        but Sonic Concepts has no equivalent check at all. Disabling Execute here the moment
        anything changes protects both alike, and catches it before a researcher clicks Execute
        at all rather than after. A no-op while nothing has been sent yet."""

        if self._sent_protocol is None:
            return
        self._sent_protocol = None
        self.execution_panel.sent_protocol_label.setText(
            "Protocol changed since it was sent. Send it again before executing.")
        self.execution_panel.execute_button.setEnabled(False)

    def _on_connect_clicked(self):
        builder = self._planning_tab.builder
        ds_instance = builder.create_control_instance()
        self._worker = DrivingSystemWorker(ds_instance)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        # A second worker on the same ds_instance, own thread, solely for do_abort(), so Abort
        # can reach the hardware even while the main worker is stuck inside a blocking
        # execute_protocol()/wait_for_trigger_result() call (see this class's own docstring).
        self._abort_worker = DrivingSystemWorker(ds_instance)
        self._abort_thread = QThread(self)
        self._abort_worker.moveToThread(self._abort_thread)
        self._connect_worker_signals()
        self._thread.start()
        self._abort_thread.start()

        self.connection_panel.status_label.setText("Connecting...")
        self.connection_panel.connect_button.setEnabled(False)
        self.connection_panel.igt_hint_label.setVisible(isinstance(ds_instance, IGT))
        self._connect_requested.emit(builder.driving_system.connect_info)

    def _connect_worker_signals(self):
        """Wires this connection's own workers to both directions: their own success signals
        back to this panel's handlers, and this panel's own _*_requested signals to their slots
        (Qt.QueuedConnection, since the workers live on different threads). Extracted out of
        _on_connect_clicked() purely to keep its own statement count under pylint's limit."""

        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.sent.connect(self._on_sent)
        self._worker.executed.connect(self._on_executed)
        self._worker.armed.connect(self._on_armed)
        self._worker.error.connect(self._on_worker_error)
        self._abort_worker.aborted.connect(self._on_aborted)
        self._abort_worker.error.connect(self._on_abort_command_failed)
        queued = Qt.ConnectionType.QueuedConnection
        self._connect_requested.connect(self._worker.do_connect, queued)
        self._disconnect_requested.connect(self._worker.do_disconnect, queued)
        self._send_requested.connect(self._worker.do_send_protocol, queued)
        self._execute_requested.connect(self._worker.do_execute_protocol, queued)
        self._arm_requested.connect(self._worker.do_wait_for_trigger, queued)
        self._abort_requested.connect(self._abort_worker.do_abort, queued)

    def _on_disconnect_clicked(self):
        self._disconnect_requested.emit()

    def _on_connected(self, is_connected):
        if is_connected and isinstance(self._worker.ds_instance, SonicConcepts):
            if not self._confirm_sonic_concepts_transducer_selection():
                show_fds_error(self, FDSSafetyError(
                    "Transducer selection was not confirmed. Refusing to connect until the "
                    "correct transducer is selected on the driving system."))
                self._on_disconnect_clicked()
                return

        self.connection_panel.status_label.setText(
            "Connected" if is_connected else "Not connected")
        self.connection_panel.disconnect_button.setEnabled(is_connected)
        self.connection_panel.igt_hint_label.setVisible(False)
        self._refresh_send_enabled()

    def _confirm_sonic_concepts_transducer_selection(self):
        """Replicates SonicConcepts.check_tran_sel()'s own safety intent (confirm the physical
        transducer selector matches before sending) as a native dialog instead of that method's
        own tkinter/CTkMessagebox one, reusing the same config-driven message text. Never calls
        check_tran_sel() itself: a Qt event loop and a Tk one in the same process is fragile,
        and check_tran_sel() is never called internally by connect()/send_protocol()/
        execute_protocol() anyway, so skipping it entirely changes nothing else.

        Returns:
            bool: True if the researcher confirmed, False otherwise.
        """

        message = get_config_value(get_logger(), config, 'Equipment.Manufacturer.SC',
                                   'Check tran message',
                                   'Ensure the correct TRANSDUCER is selected on the driving '
                                   'system.')
        button = QMessageBox.question(self, "Attention", message,
                                      QMessageBox.StandardButton.Ok
                                      | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Ok)
        return button == QMessageBox.StandardButton.Ok

    def _on_disconnected(self):
        self._reset_execution_state()
        self._teardown_connection()
        self.connection_panel.status_label.setText("Not connected")
        self._refresh_driving_system_label()
        self._refresh_send_enabled()

    def _teardown_connection(self):
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        if self._abort_thread is not None:
            self._abort_thread.quit()
            self._abort_thread.wait()
        self._worker = None
        self._thread = None
        self._abort_worker = None
        self._abort_thread = None
        self.connection_panel.disconnect_button.setEnabled(False)

    def _on_send_clicked(self):
        protocol = self._planning_tab.current_protocol()
        self._sent_protocol = protocol
        self._send_requested.emit(protocol)

    def _on_sent(self):
        # Deliberately just a plain confirmation, not the protocol's own field values: see
        # ExecutionPanel's own docstring for why those belong to the console log instead.
        self.execution_panel.sent_protocol_label.setText(
            "Protocol sent. See the console below for details.")
        self.execution_panel.execute_button.setEnabled(True)
        # Nothing changed since this exact send, so sending again would just resend the same
        # protocol, disabled until either editing it again unlocks (_invalidate_sent_protocol()
        # re-enables via _refresh_send_enabled() once re-applied) or a fresh connection is made.
        self.execution_panel.send_button.setEnabled(False)

    def _on_execute_clicked(self):
        self._busy = True
        self._triggered_run = self.trigger_panel.use_trigger_checkbox.isChecked()
        self.execution_panel.execute_button.setEnabled(False)
        self.execution_panel.abort_button.setEnabled(True)
        if self._triggered_run:
            self._start_wait_for_trigger()
            self._arm_requested.emit(self._sent_protocol, self.trigger_panel.trigger_option(),
                                     self.trigger_panel.n_triggers())
        else:
            self._start_countdown(self._sent_protocol)
            self._execute_requested.emit(self._sent_protocol)

    def _start_wait_for_trigger(self):
        self._wait_elapsed_s = 0
        self.trigger_panel.waiting_label.setText("Arming...")
        self.trigger_panel.waiting_label.setVisible(True)
        self._wait_timer.start(_COUNTDOWN_INTERVAL_MS)

    def _on_wait_tick(self):
        self._wait_elapsed_s += 1
        self.trigger_panel.waiting_label.setText(
            f"Armed. Waiting for external trigger... {self._wait_elapsed_s} s")

    def _on_armed(self):
        self.trigger_panel.waiting_label.setText("Armed. Waiting for external trigger... 0 s")

    def _on_executed(self):
        """IGT's own execute_protocol()/wait_for_trigger_result() both block until the
        sonication is genuinely done, so this signal is authoritative there and finishes
        execution immediately. Sonic Concepts' own execute_protocol() returns almost instantly
        instead, with no software-visible confirmation the sonication itself has actually
        finished (see ProtocolBuilder.uses_pulse_train_repetition()'s own docstring): finishing
        execution here for SC would tell the researcher it's done while the hardware is very
        likely still running, so this is a no-op there instead. _on_countdown_tick() finishes
        execution for SC once the estimate itself runs out. SC's own triggered wait never emits
        this signal at all, see hardware_worker.py's own do_wait_for_trigger()."""

        if self._planning_tab.builder.uses_pulse_train_repetition():
            self._finish_execution()

    def _finish_execution(self):
        self._countdown_timer.stop()
        self._wait_timer.stop()
        if self._triggered_run:
            self.trigger_panel.waiting_label.setText("Triggered protocol executed successfully.")
        else:
            self.execution_panel.countdown_label.setText("Execution complete.")
        self.execution_panel.execute_button.setEnabled(True)
        self.execution_panel.abort_button.setEnabled(False)
        self._busy = False

    def _start_countdown(self, protocol):
        """Estimated time remaining for execute_protocol() to actually finish, purely a client-
        side estimate (see ExecutionPanel's own docstring): pulse_train_rep_dur for IGT (its own
        total, repeated duration), pulse_train_dur for Sonic Concepts instead, which has no
        train-repetition concept at all (see
        ProtocolBuilder.uses_pulse_train_repetition()'s own docstring)."""

        builder = self._planning_tab.builder
        if builder.uses_pulse_train_repetition():
            total_ms = protocol.pulse_train_rep_dur
        else:
            total_ms = protocol.pulse_train_dur
        self._countdown_remaining_s = round(total_ms / 1000.0)
        self.execution_panel.countdown_label.setVisible(True)
        self._update_countdown_label()
        self._countdown_timer.start(_COUNTDOWN_INTERVAL_MS)

    def _on_countdown_tick(self):
        self._countdown_remaining_s = max(0, self._countdown_remaining_s - 1)
        self._update_countdown_label()
        if self._countdown_remaining_s > 0:
            return
        if self._planning_tab.builder.uses_pulse_train_repetition():
            self._countdown_timer.stop()  # IGT: wait for the real executed() signal instead.
        else:
            self._finish_execution()  # SC: see _on_executed()'s own docstring.

    def _update_countdown_label(self):
        self.execution_panel.countdown_label.setText(
            f"Estimated time remaining: {self._countdown_remaining_s} s")

    def _on_abort_clicked(self):
        self._abort_pending = True
        self._abort_requested.emit()

    def _on_aborted(self):
        """Like _finish_execution(), stays visible with "Aborted." rather than disappearing.
        _sent_protocol is untouched: aborting doesn't invalidate it, only editing does.
        _abort_pending stays set a bit longer, see _ABORT_ERROR_GRACE_MS."""

        QTimer.singleShot(_ABORT_ERROR_GRACE_MS, self._clear_abort_pending)
        self._countdown_timer.stop()
        self._wait_timer.stop()
        if self._triggered_run:
            self.trigger_panel.waiting_label.setText("Aborted.")
        else:
            self.execution_panel.countdown_label.setText("Aborted.")
        self._busy = False
        self._triggered_run = False
        self.execution_panel.abort_button.setEnabled(False)
        self.execution_panel.execute_button.setEnabled(self._sent_protocol is not None)

    def _clear_abort_pending(self):
        self._abort_pending = False

    def _on_abort_command_failed(self, exc):
        """abort() itself raising (not the main call unwinding afterward, see
        _on_worker_error()'s own docstring) means Abort never actually reached the hardware,
        always a real, actionable error, never suppressed."""

        self._abort_pending = False
        self._on_worker_error(exc)

    def _on_worker_error(self, exc):
        """A successful abort makes the main worker's own blocked execute_protocol()/
        wait_for_trigger_result() call raise too, once it unwinds, already reflected by
        _on_aborted(), so suppressed here rather than shown as a second, confusing error on
        top of it."""

        if self._abort_pending:
            self._abort_pending = False
            return
        self._reset_execution_state()
        show_fds_error(self, exc)
        self._teardown_connection()
        self.connection_panel.status_label.setText("Not connected")
        self._refresh_driving_system_label()
        self._refresh_send_enabled()
