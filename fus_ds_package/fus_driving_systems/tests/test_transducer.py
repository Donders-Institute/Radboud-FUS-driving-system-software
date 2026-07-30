# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.transducer -- structurally a near-mirror of
driving_system.py, but note Transducer.__init__ itself reads config
('Focus'/'Default.minimum'/'Default.maximum') to seed min_foc/max_foc, unlike
DrivingSystem.__init__ which is config-free. patch_config (see conftest.py)
keeps that -- and the per-transducer sections used below -- decoupled from
whatever real transducers happen to be listed in ds_config.ini.
"""
import pytest

from fus_driving_systems import transducer


def _configure_transducer_section_only(patch_config, serial, name='Test Transducer',
                                       manufacturer='Test Manufacturer', elements='128',
                                       fund_freq='300', natural_foc='50.0',
                                       exit_plane_dist='10.0', min_focus='20.0',
                                       max_focus='80.0', steer_info='igt/config/steer.xlsx',
                                       active='True'):
    """Configures only the per-serial section, without touching the
    combined 'Equipment'/'Transducers' list -- use this (with an explicit
    patch_config.set('Equipment', 'Transducers', ...) of your own) when a
    test needs more than one transducer at once."""
    section = f'Equipment.Transducer.{serial}'
    patch_config.set(section, 'Name', name)
    patch_config.set(section, 'Manufacturer', manufacturer)
    patch_config.set(section, 'Elements', elements)
    patch_config.set(section, 'Fund. freq.', fund_freq)
    patch_config.set(section, 'Natural focus', natural_foc)
    patch_config.set(section, 'Exit plane - first element dist.', exit_plane_dist)
    patch_config.set(section, 'Min. focus', min_focus)
    patch_config.set(section, 'Max. focus', max_focus)
    patch_config.set(section, 'Steer information', steer_info)
    patch_config.set(section, 'Active?', active)


def _configure_transducer(patch_config, serial, **kwargs):
    """Single-transducer convenience wrapper: also sets the combined
    'Equipment'/'Transducers' list to just this one serial."""
    patch_config.set('Equipment', 'Transducers', serial)
    _configure_transducer_section_only(patch_config, serial, **kwargs)


def test_init_sets_expected_defaults(patch_config):
    patch_config.set('Focus', 'Default.minimum', '5')
    patch_config.set('Focus', 'Default.maximum', '200')

    tran = transducer.Transducer()

    assert tran.serial is None
    assert tran.name is None
    assert tran.manufact is None
    assert tran.elements == 0
    assert tran.fund_freq == 0
    assert tran.natural_foc == 0
    assert tran.exit_plane_dist == 0
    assert tran.min_foc == 5.0
    assert tran.max_foc == 200.0
    assert tran.steer_info is None
    assert tran.is_active is True


def test_str_includes_all_fields():
    tran = transducer.Transducer()
    tran.serial = '12345'
    tran.name = 'My Transducer'
    tran.manufact = 'ACME'
    tran.elements = 128
    tran.fund_freq = 300
    tran.natural_foc = 50.0
    tran.exit_plane_dist = 10.0
    tran.min_foc = 20.0
    tran.max_foc = 80.0
    tran.steer_info = 'igt/config/steer.xlsx'

    text = str(tran)
    assert '12345' in text
    assert 'My Transducer' in text
    assert 'ACME' in text
    assert '128' in text
    assert '300' in text
    assert '50.0' in text
    assert '10.0' in text
    assert '20.0' in text
    assert '80.0' in text
    assert 'igt/config/steer.xlsx' in text


def test_clone_returns_independent_deep_copy():
    tran = transducer.Transducer()
    tran.serial = '12345'
    tran.name = 'My Transducer'

    cloned = tran.clone()

    assert cloned is not tran
    assert cloned.serial == tran.serial
    assert cloned.name == tran.name

    cloned.name = 'Renamed'
    assert tran.name == 'My Transducer'


def test_set_transducer_info_populates_fields_from_config(patch_config):
    _configure_transducer(patch_config, 'UNITTEST_TRAN')
    tran = transducer.Transducer()
    tran.set_transducer_info('UNITTEST_TRAN')

    assert tran.serial == 'UNITTEST_TRAN'
    assert tran.name == 'Test Transducer'
    assert tran.manufact == 'Test Manufacturer'
    assert tran.elements == 128
    assert tran.fund_freq == 300
    assert tran.natural_foc == 50.0
    assert tran.exit_plane_dist == 10.0
    assert tran.min_foc == 20.0
    assert tran.max_foc == 80.0
    assert tran.steer_info == 'igt/config/steer.xlsx'
    assert tran.is_active is True


def test_get_tran_serials_returns_only_active_serials(patch_config):
    patch_config.set('Equipment', 'Transducers',
                     'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    patch_config.set('Equipment.Transducer.UNITTEST_ACTIVE', 'Active?', 'True')
    patch_config.set('Equipment.Transducer.UNITTEST_INACTIVE', 'Active?', 'False')

    assert transducer.get_tran_serials() == ['UNITTEST_ACTIVE']


def test_get_tran_serials_exits_when_none_active(patch_config):
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_INACTIVE_ONLY')
    patch_config.set('Equipment.Transducer.UNITTEST_INACTIVE_ONLY', 'Active?', 'False')

    with pytest.raises(SystemExit) as exc_info:
        transducer.get_tran_serials()
    assert 'No active tranducers' in str(exc_info.value)


def test_get_tran_names_excludes_inactive_transducers(patch_config):
    """
    get_tran_names() delegates filtering entirely to get_tran_serials() (it
    just iterates whatever that returns) -- a single-transducer setup would
    pass even if get_tran_names() ignored the Active? flag completely.
    Configuring one active and one inactive transducer here actually
    exercises that the filtering carries through the composition (mirrors
    test_get_ds_names_excludes_inactive_driving_systems in test_driving_system.py).
    """
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    _configure_transducer_section_only(patch_config, 'UNITTEST_ACTIVE',
                                       name='Active Transducer', active='True')
    _configure_transducer_section_only(patch_config, 'UNITTEST_INACTIVE',
                                       name='Inactive Transducer', active='False')

    assert transducer.get_tran_names() == ['Active Transducer']


def test_get_tran_list_excludes_inactive_transducers(patch_config):
    """Same composition concern as test_get_tran_names_excludes_inactive_transducers
    above, for get_tran_list()."""
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_ACTIVE\nUNITTEST_INACTIVE')
    _configure_transducer_section_only(patch_config, 'UNITTEST_ACTIVE',
                                       name='Active Transducer', active='True')
    _configure_transducer_section_only(patch_config, 'UNITTEST_INACTIVE',
                                       name='Inactive Transducer', active='False')

    tran_list = transducer.get_tran_list()

    assert len(tran_list) == 1
    assert isinstance(tran_list[0], transducer.Transducer)
    assert tran_list[0].name == 'Active Transducer'

# Note: get_tran_names()/get_tran_list()'s own 'no transducers found'
# sys.exit and 'except KeyError' branches are NOT separately tested here,
# for the same reason as driving_system.py's mirror-image branches (see the
# note in test_driving_system.py): get_tran_serials() already guarantees at
# least one serial (or sys.exits itself first) before either function's
# loop runs, and get_config_value() never raises KeyError.


def test_get_serial_from_name_returns_matching_serial(patch_config):
    _configure_transducer(patch_config, 'UNITTEST_TRAN', name='My Transducer')
    assert transducer.get_serial_from_name('My Transducer') == 'UNITTEST_TRAN'


def test_get_serial_from_name_returns_none_when_not_found(patch_config):
    _configure_transducer(patch_config, 'UNITTEST_TRAN', name='My Transducer')
    assert transducer.get_serial_from_name('Nonexistent') is None
