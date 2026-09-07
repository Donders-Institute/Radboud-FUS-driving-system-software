# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

import sys

from PySide6.QtWidgets import QApplication

from fus_ds_gui.main_window import MainWindow


def main():
    """
    Entry point: python -m fus_ds_gui.app
    """

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
