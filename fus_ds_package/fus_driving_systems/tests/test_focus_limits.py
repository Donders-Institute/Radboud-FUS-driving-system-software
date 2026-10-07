# -*- coding: utf-8 -*-
"""
Focus limits of every active transducer on every active driving system it is compatible with,
read from the shipped configuration (not a synthetic one). The limits a researcher is offered
(the transducer's min_foc/max_foc, shifted by exit_plane_dist for the mid-bowl option, as the GUI
does) must be accepted by the protocol; for the exit-plane option, which is exact, just outside
must be rejected.
"""
import pytest

from fus_driving_systems.driving_system import DrivingSystem, get_ds_serials
from fus_driving_systems.exceptions import FDSValidationError
from fus_driving_systems.transducer import Transducer, get_tran_serials
from fus_driving_systems.tus_protocol import TUSProtocol

EXIT_PLANE = 'Focus wrt exit plane [mm]'
MID_BOWL = 'Focus wrt mid bowl [mm]'
MARGIN_MM = 1.0

# A small native power value per option, only so that a slot can be built.
SAFE_NATIVE_POWER = {'Amplitude [%]': 1.0, 'Global power [W]': 0.1, 'Voltage [V]': 1.0}


def _combinations(focus_options):
    active_trans = set(get_tran_serials())
    for ds_serial in get_ds_serials():
        ds = DrivingSystem()
        ds.set_ds_info(ds_serial)
        power_option = ds.native_power_params[0]
        if power_option not in SAFE_NATIVE_POWER:
            continue
        for tran_serial in ds.tran_comp:
            if tran_serial not in active_trans:
                continue
            tran = Transducer()
            tran.set_transducer_info(tran_serial)
            if tran.elements > ds.available_ch // ds.max_tran_slots:
                continue
            for focus_option in focus_options:
                if focus_option not in ds.focus_options:
                    continue
                offset = tran.exit_plane_dist if focus_option == MID_BOWL else 0.0
                yield pytest.param(ds_serial, tran_serial, focus_option, power_option,
                                   tran.min_foc + offset, tran.max_foc + offset,
                                   id=f'{ds_serial}-{tran_serial}-{focus_option.split()[2]}')


def _add_slot(ds_serial, tran_serial, focus_option, focus, power_option):
    protocol = TUSProtocol(ds_serial, engineering_mode=True)
    try:
        return protocol.add_slot(tran_serial, focus_option, focus, power_option,
                                 SAFE_NATIVE_POWER[power_option])
    except FDSValidationError as e:
        if 'No active calibration available' in str(e):
            pytest.skip(f'{focus_option} needs a calibration this combination does not have.')
        raise


PARAMETERS = 'ds_serial, tran_serial, focus_option, power_option, lowest, highest'


@pytest.mark.parametrize(PARAMETERS, list(_combinations((EXIT_PLANE, MID_BOWL))))
def test_offered_focus_limits_are_accepted(
        ds_serial, tran_serial, focus_option, power_option, lowest, highest):
    """What the GUI offers as the lowest and highest focus must never be rejected."""
    for focus in (lowest, highest):
        slot = _add_slot(ds_serial, tran_serial, focus_option, focus, power_option)
        assert slot.focus_wrt_exit_plane is not None


@pytest.mark.parametrize(PARAMETERS, list(_combinations((EXIT_PLANE,))))
def test_exit_plane_focus_just_outside_the_limits_is_rejected(
        ds_serial, tran_serial, focus_option, power_option, lowest, highest):
    """The exit-plane limits are exact, so a focus a margin beyond either one must fail."""
    _add_slot(ds_serial, tran_serial, focus_option, lowest, power_option)  # skips w/o calibration
    for focus in (lowest - MARGIN_MM, highest + MARGIN_MM):
        with pytest.raises(FDSValidationError):
            _add_slot(ds_serial, tran_serial, focus_option, focus, power_option)


def test_at_least_one_combination_is_checked():
    """Guards against the parametrization silently turning empty."""
    assert list(_combinations((EXIT_PLANE, MID_BOWL)))
