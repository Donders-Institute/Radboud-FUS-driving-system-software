# -*- coding: utf-8 -*-
"""
Unit tests for fus_driving_systems/transducer.py.

Uses the real bundled ds_config.ini — no config mocking needed.
Error-path tests rely on pytest.raises(SystemExit) since sys.exit() raises SystemExit.
"""

import pytest

from fus_driving_systems.transducer import (
    Transducer,
    get_tran_serials,
    get_tran_names,
    get_tran_list,
    get_serial_from_name,
)

# ---------------------------------------------------------------------------
# Known config values (from ds_config.ini) used as expected values
# ---------------------------------------------------------------------------
CTX_250_009 = 'CTX-250-009'
IS_PCD15287_01001 = 'IS_PCD15287_01001'
CTX_500_024 = 'CTX-500-024'   # inactive
IS_PCD15473_01002 = 'IS_PCD15473_01002'  # inactive
DUMMY = 'Dummy'               # inactive
DPX_500_022 = 'DPX-500-022'  # active, empty steer_info

ACTIVE_SERIAL_COUNT = 13
INACTIVE_SERIALS = [CTX_500_024, IS_PCD15473_01002, DUMMY]


# ===========================================================================
# TestTransducerInit
# ===========================================================================
class TestTransducerInit:
    def test_default_serial_is_none(self):
        tran = Transducer()
        assert tran.serial is None
        assert tran.name is None
        assert tran.manufact is None
        assert tran.steer_info is None

    def test_default_numeric_zeros(self):
        tran = Transducer()
        assert tran.elements == 0
        assert tran.fund_freq == 0
        assert tran.natural_foc == 0
        assert tran.exit_plane_dist == 0

    def test_default_is_active_true(self):
        assert Transducer().is_active is True

    def test_default_min_foc_from_config(self):
        assert Transducer().min_foc == 15.0

    def test_default_max_foc_from_config(self):
        assert Transducer().max_foc == 1000.0


# ===========================================================================
# TestSetTransducerInfo
# ===========================================================================
class TestSetTransducerInfo:
    def test_sonic_concepts_transducer(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        assert tran.name == 'NeuroFUS 2 ch. CTX-250-009'
        assert tran.manufact == 'Sonic Concepts'
        assert tran.elements == 2
        assert tran.fund_freq == 250
        assert tran.natural_foc == 0.0
        assert tran.exit_plane_dist == 0.0
        assert tran.min_foc == 15.9
        assert tran.max_foc == 46.0
        assert tran.is_active is True

    def test_imasonic_transducer(self):
        tran = Transducer()
        tran.set_transducer_info(IS_PCD15287_01001)
        assert tran.manufact == 'Imasonic'
        assert tran.elements == 10
        assert tran.fund_freq == 300
        assert tran.natural_foc == 75.0
        assert tran.exit_plane_dist == 9.7
        assert tran.min_foc == 5.0
        assert tran.max_foc == 91.7
        assert tran.is_active is True

    def test_serial_is_stored(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        assert tran.serial == CTX_250_009

    def test_inactive_transducer(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_500_024)
        assert tran.is_active is False

    def test_empty_steer_info(self):
        tran = Transducer()
        tran.set_transducer_info(DPX_500_022)
        assert tran.steer_info == ''

    def test_imasonic_has_steer_info_path(self):
        tran = Transducer()
        tran.set_transducer_info(IS_PCD15287_01001)
        assert isinstance(tran.steer_info, str)
        assert len(tran.steer_info) > 0

    def test_elements_is_int(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        assert isinstance(tran.elements, int)

    def test_fund_freq_is_int(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        assert isinstance(tran.fund_freq, int)

    def test_focus_values_are_float(self):
        tran = Transducer()
        tran.set_transducer_info(IS_PCD15287_01001)
        assert isinstance(tran.min_foc, float)
        assert isinstance(tran.max_foc, float)
        assert isinstance(tran.natural_foc, float)
        assert isinstance(tran.exit_plane_dist, float)

    def test_unknown_serial_exits(self):
        tran = Transducer()
        with pytest.raises(SystemExit):
            tran.set_transducer_info('INVALID_SERIAL_XYZ')


# ===========================================================================
# TestTransducerStr
# ===========================================================================
class TestTransducerStr:
    @pytest.fixture
    def loaded_tran(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        return tran

    def test_str_returns_string(self, loaded_tran):
        assert isinstance(str(loaded_tran), str)

    def test_str_contains_serial(self, loaded_tran):
        assert CTX_250_009 in str(loaded_tran)

    def test_str_contains_all_field_labels(self, loaded_tran):
        output = str(loaded_tran)
        expected_labels = [
            'Transducer serial number:',
            'Transducer name:',
            'Transducer manufacturer:',
            'Transducer elements:',
            'Transducer fundamental frequency',
            'Transducer natural focus',
            'Transducer exit plane',
            'Transducer min. focus',
            'Transducer max. focus',
            'steer table',
        ]
        for label in expected_labels:
            assert label in output, f'Missing label in __str__ output: {label!r}'


# ===========================================================================
# TestTransducerClone
# ===========================================================================
class TestTransducerClone:
    @pytest.fixture
    def loaded_tran(self):
        tran = Transducer()
        tran.set_transducer_info(CTX_250_009)
        return tran

    def test_clone_is_different_object(self, loaded_tran):
        assert loaded_tran.clone() is not loaded_tran

    def test_clone_attributes_equal(self, loaded_tran):
        clone = loaded_tran.clone()
        assert clone.__dict__ == loaded_tran.__dict__

    def test_clone_is_deep_copy(self, loaded_tran):
        clone = loaded_tran.clone()
        clone.serial = 'MUTATED'
        assert loaded_tran.serial == CTX_250_009

    def test_clone_of_loaded_transducer(self, loaded_tran):
        clone = loaded_tran.clone()
        assert clone.serial == CTX_250_009
        assert clone.name == loaded_tran.name
        assert clone.elements == loaded_tran.elements


# ===========================================================================
# TestGetTranSerials
# ===========================================================================
class TestGetTranSerials:
    def test_returns_list(self):
        assert isinstance(get_tran_serials(), list)

    def test_returns_strings(self):
        assert all(isinstance(s, str) for s in get_tran_serials())

    def test_only_active_serials(self):
        serials = get_tran_serials()
        for inactive in INACTIVE_SERIALS:
            assert inactive not in serials

    def test_known_active_serials_present(self):
        serials = get_tran_serials()
        assert CTX_250_009 in serials
        assert IS_PCD15287_01001 in serials

    def test_count_active_serials(self):
        assert len(get_tran_serials()) == ACTIVE_SERIAL_COUNT


# ===========================================================================
# TestGetTranNames
# ===========================================================================
class TestGetTranNames:
    def test_returns_list_of_strings(self):
        names = get_tran_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)

    def test_same_length_as_serials(self):
        assert len(get_tran_names()) == len(get_tran_serials())

    def test_known_name_present(self):
        assert 'NeuroFUS 2 ch. CTX-250-009' in get_tran_names()

    def test_no_inactive_names(self):
        assert 'Dummy load' not in get_tran_names()


# ===========================================================================
# TestGetTranList
# ===========================================================================
class TestGetTranList:
    def test_returns_list_of_transducer_objects(self):
        tran_list = get_tran_list()
        assert isinstance(tran_list, list)
        assert all(isinstance(t, Transducer) for t in tran_list)

    def test_same_length_as_serials(self):
        assert len(get_tran_list()) == len(get_tran_serials())

    def test_all_have_serial_set(self):
        assert all(t.serial is not None for t in get_tran_list())

    def test_serials_match_get_tran_serials(self):
        list_serials = [t.serial for t in get_tran_list()]
        assert list_serials == get_tran_serials()


# ===========================================================================
# TestGetSerialFromName
# ===========================================================================
class TestGetSerialFromName:
    def test_known_name_returns_correct_serial(self):
        assert get_serial_from_name('NeuroFUS 2 ch. CTX-250-009') == CTX_250_009

    def test_imasonic_name_returns_serial(self):
        result = get_serial_from_name('Imasonic 10 ch. PCD15287_01001 ROC 75 mm')
        assert result == IS_PCD15287_01001

    def test_unknown_name_returns_none(self):
        assert get_serial_from_name('Nonexistent Transducer XYZ') is None
