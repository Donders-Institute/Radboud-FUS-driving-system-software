# -*- coding: utf-8 -*-
"""Tests for TriggerPanel."""
from fus_ds_gui.executing.trigger_panel import ONE_PULSE_TRAIN, WHOLE_PROTOCOL, TriggerPanel


def test_starts_unchecked_with_waiting_label_hidden(qtbot):
    panel = TriggerPanel()
    qtbot.addWidget(panel)

    assert panel.use_trigger_checkbox.isChecked() is False
    assert panel.waiting_label.isVisible() is False


def test_trigger_option_reflects_the_combo(qtbot):
    panel = TriggerPanel()
    qtbot.addWidget(panel)

    panel.trigger_mode_combo.setCurrentText(WHOLE_PROTOCOL)
    assert panel.trigger_option() == WHOLE_PROTOCOL

    panel.trigger_mode_combo.setCurrentText(ONE_PULSE_TRAIN)
    assert panel.trigger_option() == ONE_PULSE_TRAIN


def test_n_triggers_only_set_for_one_pulse_train(qtbot):
    panel = TriggerPanel()
    qtbot.addWidget(panel)

    panel.trigger_mode_combo.setCurrentText(WHOLE_PROTOCOL)
    assert panel.n_triggers() is None

    panel.trigger_mode_combo.setCurrentText(ONE_PULSE_TRAIN)
    panel.n_triggers_spin.setValue(3)
    assert panel.n_triggers() == 3


def test_checkbox_toggle_emits_settings_changed(qtbot):
    panel = TriggerPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.settings_changed, timeout=1000):
        panel.use_trigger_checkbox.setChecked(True)


def test_mode_change_emits_settings_changed(qtbot):
    panel = TriggerPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.settings_changed, timeout=1000):
        panel.trigger_mode_combo.setCurrentIndex(1 - panel.trigger_mode_combo.currentIndex())
