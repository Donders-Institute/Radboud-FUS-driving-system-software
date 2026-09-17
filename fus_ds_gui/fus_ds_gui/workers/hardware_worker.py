# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtCore import QObject, Signal, Slot

from fus_driving_systems.exceptions import FDSError


class DrivingSystemWorker(QObject):
    """
    Owns one ControlDrivingSystem instance's whole connected lifetime, moved (via
    moveToThread()) onto its own dedicated QThread so the blocking connect()/send_protocol()/
    execute_protocol() calls it wraps never freeze the GUI thread. One worker per connection:
    these SDK/serial objects are stateful and single-connection, so nothing else may call
    methods on the same ds_instance concurrently (see
    ProtocolBuilder.create_control_instance()'s own docstring on why this must be a fresh
    instance, never the Planning tab's own validation-only one).

    Every slot below wraps exactly one blocking backend call in try/except FDSError, emitting
    the matching success signal or error(exc) instead of letting the exception propagate,
    which would otherwise crash the worker thread silently, with no way for the GUI thread to
    find out.

    Signals:
        connected(bool): Emitted after a successful connect(), carrying is_connected()'s own
            answer (normally True, but checked rather than assumed).
        disconnected(): Emitted after a successful disconnect().
        sent(): Emitted after a successful send_protocol().
        executed(): Emitted once execute_protocol() returns without raising. Blocks for the
            whole protocol duration on IGT; returns almost immediately on Sonic Concepts, with
            no confirmation the sonication itself actually finished (see
            ProtocolBuilder.uses_pulse_train_repetition()'s own docstring on that asymmetry).
        error(object): Emitted instead of any of the above whenever the wrapped call raises
            FDSError; carries the caught exception itself, not a string, so
            error_dialogs.show_fds_error() can dispatch on its real type.
    """

    connected = Signal(bool)
    disconnected = Signal()
    sent = Signal()
    executed = Signal()
    error = Signal(object)

    def __init__(self, ds_instance):
        super().__init__()
        self.ds_instance = ds_instance

    @Slot(str)
    def do_connect(self, connect_info):
        """Connects to the driving system; see this class's own docstring."""

        try:
            self.ds_instance.connect(connect_info)
        except FDSError as e:
            self.error.emit(e)
            return
        self.connected.emit(self.ds_instance.is_connected())

    @Slot()
    def do_disconnect(self):
        """Disconnects from the driving system; see this class's own docstring."""

        try:
            self.ds_instance.disconnect()
        except FDSError as e:
            self.error.emit(e)
            return
        self.disconnected.emit()

    @Slot(object)
    def do_send_protocol(self, protocol):
        """Sends protocol to the driving system; see this class's own docstring."""

        try:
            self.ds_instance.send_protocol(protocol)
        except FDSError as e:
            self.error.emit(e)
            return
        self.sent.emit()

    @Slot(object)
    def do_execute_protocol(self, protocol):
        """Executes the already-sent protocol; see this class's own docstring."""

        try:
            self.ds_instance.execute_protocol(protocol)
        except FDSError as e:
            self.error.emit(e)
            return
        self.executed.emit()
