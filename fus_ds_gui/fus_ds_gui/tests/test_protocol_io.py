# -*- coding: utf-8 -*-
"""
Tests for protocol_io, the Planning tab's own thin wrapper around
fus_driving_systems.protocol_loader. Uses the same synthetic 'UNITTEST_*' fixture shape as
test_protocol_builder.py/test_slot_editor.py.
"""
import pytest

from fus_driving_systems import driving_system
from fus_driving_systems.exceptions import FDSSafetyError, FDSValidationError
from fus_driving_systems.tus_protocol import TUSProtocol

from fus_ds_gui.models import protocol_io


def _configure_driving_system(patch_config, serial='UNITTEST_IGT'):
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '4')
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '2')
    patch_config.set(section, 'Active?', 'True')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')


@pytest.fixture
def protocol(patch_config):
    _configure_driving_system(patch_config)
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    tus_protocol = TUSProtocol('UNITTEST_IGT')
    tus_protocol.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 40,
                          'Max. pressure in free water [MPa]', 0.5)
    return tus_protocol


def test_save_then_load_round_trips_the_protocol(tmp_path, protocol):
    path = str(tmp_path / 'protocol.yaml')

    protocol_io.save(protocol, path)
    result = protocol_io.load(path)

    assert result.protocol.driving_sys.serial == 'UNITTEST_IGT'
    assert len(result.protocol.slots) == 1
    assert result.protocol.slots[0].focus_wrt_exit_plane == 40
    assert result.protocol.slots[0].press == 0.5
    assert result.failed_slots == []


def test_approve_writes_a_hash_sidecar(tmp_path, protocol):
    path = str(tmp_path / 'protocol.yaml')
    protocol_io.save(protocol, path)

    protocol_io.approve(path)

    assert (tmp_path / 'protocol.yaml.sha256').exists()


def test_load_recovers_a_slot_exceeding_the_safety_limit(tmp_path, patch_config):
    """A slot whose own power value exceeds the configured safety limit (see
    get_max_pressure()) doesn't abort the whole file: it's skipped, and its own raw slot_def
    plus the FDSSafetyError that stopped it are returned in failed_slots instead, while timing
    (and, in test_load_recovers_only_the_failing_slot_below, every other slot) still loads."""
    _configure_driving_system(patch_config)
    path = tmp_path / 'protocol.yaml'
    path.write_text("""
driving_sys_serial: UNITTEST_IGT
protocols:
  - slots:
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 40
        power_option: Max. pressure in free water [MPa]
        power_value: 2
    timing:
      pulse_dur: 10
""", encoding='utf-8')

    result = protocol_io.load(str(path))

    assert result.protocol.slots == []
    assert result.protocol.pulse_dur == 10
    assert len(result.failed_slots) == 1
    failed_slot_def, exc = result.failed_slots[0]
    assert failed_slot_def['power_value'] == 2
    assert isinstance(exc, FDSSafetyError)


def test_load_recovers_only_the_failing_slot(tmp_path, patch_config):
    """A second, valid slot must still load normally alongside the one that failed."""
    _configure_driving_system(patch_config)  # Max. transducer slots = 2, per its own default.
    path = tmp_path / 'protocol.yaml'
    path.write_text("""
driving_sys_serial: UNITTEST_IGT
protocols:
  - slots:
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 40
        power_option: Max. pressure in free water [MPa]
        power_value: 2
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 50
        power_option: Max. pressure in free water [MPa]
        power_value: 0.5
    timing:
      pulse_dur: 10
""", encoding='utf-8')

    result = protocol_io.load(str(path))

    assert len(result.protocol.slots) == 1
    assert result.protocol.slots[0].focus_wrt_exit_plane == 50
    assert len(result.failed_slots) == 1
    assert result.failed_slots[0][0]['focus_value'] == 40


def test_load_rejects_an_interleaved_file(tmp_path, patch_config):
    """protocol_io.load() is the Planning tab's own single-protocol entry point; an interleaved
    file must be refused outright, never silently reduced to its own first protocol (see this
    module's own docstring)."""
    _configure_driving_system(patch_config)
    path = tmp_path / 'interleaved.yaml'
    path.write_text("""
driving_sys_serial: UNITTEST_IGT
protocols:
  - slots:
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 40
        power_option: Max. pressure in free water [MPa]
        power_value: 0.5
    timing:
      pulse_dur: 10
  - slots:
      - transducer_serial: UNITTEST_TRAN
        focus_option: Focus wrt exit plane [mm]
        focus_value: 50
        power_option: Max. pressure in free water [MPa]
        power_value: 0.5
    timing:
      pulse_dur: 10
""", encoding='utf-8')

    with pytest.raises(FDSValidationError, match='interleaved'):
        protocol_io.load(str(path))
