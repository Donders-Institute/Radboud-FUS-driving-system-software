# -*- coding: utf-8 -*-
"""
Tests for EquipmentPanel. Uses the patch_config fixture (see conftest.py) with synthetic
'UNITTEST_*' serials, so these don't depend on whatever real driving systems happen to be
listed in the shipped ds_config.ini.
"""
import pytest

from fus_ds_gui.planning.equipment_panel import EquipmentPanel


def _configure_driving_system(patch_config, serial, name, manufacturer, active='True'):
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', name)
    patch_config.set(section, 'Manufacturer', manufacturer)
    patch_config.set(section, 'Available channels', '2')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'TRAN_A')
    patch_config.set(section, 'Power options', 'Amplitude [%]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Amplitude [%]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Active?', active)


@pytest.fixture
def igt_and_citrus(patch_config):
    """One ordinary active driving system plus an active CITRUS one, so tests can assert
    CITRUS gets filtered out regardless of what the real ds_config.ini contains."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT\nUNITTEST_CITRUS')
    _configure_driving_system(patch_config, 'UNITTEST_IGT', 'Test IGT', 'IGT')
    _configure_driving_system(patch_config, 'UNITTEST_CITRUS', 'Test CITRUS', 'CITRUS')


def test_populates_from_active_driving_systems_excluding_citrus(qtbot, igt_and_citrus):
    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    names = [ds.name for ds in panel.driving_systems()]

    assert names == ['Test IGT']


def test_citrus_lowercase_manufacturer_is_still_excluded(qtbot, patch_config):
    """The exclusion check is case-insensitive, matching how the exact casing of a
    manufacturer string in ds_config.ini isn't otherwise guaranteed."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_CITRUS')
    _configure_driving_system(patch_config, 'UNITTEST_CITRUS', 'Test CITRUS', 'citrus')

    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    assert panel.driving_systems() == []


def test_starts_on_the_no_driving_system_selected_placeholder(qtbot, igt_and_citrus):
    """A researcher must deliberately choose a driving system, never build a protocol for
    whichever one happens to be listed first in ds_config.ini without having picked it
    themselves (see reload_driving_systems()'s own docstring)."""
    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    assert panel.selected_driving_system() is None


def test_selected_driving_system_returns_the_matching_object(qtbot, igt_and_citrus):
    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    panel._driving_system_combo.setCurrentIndex(1)  # UNITTEST_IGT

    assert panel.selected_driving_system().serial == 'UNITTEST_IGT'


def test_driving_system_changed_emits_the_newly_selected_object(qtbot, patch_config):
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A\nUNITTEST_B')
    _configure_driving_system(patch_config, 'UNITTEST_A', 'System A', 'IGT')
    _configure_driving_system(patch_config, 'UNITTEST_B', 'System B', 'Sonic Concepts')

    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.driving_system_changed, timeout=1000) as blocker:
        panel._driving_system_combo.setCurrentIndex(2)  # UNITTEST_B (1 is UNITTEST_A)

    assert blocker.args[0].serial == 'UNITTEST_B'


def test_empty_config_leaves_the_dropdown_empty_without_raising(qtbot, patch_config):
    """get_ds_list() raises FDSConfigError when no active driving system exists at all --
    the panel must catch that and leave the dropdown empty rather than propagating it, since
    that would otherwise crash the whole app at startup."""
    patch_config.set('Equipment', 'Driving systems', '')

    panel = EquipmentPanel()  # must not raise
    qtbot.addWidget(panel)

    assert panel.driving_systems() == []
    assert panel.selected_driving_system() is None


def test_select_driving_system_matches_by_serial(qtbot, patch_config):
    """By serial, not object identity: a caller like protocol_io.load() constructs its own
    DrivingSystem instance while parsing a file, never the same object already in this combo."""
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A\nUNITTEST_B')
    _configure_driving_system(patch_config, 'UNITTEST_A', 'System A', 'IGT')
    _configure_driving_system(patch_config, 'UNITTEST_B', 'System B', 'Sonic Concepts')
    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    from fus_driving_systems import driving_system
    other_instance = driving_system.DrivingSystem()
    other_instance.set_ds_info('UNITTEST_B')

    found = panel.select_driving_system(other_instance)

    assert found is True
    assert panel.selected_driving_system().serial == 'UNITTEST_B'


def test_select_driving_system_returns_false_when_not_offered(qtbot, igt_and_citrus):
    """E.g. the loaded protocol's own driving system is a CITRUS one, filtered out of this
    dropdown entirely."""
    panel = EquipmentPanel()
    qtbot.addWidget(panel)

    from fus_driving_systems import driving_system
    citrus_instance = driving_system.DrivingSystem()
    citrus_instance.set_ds_info('UNITTEST_CITRUS')

    found = panel.select_driving_system(citrus_instance)

    assert found is False
    assert panel.selected_driving_system() is None  # unchanged: still the placeholder


def test_reload_driving_systems_picks_up_a_config_change(qtbot, patch_config):
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A')
    _configure_driving_system(patch_config, 'UNITTEST_A', 'System A', 'IGT')

    panel = EquipmentPanel()
    qtbot.addWidget(panel)
    assert [ds.name for ds in panel.driving_systems()] == ['System A']

    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_A\nUNITTEST_B')
    _configure_driving_system(patch_config, 'UNITTEST_B', 'System B', 'Sonic Concepts')
    panel.reload_driving_systems()

    assert [ds.name for ds in panel.driving_systems()] == ['System A', 'System B']
