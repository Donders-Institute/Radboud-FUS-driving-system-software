# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import logging
import sys

from PySide6.QtWidgets import QApplication

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger, initialize_logger
from fus_driving_systems.utils import get_config_value

from fus_ds_gui.main_window import MainWindow
from fus_ds_gui.wheel_guard import WheelGuard

# Matches every standalone example script's own default (initialize_logger()'s log_dir param):
# the same config key, so a GUI session and a script session land their logs in the same place
# by default. Also enables crash detection (faulthandler, GitHub issue #126) for the whole GUI
# session.
_LOG_FILENAME = 'fus_ds_gui'

# Mirrors create_config.py's own DEMO_MAX_PRESSURE default, duplicated for the same reason as
# fus_driving_systems.config.logging_config._SHIPPED_MAX_PRESSURE_MPA: create_config.py is a
# generator script, not importable. Keep in sync by hand.
_SHIPPED_DEMO_MAX_PRESSURE_MPA = 0.6


class _StartupRecords(logging.Filter):
    """Keeps every record it sees, to replay them into the console panel (see main()). It is a
    logging.Filter because that is how a logger can be tapped; it filters nothing. Not a handler,
    because initialize_logger() removes handlers."""

    def __init__(self):
        super().__init__()
        self.records = []

    def filter(self, record):
        self.records.append(record)
        return True


def warn_if_demo_pressure_limit_modified():
    """
    Logs an explicit WARNING at the start of a session if the configured 'Demo maximum pressure
    allowed in free water [MPa]' differs from what create_config.py ships: the Demo mode ceiling
    is a safety margin below the package's own limit, and is otherwise easy to miss among other
    config detail. Same idea as the package's own warning for the global pressure limit.
    """

    try:
        active_mpa = float(get_config_value(
            None, config, 'Power', 'Demo maximum pressure allowed in free water [MPa]',
            _SHIPPED_DEMO_MAX_PRESSURE_MPA))
    except (TypeError, ValueError):
        return  # a malformed value is not this warning's job to catch

    if active_mpa != _SHIPPED_DEMO_MAX_PRESSURE_MPA:
        get_logger().warning(
            f'This session is running with a MODIFIED Demo mode pressure limit of {active_mpa} '
            f'MPa (default: {_SHIPPED_DEMO_MAX_PRESSURE_MPA} MPa).')


def main():
    """
    Entry point: python -m fus_ds_gui.app
    """

    log_dir = get_config_value(None, config, 'Logging', 'Temporary logging path', 'C:\\Temp')

    # initialize_logger() drops every handler, and the console panel only attaches once the
    # window exists, so the start-up records (version, modified pressure limits) are collected
    # here and handed to the console afterwards.
    startup_records = _StartupRecords()
    get_logger().addFilter(startup_records)
    initialize_logger(log_dir, _LOG_FILENAME)
    warn_if_demo_pressure_limit_modified()

    app = QApplication(sys.argv)
    app.installEventFilter(WheelGuard(app))
    window = MainWindow()
    get_logger().removeFilter(startup_records)
    window.executing_panel.console_panel.replay(startup_records.records)
    app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
