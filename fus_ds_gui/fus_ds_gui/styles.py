# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

# Radboud red (the official brand color, #E3000B), for the one button in each tab that
# actually commits an action (Apply, Execute). Only :enabled is styled here: a disabled button
# matches no rule at all, so it falls back to the platform's own native disabled look, identical
# to every other (unstyled) button, instead of a hand-picked grey trying to imitate it.
ACCENT_BUTTON_STYLE = """
QPushButton:enabled {
    background-color: #E3000B;
    color: white;
    padding: 4px 14px;
    border-radius: 4px;
}
QPushButton:enabled:hover {
    background-color: #C40009;
}
QPushButton:enabled:pressed {
    background-color: #A50008;
}
"""
