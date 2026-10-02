# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import sys

from PySide6.QtWidgets import QApplication

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import initialize_logger
from fus_driving_systems.utils import get_config_value

from fus_ds_gui.main_window import MainWindow

# Matches every standalone example script's own default (initialize_logger()'s log_dir param):
# the same config key, so a GUI session and a script session land their logs in the same place
# by default. Also enables crash detection (faulthandler, GitHub issue #126) for the whole GUI
# session.
_LOG_FILENAME = 'fus_ds_gui'


def main():
    """
    Entry point: python -m fus_ds_gui.app
    """

    log_dir = get_config_value(None, config, 'Logging', 'Temporary logging path', 'C:\\Temp')
    initialize_logger(log_dir, _LOG_FILENAME)

    app = QApplication(sys.argv)
    window = MainWindow()
    app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
