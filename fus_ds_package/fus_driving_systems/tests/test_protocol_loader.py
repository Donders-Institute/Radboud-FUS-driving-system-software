# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.protocol_loader.load_protocol().

Every test uses real, shipped config values (driving system 'IGT-32-ch_comb_2x10-ch',
transducers 'IS_PCD15287_01001'/'IS_PCD15287_01002') rather than mocks -- load_protocol() is a
thin translation layer over TUSProtocol/add_slot()/configure_timing(), which already validate
everything semantic (unknown serials, invalid options, out-of-range values) by raising their own
clear FDSValidationError; these tests confirm load_protocol() delegates to those unchanged, and
only adds its own validation for the YAML file's own structure (required keys, unknown/typo'd
keys).
"""
import hashlib
import pathlib

import pytest

from fus_driving_systems.exceptions import FDSSafetyError, FDSValidationError
from fus_driving_systems.protocol_loader import approve_protocol, load_protocol, save_protocol

DS_SERIAL = 'IGT-32-ch_comb_2x10-ch'
TRANSDUCER_1 = 'IS_PCD15287_01001'
TRANSDUCER_2 = 'IS_PCD15287_01002'
FOCUS_OPTION = 'Focus wrt exit plane [mm]'
POWER_OPTION = 'Max. pressure in free water [MPa]'

# fus_ds_package/fus_driving_systems/tests/ -> repo root -> example_protocols/
_EXAMPLE_PROTOCOLS_DIR = pathlib.Path(__file__).resolve().parents[3] / 'example_protocols'
_SHIPPED_EXAMPLE_YAML_FILES = sorted(_EXAMPLE_PROTOCOLS_DIR.rglob('*.yaml'))


def _write_yaml(tmp_path, content, name='protocol.yaml'):
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return str(path)


def _single_protocol_yaml(extra_slot_lines='', extra_timing_lines='', extra_top_level_lines=''):
    return f"""
driving_sys_serial: {DS_SERIAL}
{extra_top_level_lines}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
        {extra_slot_lines}
    timing:
      pulse_dur: 45
      {extra_timing_lines}
"""


class TestValidFiles:

    def test_loads_single_protocol_with_all_fields(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml(
            extra_slot_lines='oper_freq: 300\n        dephasing_degree: null',
            extra_timing_lines='pulse_rep_int: 100',
            extra_top_level_lines=('trigger_option: TriggerWholeProtocol\n'
                                   'n_triggers: 1\nbuffer_num: 0')))

        protocols, duration, trigger_option, n_triggers, buffer_num = load_protocol(path)

        assert len(protocols) == 1
        assert duration is None
        assert len(protocols[0].slots) == 1
        assert protocols[0].slots[0].press == 0.5
        assert protocols[0].pulse_dur == 45
        assert protocols[0].pulse_rep_int == 100
        assert trigger_option == 'TriggerWholeProtocol'
        assert n_triggers == 1
        assert buffer_num == 0

    def test_optional_slot_and_timing_fields_omitted_fall_back_to_library_defaults(
            self, tmp_path):
        """oper_freq/dephasing_degree (slot) and every timing field but pulse_dur are optional
        -- omitting them entirely (not even null) must flow through to add_slot()/
        configure_timing()'s own cascade defaults, not raise. trigger_option/n_triggers/
        buffer_num are also optional at the top level -- omitting them must not raise either."""
        path = _write_yaml(tmp_path, _single_protocol_yaml())

        protocols, duration, trigger_option, n_triggers, buffer_num = load_protocol(path)

        assert duration is None
        # pulse_rep_int defaults to pulse_dur, pulse_train_dur to pulse_rep_int, etc.
        assert protocols[0].pulse_rep_int == 45
        assert protocols[0].pulse_train_dur == 45
        assert trigger_option is None
        assert n_triggers is None
        assert buffer_num == 0

    def test_loads_multiple_protocols_and_returns_total_alternating_duration_ms(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
trigger_option: TriggerWholeProtocol
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_dur: 45
      pulse_rep_int: 100
  - slots:
      - transducer_serial: {TRANSDUCER_2}
        focus_option: {FOCUS_OPTION}
        focus_value: 80
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_dur: 45
      pulse_rep_int: 150
total_alternating_duration_ms: 80000
""")

        protocols, duration, trigger_option, *_ = load_protocol(path)

        assert len(protocols) == 2
        assert duration == 80000
        assert trigger_option == 'TriggerWholeProtocol'
        assert protocols[0].pulse_rep_int == 100
        assert protocols[1].pulse_rep_int == 150

    def test_engineering_mode_python_parameter_reaches_every_protocol(self, tmp_path):
        """engineering_mode is deliberately not a file field -- confirm the Python-level
        parameter actually reaches TUSProtocol, by using an engineering-only power option
        ('Voltage [V]') that would otherwise raise FDSValidationError."""
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: Voltage [V]
        power_value: 5
    timing:
      pulse_dur: 45
""")

        protocols, *_ = load_protocol(path, engineering_mode=True)

        assert protocols[0].slots[0].volt == [5]


class TestFileErrors:

    def test_raises_when_file_missing(self, tmp_path):
        with pytest.raises(FDSValidationError):
            load_protocol(str(tmp_path / 'does_not_exist.yaml'))

    def test_raises_when_yaml_malformed(self, tmp_path):
        path = _write_yaml(tmp_path, 'driving_sys_serial: [unclosed')

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_top_level_is_not_a_mapping(self, tmp_path):
        path = _write_yaml(tmp_path, '- just\n- a\n- list\n')

        with pytest.raises(FDSValidationError):
            load_protocol(path)


class TestMissingRequiredKeys:

    def test_raises_when_driving_sys_serial_missing(self, tmp_path):
        path = _write_yaml(tmp_path, 'protocols: []\n')

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_protocols_key_missing(self, tmp_path):
        path = _write_yaml(tmp_path, f'driving_sys_serial: {DS_SERIAL}\n')

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_protocols_is_empty(self, tmp_path):
        path = _write_yaml(tmp_path, f'driving_sys_serial: {DS_SERIAL}\nprotocols: []\n')

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_slots_key_missing_from_protocol(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_timing_key_missing_from_protocol(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_slot_missing_a_required_field(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_timing_missing_pulse_dur(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_rep_int: 100
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)


class TestUnknownKeys:

    def test_raises_when_top_level_has_an_unknown_key(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols: []
some_typo: 1
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_protocol_has_an_unknown_key(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots: []
    timing: {{}}
    some_typo: 1
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_slot_has_an_unknown_key(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
        some_typo: 1
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_timing_has_a_typo_d_key(self, tmp_path):
        """puls_dur (missing the 'e') is exactly the class of mistake this check exists for --
        without it, a typo'd optional-looking key would silently do nothing instead of erroring,
        since every optional field is read via .get()."""
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      puls_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    @pytest.mark.parametrize('yaml_snippet', [
        'driving_sys_serial: {ds}\nengineering_mode: true\nprotocols: []\n',
        ('driving_sys_serial: {ds}\nprotocols:\n  - slots: []\n    timing: {{}}\n    '
         'engineering_mode: true\n'),
    ])
    def test_raises_with_dedicated_message_when_engineering_mode_is_a_file_field(
            self, tmp_path, yaml_snippet):
        """engineering_mode is deliberately not a file field anywhere in this schema (top-level
        or per-protocol) -- a researcher adding it should get a message pointing at the correct
        Python-level parameter, not the generic 'unknown key' message."""
        path = _write_yaml(tmp_path, yaml_snippet.format(ds=DS_SERIAL))

        with pytest.raises(FDSValidationError) as exc_info:
            load_protocol(path)

        assert 'engineering_mode' in str(exc_info.value)
        assert 'load_protocol' in str(exc_info.value)


class TestStructuralTypeErrors:

    def test_raises_when_protocols_is_not_a_list(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  slots: []
  timing: {{}}
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_slots_is_not_a_list(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      transducer_serial: {TRANSDUCER_1}
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)

    def test_raises_when_a_slot_entry_is_not_a_mapping(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - {TRANSDUCER_1}
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError):
            load_protocol(path)


class TestDelegatedSemanticValidation:
    """load_protocol() must not re-implement any of this -- TUSProtocol/add_slot() already raise
    FDSValidationError clearly. These tests confirm the existing library messages surface
    unchanged, proving load_protocol() doesn't swallow or double-validate them."""

    def test_unknown_driving_sys_serial_surfaces_the_existing_library_message(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: NOT-A-REAL-SERIAL
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError) as exc_info:
            load_protocol(path)

        assert 'NOT-A-REAL-SERIAL' in str(exc_info.value)

    def test_unknown_transducer_serial_surfaces_the_existing_library_message(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: NOT-A-REAL-TRANSDUCER
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError) as exc_info:
            load_protocol(path)

        assert 'NOT-A-REAL-TRANSDUCER' in str(exc_info.value)

    def test_engineering_only_power_option_without_engineering_mode_surfaces_the_existing_error(
            self, tmp_path):
        """Confirm load_protocol() lets TUSProtocol/add_slot()'s engineering-mode violation
        propagate unchanged, rather than converting or swallowing it."""
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: Voltage [V]
        power_value: 5
    timing:
      pulse_dur: 45
""")

        with pytest.raises(FDSValidationError) as exc_info:
            load_protocol(path)

        assert 'engineering_mode' in str(exc_info.value).lower()


class TestHashProtection:
    """Hash/sidecar protection is opt-in by default -- a sidecar '<path>.sha256' only ever
    exists if approve_protocol() was explicitly run on that file. require_hash=True (tested
    separately below) is the one way a calling script can insist a sidecar must exist."""

    def test_loads_normally_with_no_sidecar_present(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())

        protocols, *_ = load_protocol(path)

        assert len(protocols) == 1

    def test_loads_normally_when_sidecar_hash_matches(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())
        approve_protocol(path)

        protocols, *_ = load_protocol(path)

        assert len(protocols) == 1

    def test_raises_when_file_edited_after_approval(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())
        approve_protocol(path)

        # Simulate an accidental edit after approval -- change the focal depth.
        edited = _single_protocol_yaml().replace('focus_value: 40', 'focus_value: 41')
        _write_yaml(tmp_path, edited)

        with pytest.raises(FDSSafetyError) as exc_info:
            load_protocol(path)

        assert path in str(exc_info.value)
        assert 'approve_protocol' in str(exc_info.value)

    def test_approve_protocol_raises_when_file_missing(self, tmp_path):
        """Must raise a catchable FDSValidationError, not a raw OSError/FileNotFoundError,
        matching load_protocol()'s own file-read error handling."""
        missing_path = str(tmp_path / 'does_not_exist.yaml')

        with pytest.raises(FDSValidationError, match='Could not read protocol file'):
            approve_protocol(missing_path)

    def test_approve_protocol_writes_sidecar_matching_real_sha256sum_format(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())

        approve_protocol(path)

        with open(path, 'rb') as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()
        sidecar_path = f'{path}.sha256'
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            sidecar_contents = f.read()

        assert sidecar_contents == f'{expected_hash}  {path}\n'

    def test_approve_then_edit_then_reapprove_then_load_succeeds(self, tmp_path):
        """The realistic workflow: approve, make a legitimate edit, re-approve, load again --
        must not raise, since the sidecar now reflects the current, intentional content."""
        path = _write_yaml(tmp_path, _single_protocol_yaml())
        approve_protocol(path)

        edited = _single_protocol_yaml().replace('focus_value: 40', 'focus_value: 41')
        _write_yaml(tmp_path, edited)
        approve_protocol(path)

        protocols, *_ = load_protocol(path)

        assert protocols[0].slots[0].focus_wrt_exit_plane == 41


class TestRequireHash:
    """require_hash=True is a Python-level parameter a calling script sets to insist a protocol
    file must already be approved -- unlike the default (opt-in only when a sidecar happens to
    exist), a missing sidecar itself becomes an error."""

    def test_raises_when_require_hash_true_and_no_sidecar_present(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())

        with pytest.raises(FDSSafetyError) as exc_info:
            load_protocol(path, require_hash=True)

        assert path in str(exc_info.value)
        assert 'approve_protocol' in str(exc_info.value)

    def test_loads_normally_when_require_hash_true_and_sidecar_matches(self, tmp_path):
        path = _write_yaml(tmp_path, _single_protocol_yaml())
        approve_protocol(path)

        protocols, *_ = load_protocol(path, require_hash=True)

        assert len(protocols) == 1

    def test_raises_when_require_hash_true_and_sidecar_mismatched(self, tmp_path):
        """A stale (mismatched) sidecar is still reported as an edited-since-approval mismatch,
        not as if no sidecar existed at all -- require_hash doesn't change that message."""
        path = _write_yaml(tmp_path, _single_protocol_yaml())
        approve_protocol(path)

        edited = _single_protocol_yaml().replace('focus_value: 40', 'focus_value: 41')
        _write_yaml(tmp_path, edited)

        with pytest.raises(FDSSafetyError) as exc_info:
            load_protocol(path, require_hash=True)

        assert 'edited since it was last approved' in str(exc_info.value)


class TestSaveProtocol:
    """save_protocol() is load_protocol()'s own inverse for the single-protocol case: every test
    here saves a protocol built one way, reloads it, and checks the reload reproduces the same
    protocol, rather than inspecting the written YAML's own text directly."""

    def test_round_trip_reproduces_a_multi_slot_protocol(self, tmp_path):
        original_path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
trigger_option: TriggerWholeProtocol
n_triggers: 3
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: {POWER_OPTION}
        power_value: 0.5
        oper_freq: 300
        dephasing_degree: [90]
      - transducer_serial: {TRANSDUCER_2}
        focus_option: {FOCUS_OPTION}
        focus_value: 60
        power_option: {POWER_OPTION}
        power_value: 0.3
    timing:
      pulse_dur: 10
      pulse_ramp_shape: Linear
      pulse_ramp_dur: 1
      pulse_rep_int: 50
      pulse_train_dur: 200
      pulse_train_rep_int: 400
      pulse_train_rep_dur: 2
""", name='original.yaml')
        original, _, trigger_option, n_triggers, buffer_num = load_protocol(original_path)

        saved_path = str(tmp_path / 'saved.yaml')
        save_protocol(original[0], saved_path, trigger_option=trigger_option,
                      n_triggers=n_triggers, buffer_num=buffer_num)
        reloaded, duration, reloaded_trigger_option, reloaded_n_triggers, reloaded_buffer_num = (
            load_protocol(saved_path))

        assert duration is None
        assert reloaded_trigger_option == 'TriggerWholeProtocol'
        assert reloaded_n_triggers == 3
        assert reloaded_buffer_num == 0
        reloaded_protocol = reloaded[0]
        assert reloaded_protocol.pulse_dur == 10
        assert reloaded_protocol.pulse_ramp_shape == 'Linear'
        assert reloaded_protocol.pulse_ramp_dur == 1
        assert reloaded_protocol.pulse_rep_int == 50
        assert reloaded_protocol.pulse_train_dur == 200
        assert reloaded_protocol.pulse_train_rep_int == 400
        assert reloaded_protocol.pulse_train_rep_dur == 2000  # stored internally in ms
        assert len(reloaded_protocol.slots) == 2
        assert reloaded_protocol.slots[0].transducer.serial == TRANSDUCER_1
        assert reloaded_protocol.slots[0].focus_wrt_exit_plane == 40
        assert reloaded_protocol.slots[0].press == 0.5
        assert reloaded_protocol.slots[0].oper_freq == 300
        assert reloaded_protocol.slots[0].dephasing_degree == [90]
        assert reloaded_protocol.slots[1].transducer.serial == TRANSDUCER_2
        assert reloaded_protocol.slots[1].focus_wrt_exit_plane == 60
        assert reloaded_protocol.slots[1].dephasing_degree is None

    def test_round_trip_preserves_a_list_valued_power_value(self, tmp_path):
        """'Voltage [V]' (engineering-only) stores its value as list(float), unlike the plain
        float 'Max. pressure in free water [MPa]' every other test in this class uses."""
        original_path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - transducer_serial: {TRANSDUCER_1}
        focus_option: {FOCUS_OPTION}
        focus_value: 40
        power_option: Voltage [V]
        power_value: 5
    timing:
      pulse_dur: 10
""")
        original, *_ = load_protocol(original_path, engineering_mode=True)

        saved_path = str(tmp_path / 'saved.yaml')
        save_protocol(original[0], saved_path)
        reloaded, *_ = load_protocol(saved_path, engineering_mode=True)

        assert reloaded[0].slots[0].volt == [5]

    def test_round_trip_preserves_an_xyz_focus_value(self, tmp_path):
        """(x, y, z) focus values are tuples on TransducerSlot itself (see
        chosen_focus_value's own docstring); yaml.safe_dump has no representer for tuple, so
        _dump_slot() must convert it to a list first. The mid-bowl xyz option, not the exit-
        plane one: the latter needs an active calibration combo to convert, which this
        synthetic (driving system, transducer) pair doesn't have."""
        original_path = _write_yaml(tmp_path, """
driving_sys_serial: IGT-256-ch_comb_1x52-ch
protocols:
  - slots:
      - transducer_serial: Clover_1
        focus_option: Focus xyz wrt mid bowl [mm]
        focus_value: [1, 2, 60]
        power_option: Amplitude [%]
        power_value: 30
    timing:
      pulse_dur: 10
""")
        original, *_ = load_protocol(original_path, engineering_mode=True)

        saved_path = str(tmp_path / 'saved.yaml')
        save_protocol(original[0], saved_path)
        reloaded, *_ = load_protocol(saved_path, engineering_mode=True)

        slot = reloaded[0].slots[0]
        assert slot.focus_offset_x == 1
        assert slot.focus_offset_y == 2
        assert slot.focus_wrt_mid_bowl == 60

    def test_saves_a_nonzero_buffer_num(self, tmp_path):
        original_path = _write_yaml(tmp_path, _single_protocol_yaml())
        original, *_ = load_protocol(original_path)

        saved_path = str(tmp_path / 'saved.yaml')
        save_protocol(original[0], saved_path, buffer_num=2)
        *_, buffer_num = load_protocol(saved_path)

        assert buffer_num == 2

    def test_raises_when_protocol_has_no_slots(self, tmp_path):
        """Fails at save time rather than only on a later, separate load attempt: load_protocol()
        would reject an empty 'slots: []' the same way, but only once someone actually tries to
        load the file back."""
        from fus_driving_systems.tus_protocol import TUSProtocol

        empty_protocol = TUSProtocol(DS_SERIAL)

        with pytest.raises(FDSValidationError, match='no transducer slots'):
            save_protocol(empty_protocol, str(tmp_path / 'empty.yaml'))

    def test_raises_when_yaml_path_cannot_be_written(self, tmp_path):
        """A nonexistent parent directory (or a permissions error, same OSError family) must
        raise a catchable FDSValidationError, mirroring load_protocol()'s own file-read
        error handling, not propagate a raw OSError/FileNotFoundError."""
        original_path = _write_yaml(tmp_path, _single_protocol_yaml())
        original, *_ = load_protocol(original_path)
        unwritable_path = str(tmp_path / 'does' / 'not' / 'exist' / 'saved.yaml')

        with pytest.raises(FDSValidationError, match='Could not write protocol file'):
            save_protocol(original[0], unwritable_path)


class TestShippedExampleFiles:
    """Regression net against config drift: every protocol.yaml shipped under
    example_protocols/ must keep loading successfully against the real, current ds_config.ini.
    A renamed/removed focus or power option, for instance, would otherwise only surface once a
    researcher copies one of these files and hits it themselves."""

    @pytest.mark.parametrize(
        'yaml_path', _SHIPPED_EXAMPLE_YAML_FILES,
        ids=[str(p.relative_to(_EXAMPLE_PROTOCOLS_DIR)) for p in _SHIPPED_EXAMPLE_YAML_FILES])
    def test_shipped_example_loads_successfully(self, yaml_path):
        protocols, *_ = load_protocol(str(yaml_path))

        assert len(protocols) >= 1
