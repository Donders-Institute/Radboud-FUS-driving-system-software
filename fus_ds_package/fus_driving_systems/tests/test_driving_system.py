# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.driving_system.

set_ds_info()/get_ds_serials()/get_ds_names()/get_ds_list()/get_serial_from_name()
all read the module-level 'config' singleton (the real, shared ds_config.ini
ConfigParser). The patch_config fixture (see conftest.py) overrides specific
sections/keys in place and restores them afterwards, so these tests use
synthetic 'UNITTEST_*' serials rather than depending on whatever real driving
systems happen to be listed in ds_config.ini.
"""
import pytest

from fus_driving_systems import driving_system


def _configure_driving_system_section_only(patch_config, serial, name='Test DS',
                                           manufacturer='Test Manufacturer',
                                           available_channels='2', connection_info='COM1',
                                           tran_compatibility='TRAN_A\nTRAN_B',
                                           power_options='Global power\nAmplitude',
                                           requires_conv_eq='False', active='True'):
    """Configures only the per-serial section, without touching the
    combined 'Equipment'/'Driving systems' list -- use this (with an
    explicit patch_config.set('Equipment', 'Driving systems', ...) of your
    own) when a test needs more than one driving system at once."""
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', name)
    patch_config.set(section, 'Manufacturer', manufacturer)
    patch_config.set(section, 'Available channels', available_channels)
    patch_config.set(section, 'Connection info', connection_info)
    patch_config.set(section, 'Transducer compatibility', tran_compatibility)
    patch_config.set(section, 'Power options', power_options)
    patch_config.set(section, 'Requires conversion equations?', requires_conv_eq)
    patch_config.set(section, 'Active?', active)


def _configure_driving_system(patch_config, serial, **kwargs):
    """Single-driving-system convenience wrapper: also sets the combined
    'Equipment'/'Driving systems' list to just this one serial."""
    patch_config.set('Equipment', 'Driving systems', serial)
    _configure_driving_system_section_only(patch_config, serial, **kwargs)


def test_init_sets_expected_defaults():
    ds = driving_system.DrivingSystem()
    assert ds.serial is None
    assert ds.name is None
    assert ds.manufact is None
    assert ds.available_ch == 0
    assert ds.connect_info is None
    assert ds.tran_comp is None
    assert ds.power_options is None
    assert ds.require_conv_eq is False
    assert ds.is_active is True


def test_str_includes_all_fields():
    ds = driving_system.DrivingSystem()
    ds.serial = '12345'
    ds.name = 'My DS'
    ds.manufact = 'ACME'
    ds.available_ch = 4
    ds.connect_info = 'COM3'
    ds.tran_comp = ['TRAN_A', 'TRAN_B']
    ds.power_options = ['Global power']
    ds.require_conv_eq = True

    text = str(ds)
    assert '12345' in text
    assert 'My DS' in text
    assert 'ACME' in text
    assert '4' in text
    assert 'COM3' in text
    assert 'TRAN_A' in text and 'TRAN_B' in text
    assert 'Global power' in text
    assert 'True' in text


def test_clone_returns_independent_deep_copy():
    ds = driving_system.DrivingSystem()
    ds.serial = '12345'
    ds.tran_comp = ['TRAN_A']

    cloned = ds.clone()

    assert cloned is not ds
    assert cloned.serial == ds.serial
    assert cloned.tran_comp == ds.tran_comp
    assert cloned.tran_comp is not ds.tran_comp

    cloned.tran_comp.append('TRAN_B')
    assert ds.tran_comp == ['TRAN_A']


def test_set_ds_info_populates_fields_from_config(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_DS')
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_DS')

    assert ds.serial == 'UNITTEST_DS'
    assert ds.name == 'Test DS'
    assert ds.manufact == 'Test Manufacturer'
    assert ds.available_ch == 2
    assert ds.connect_info == 'COM1'
    assert ds.tran_comp == ['TRAN_A', 'TRAN_B']
    assert ds.power_options == ['Global power', 'Amplitude']
    assert ds.require_conv_eq is False
    assert ds.is_active is True


def test_get_ds_serials_returns_only_active_serials(patch_config):
    patch_config.set('Equipment', 'Driving systems',
                     'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    patch_config.set('Equipment.Driving system.UNITTEST_ACTIVE', 'Active?', 'True')
    patch_config.set('Equipment.Driving system.UNITTEST_INACTIVE', 'Active?', 'False')

    assert driving_system.get_ds_serials() == ['UNITTEST_ACTIVE']


def test_get_ds_serials_exits_when_none_active(patch_config):
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_INACTIVE_ONLY')
    patch_config.set('Equipment.Driving system.UNITTEST_INACTIVE_ONLY', 'Active?', 'False')

    with pytest.raises(SystemExit) as exc_info:
        driving_system.get_ds_serials()
    assert 'No active driving systems' in str(exc_info.value)


def test_get_ds_names_excludes_inactive_driving_systems(patch_config):
    """
    get_ds_names() delegates filtering entirely to get_ds_serials() (it
    just iterates whatever that returns) -- a single-driving-system setup
    would pass even if get_ds_names() ignored the Active? flag completely.
    Configuring one active and one inactive system here actually exercises
    that the filtering carries through the composition.
    """
    patch_config.set('Equipment', 'Driving systems',
                     'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    _configure_driving_system_section_only(patch_config, 'UNITTEST_ACTIVE',
                                           name='Active DS', active='True')
    _configure_driving_system_section_only(patch_config, 'UNITTEST_INACTIVE',
                                           name='Inactive DS', active='False')

    assert driving_system.get_ds_names() == ['Active DS']


def test_get_ds_list_excludes_inactive_driving_systems(patch_config):
    """Same composition concern as test_get_ds_names_excludes_inactive_driving_systems
    above, for get_ds_list()."""
    patch_config.set('Equipment', 'Driving systems',
                     'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    _configure_driving_system_section_only(patch_config, 'UNITTEST_ACTIVE',
                                           name='Active DS', active='True')
    _configure_driving_system_section_only(patch_config, 'UNITTEST_INACTIVE',
                                           name='Inactive DS', active='False')

    ds_list = driving_system.get_ds_list()

    assert len(ds_list) == 1
    assert isinstance(ds_list[0], driving_system.DrivingSystem)
    assert ds_list[0].name == 'Active DS'

# Note: get_ds_names()'s own 'if len(names) < 1: sys.exit(...)' and
# get_ds_list()'s 'except KeyError' are NOT separately tested here. Both are
# unreachable via the public API: get_ds_serials() already guarantees at
# least one serial (or sys.exits itself first, see
# test_get_ds_serials_exits_when_none_active above) before either of these
# functions' loops ever run, and get_config_value() never raises KeyError
# (it checks membership defensively). Forcing those branches would mean
# testing a state the real code can't reach, not real behavior.


def test_get_serial_from_name_returns_matching_serial(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_DS', name='My Driving System')
    assert driving_system.get_serial_from_name('My Driving System') == 'UNITTEST_DS'


def test_get_serial_from_name_returns_none_when_not_found(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_DS', name='My Driving System')
    assert driving_system.get_serial_from_name('Nonexistent') is None
