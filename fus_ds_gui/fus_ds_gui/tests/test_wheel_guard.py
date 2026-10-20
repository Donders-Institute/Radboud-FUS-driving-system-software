# -*- coding: utf-8 -*-
"""Tests for WheelGuard: the wheel scrolls the page and never changes a field."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QScrollArea, QVBoxLayout, QWidget)

from fus_ds_gui.wheel_guard import WheelGuard


@pytest.fixture
def guarded_page(qtbot):
    guard = WheelGuard(QApplication.instance())
    QApplication.instance().installEventFilter(guard)

    content = QWidget()
    layout = QVBoxLayout(content)
    spin = QDoubleSpinBox()
    spin.setRange(0, 100)
    spin.setValue(10)
    layout.addWidget(spin)
    layout.addWidget(QWidget())
    content.setMinimumHeight(2000)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    scroll.resize(300, 200)
    qtbot.addWidget(scroll)
    scroll.show()
    qtbot.waitExposed(scroll)

    yield scroll, spin

    QApplication.instance().removeEventFilter(guard)


def _wheel_down(widget):
    center = QPointF(widget.rect().center())
    event = QWheelEvent(center, widget.mapToGlobal(center), QPoint(0, 0), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)
    assert event.type() == QEvent.Type.Wheel


def test_wheel_over_an_unfocused_spinbox_scrolls_the_page_not_the_value(guarded_page):
    scroll, spin = guarded_page
    spin.clearFocus()  # the first field of a shown window starts with focus

    _wheel_down(spin)

    assert spin.value() == 10
    assert scroll.verticalScrollBar().value() > 0


def test_wheel_over_the_focused_spinbox_does_not_change_its_value_either(guarded_page):
    scroll, spin = guarded_page
    spin.setFocus()

    _wheel_down(spin)

    assert spin.value() == 10
    assert scroll.verticalScrollBar().value() > 0
