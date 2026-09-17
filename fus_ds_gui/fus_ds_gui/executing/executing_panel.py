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
from fus_ds_gui.workers.hardware_worker import DrivingSystemWorker

_COUNTDOWN_INTERVAL_MS = 1000


class ExecutingPanel(QWidget):
    """
    Connects to real hardware and sends/executes the Planning tab's own current protocol.
    Always visible next to Planning (see MainWindow), not something you switch to: Send is only
    ever available while the Planning tab is locked (see PlanningTab.is_locked()'s own
    docstring), so what this panel would send always exactly matches what the Planning tab is
    currently showing.

    Trigger support and abort are out of scope here (a later phase); this panel stops at
    unattended send/execute.

    One DrivingSystemWorker/QThread is created per connection (see hardware_worker.py's own
    docstring) and torn down again on Disconnect or on a connection-level error; nothing here
    ever reuses one across two separate connections.
    """

    _connect_requested = Signal(str)
    _disconnect_requested = Signal()
    _send_requested = Signal(object)
    _execute_requested = Signal(object)

    def __init__(self, planning_tab, parent=None):
        super().__init__(parent)

        self._planning_tab = planning_tab
        self._worker = None
        self._thread = None
        self._sent_protocol = None
        self._countdown_remaining_s = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self.connection_panel = ConnectionPanel()
        self.connection_panel.connect_clicked.connect(self._on_connect_clicked)
        self.connection_panel.disconnect_clicked.connect(self._on_disconnect_clicked)

        self.execution_panel = ExecutionPanel()
        self.execution_panel.send_clicked.connect(self._on_send_clicked)
        self.execution_panel.execute_clicked.connect(self._on_execute_clicked)

        self.console_panel = ConsolePanel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.connection_panel)
        layout.addWidget(self.execution_panel)
        layout.addWidget(self.console_panel)
        layout.addStretch()

        planning_tab.lock_changed.connect(self._refresh_send_enabled)
        planning_tab.equipment_panel.driving_system_changed.connect(
            self._refresh_driving_system_label)
        self._refresh_driving_system_label()
        self._refresh_send_enabled()

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

    def _on_connect_clicked(self):
        builder = self._planning_tab.builder
        ds_instance = builder.create_control_instance()
        self._worker = DrivingSystemWorker(ds_instance)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._connect_worker_signals()
        self._thread.start()

        self.connection_panel.status_label.setText("Connecting...")
        self.connection_panel.connect_button.setEnabled(False)
        self.connection_panel.igt_hint_label.setVisible(isinstance(ds_instance, IGT))
        self._connect_requested.emit(builder.driving_system.connect_info)

    def _connect_worker_signals(self):
        """Wires this connection's own worker to both directions: its own success signals back
        to this panel's handlers, and this panel's own _*_requested signals to its slots
        (Qt.QueuedConnection, since the worker lives on a different thread). Extracted out of
        _on_connect_clicked() purely to keep its own statement count under pylint's limit."""

        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.sent.connect(self._on_sent)
        self._worker.executed.connect(self._on_executed)
        self._worker.error.connect(self._on_worker_error)
        queued = Qt.ConnectionType.QueuedConnection
        self._connect_requested.connect(self._worker.do_connect, queued)
        self._disconnect_requested.connect(self._worker.do_disconnect, queued)
        self._send_requested.connect(self._worker.do_send_protocol, queued)
        self._execute_requested.connect(self._worker.do_execute_protocol, queued)

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
        self._teardown_connection()
        self.connection_panel.status_label.setText("Not connected")
        self._refresh_driving_system_label()
        self._refresh_send_enabled()

    def _teardown_connection(self):
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self._worker = None
        self._thread = None
        self.connection_panel.disconnect_button.setEnabled(False)

    def _on_send_clicked(self):
        protocol = self._planning_tab.current_protocol()
        self._sent_protocol = protocol
        self._send_requested.emit(protocol)

    def _on_sent(self):
        self.execution_panel.sent_protocol_label.setText(str(self._sent_protocol))
        self.execution_panel.execute_button.setEnabled(True)

    def _on_execute_clicked(self):
        self._start_countdown(self._sent_protocol)
        self.execution_panel.execute_button.setEnabled(False)
        self._execute_requested.emit(self._sent_protocol)

    def _on_executed(self):
        """IGT's own execute_protocol() blocks until the sonication is genuinely done, so this
        signal is authoritative there and finishes execution immediately. Sonic Concepts' own
        execute_protocol() returns almost instantly instead, with no software-visible
        confirmation the sonication itself has actually finished (see
        ProtocolBuilder.uses_pulse_train_repetition()'s own docstring): finishing execution
        here for SC would tell the researcher it's done while the hardware is very likely
        still running, so this is a no-op there instead. _on_countdown_tick() finishes
        execution for SC once the estimate itself runs out."""

        if self._planning_tab.builder.uses_pulse_train_repetition():
            self._finish_execution()

    def _finish_execution(self):
        self._countdown_timer.stop()
        self.execution_panel.countdown_label.setVisible(False)
        self.execution_panel.execute_button.setEnabled(True)

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

    def _on_worker_error(self, exc):
        self._countdown_timer.stop()
        show_fds_error(self, exc)
        self._teardown_connection()
        self.connection_panel.status_label.setText("Not connected")
        self._refresh_driving_system_label()
        self._refresh_send_enabled()
