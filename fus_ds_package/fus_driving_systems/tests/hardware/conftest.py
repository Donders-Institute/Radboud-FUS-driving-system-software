# -*- coding: utf-8 -*-
"""
Fixtures for the hardware tests: they talk to a real IGT or Sonic Concepts driving system, so
they only run when you opt in with two separate things: select them with
`pytest -m hardware --no-cov`, and set the environment variable FDS_HARDWARE_TESTS=1.

SAFETY: meant for a dummy load wired to the driving system, never a real transducer. Every test
keeps its amplitude (IGT) or power (Sonic Concepts) at or below MAX_AMPLITUDE_PERCENT and
MAX_POWER_W, whatever the environment asks for.

Configuration (environment variables, all optional except the first):
    FDS_HARDWARE_TESTS=1            Required, otherwise every hardware test is skipped.

IGT:
    FDS_HW_DRIVING_SYSTEM           Default: IGT-256-ch_comb_1x10-ch (a local-only test setup).
    FDS_HW_TRANSDUCER               The "pretend" transducer selected in software. Default:
                                    IS_PCD15287_01001 (10 elements, matches the 10 channels).
    FDS_HW_FOCUS_MM                 Focus wrt mid bowl [mm] to ask for. Default: 60.
    FDS_HW_AMPLITUDE_PERCENT        Default: 5. Capped at MAX_AMPLITUDE_PERCENT.
    FDS_HW_VOLTAGE_TOLERANCE_PERCENT  How far the measured voltage may be from the calibration's
                                    expected one, in percent (calibration test only). Default: 25,
                                    a starting point to tighten once real measurements exist.

Sonic Concepts (no defaults: a dummy load cannot be selected as a transducer on a TPO, so leave
whichever transducer is selected and name it here, because the TPO answers E2 to a focus outside
that transducer's range):
    FDS_HW_SC_DRIVING_SYSTEM        Required, e.g. 105-010.
    FDS_HW_SC_TRANSDUCER            Required: the transducer currently selected on the TPO.
    FDS_HW_SC_PORT                  Optional COM port, overriding the one in ds_config.ini.
    FDS_HW_SC_POWER_W               Global power in W. Default: 2.5. Capped at MAX_POWER_W.
"""
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import serial

from fus_driving_systems.config import logging_config
from fus_driving_systems.driving_system import get_ds_serials
from fus_driving_systems.exceptions import FDSError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.transducer import Transducer
from fus_driving_systems.tus_protocol import TUSProtocol

HARDWARE_DIR = Path(__file__).parent

MAX_AMPLITUDE_PERCENT = 10
MAX_POWER_W = 5


def pytest_collection_modifyitems(items):
    """Marks everything in this folder as hardware, so none of it can run by accident (the
    default options deselect 'hardware')."""
    for item in items:
        if HARDWARE_DIR in Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.hardware)


@pytest.fixture(scope='session')
def hw_config():
    """The setup under test, read from the environment (see the module docstring)."""
    if os.environ.get('FDS_HARDWARE_TESTS', '').strip() != '1':
        pytest.skip('Set FDS_HARDWARE_TESTS=1 to run the hardware tests.')

    ds_serial = os.environ.get('FDS_HW_DRIVING_SYSTEM', 'IGT-256-ch_comb_1x10-ch')
    if ds_serial not in get_ds_serials():
        pytest.skip(f'Driving system {ds_serial} is not in ds_config.ini. The default is a '
                    'local-only test setup; set FDS_HW_DRIVING_SYSTEM to one that exists.')

    amplitude = float(os.environ.get('FDS_HW_AMPLITUDE_PERCENT', '5'))
    return SimpleNamespace(
        ds_serial=ds_serial,
        transducer=os.environ.get('FDS_HW_TRANSDUCER', 'IS_PCD15287_01001'),
        focus_mm=float(os.environ.get('FDS_HW_FOCUS_MM', '60')),
        amplitude=min(amplitude, MAX_AMPLITUDE_PERCENT),
        max_amplitude=MAX_AMPLITUDE_PERCENT,
        voltage_tolerance_percent=float(os.environ.get('FDS_HW_VOLTAGE_TOLERANCE_PERCENT', '25')),
    )


@pytest.fixture(scope='module')
def igt(hw_config, tmp_path_factory):
    """A connected IGT, shared by one test module and always disconnected afterwards."""
    log_dir = str(tmp_path_factory.mktemp('hardware_logs'))
    driving_sys = IGT(log_dir)
    connect_info = TUSProtocol(hw_config.ds_serial).driving_sys.connect_info
    try:
        driving_sys.connect(connect_info, log_dir, 'hardware_tests')
    except FDSError as e:
        pytest.fail(f'Could not connect to {hw_config.ds_serial}: {e}')

    yield driving_sys

    driving_sys.disconnect()


@pytest.fixture(scope='session')
def sc_config():
    """The Sonic Concepts setup under test. Nothing here has a default on purpose (see the
    module docstring)."""
    if os.environ.get('FDS_HARDWARE_TESTS', '').strip() != '1':
        pytest.skip('Set FDS_HARDWARE_TESTS=1 to run the hardware tests.')

    ds_serial = os.environ.get('FDS_HW_SC_DRIVING_SYSTEM', '').strip()
    transducer = os.environ.get('FDS_HW_SC_TRANSDUCER', '').strip()
    if not ds_serial or not transducer:
        pytest.skip('Set FDS_HW_SC_DRIVING_SYSTEM and FDS_HW_SC_TRANSDUCER (the transducer '
                    'actually selected on the TPO) to run the Sonic Concepts hardware tests.')
    if ds_serial not in get_ds_serials():
        pytest.skip(f'Driving system {ds_serial} is not in ds_config.ini.')

    protocol = TUSProtocol(ds_serial)
    tran = Transducer()
    tran.set_transducer_info(transducer)
    return SimpleNamespace(
        ds_serial=ds_serial,
        transducer=transducer,
        port=os.environ.get('FDS_HW_SC_PORT', '').strip() or protocol.driving_sys.connect_info,
        focus_mm=round((tran.min_foc + tran.max_foc) / 2, 1),
        power_w=min(float(os.environ.get('FDS_HW_SC_POWER_W', '2.5')), MAX_POWER_W),
        max_power_w=MAX_POWER_W,
    )


@pytest.fixture(scope='module')
def sc(sc_config):
    """A connected SonicConcepts, shared by one test module and always disconnected afterwards."""
    driving_sys = SonicConcepts()
    try:
        driving_sys.connect(sc_config.port)
    except (FDSError, serial.SerialException) as e:
        pytest.fail(f'Could not connect to {sc_config.ds_serial} on {sc_config.port}: {e}')

    yield driving_sys

    driving_sys.disconnect()


@pytest.fixture
def make_sc_protocol(sc_config):
    """Builds a one-slot protocol with SC's only power option, Global power (in watt)."""
    def _make(power_w=None, pulse_dur=10, pulse_rep_int=50, pulse_train_dur=200):
        protocol = TUSProtocol(sc_config.ds_serial)
        protocol.add_slot(sc_config.transducer, 'Focus wrt exit plane [mm]', sc_config.focus_mm,
                          'Global power [W]',
                          sc_config.power_w if power_w is None else min(power_w, MAX_POWER_W))
        protocol.configure_timing(pulse_dur=pulse_dur, pulse_rep_int=pulse_rep_int,
                                  pulse_train_dur=pulse_train_dur)
        return protocol
    return _make


@pytest.fixture(autouse=True)
def _stop_anything_still_running(request):
    """A failed test must never leave a driving system firing: abort after every test."""
    yield

    for name in ('igt', 'sc'):
        if name in request.fixturenames:
            try:
                request.getfixturevalue(name).abort()
            except (FDSError, serial.SerialException):
                pass


class _RecordList(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def fds_log():
    """Every record the package logs during a test (the test session's own logger is otherwise
    silent)."""
    logger = logging_config.get_logger()
    handler = _RecordList()
    logger.addHandler(handler)

    yield handler.records

    logger.removeHandler(handler)


@pytest.fixture
def make_protocol(hw_config):
    """Builds a one-slot protocol with native options only (Amplitude and Focus wrt mid bowl,
    which need no calibration). engineering_mode is needed for Amplitude."""
    def _make(pulse_dur=10, amplitude=None, **timing):
        protocol = TUSProtocol(hw_config.ds_serial, engineering_mode=True)
        protocol.add_slot(hw_config.transducer, 'Focus wrt mid bowl [mm]', hw_config.focus_mm,
                          'Amplitude [%]',
                          hw_config.amplitude if amplitude is None else min(
                              amplitude, MAX_AMPLITUDE_PERCENT))
        protocol.configure_timing(pulse_dur=pulse_dur, **timing)
        return protocol
    return _make
