# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFormLayout, QLabel

# SlotEditor's own label texts, used as the reference width every other QFormLayout in the
# Planning tab aligns to (see align_form_labels()); a placeholder wide enough for a realistic
# focus range stands in for _focus_value_label's actual, dynamic text.
_REFERENCE_LABELS = (
    "Transducer:",
    "Focus value (-999.9-999.9):",
    "Focus value (x, y, z):",
    "Power:",
    "Operating frequency:",
    "Dephasing mode:",
    "Dephasing degree:",
    "Dephasing values:",
)


def align_form_labels(form):
    """Widens every row's own label to at least SlotEditor's own label column width, so
    shorter labels elsewhere (e.g. TimingPanel's "Power:") start their field at the same x
    position instead of each QFormLayout sizing its label column independently."""

    min_width = max(QFontMetrics(QLabel().font()).horizontalAdvance(text)
                    for text in _REFERENCE_LABELS)
    for row in range(form.rowCount()):
        label_item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        if label_item is not None and label_item.widget() is not None:
            label_item.widget().setMinimumWidth(min_width)
