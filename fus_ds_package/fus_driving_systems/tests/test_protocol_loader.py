# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.protocol_loader.load_protocol().

Every test uses real, shipped config values (driving system 'IGT-32-ch_comb_2x10-ch',
transducers 'IS_PCD15287_01001'/'IS_PCD15287_01002') rather than mocks -- load_protocol() is a
thin translation layer over TUSProtocol/add_slot()/configure_timing(), which already validate
everything semantic (unknown serials, invalid options, out-of-range values) with their own clear
sys.exit() messages; these tests confirm load_protocol() delegates to those unchanged, and only
adds its own validation for the YAML file's own structure (required keys, unknown/typo'd keys).
"""
import pytest

from fus_driving_systems.protocol_loader import load_protocol

DS_SERIAL = 'IGT-32-ch_comb_2x10-ch'
TRANSDUCER_1 = 'IS_PCD15287_01001'
TRANSDUCER_2 = 'IS_PCD15287_01002'
FOCUS_OPTION = 'Focus wrt exit plane [mm]'
POWER_OPTION = 'Max. pressure in free water [MPa]'


def _write_yaml(tmp_path, content, name='protocol.yaml'):
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return str(path)


def _single_protocol_yaml(extra_slot_lines='', extra_timing_lines=''):
    return f"""
driving_sys_serial: {DS_SERIAL}
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
            extra_timing_lines=('pulse_rep_int: 100\n      trigger_option: '
                                'TriggerWholeProtocol')))

        protocols, duration = load_protocol(path)

        assert len(protocols) == 1
        assert duration is None
        assert len(protocols[0].slots) == 1
        assert protocols[0].slots[0].press == 0.5
        assert protocols[0].pulse_dur == 45
        assert protocols[0].pulse_rep_int == 100
        assert protocols[0].trigger_option == 'TriggerWholeProtocol'

    def test_optional_slot_and_timing_fields_omitted_fall_back_to_library_defaults(
            self, tmp_path):
        """oper_freq/dephasing_degree (slot) and every timing field but pulse_dur are optional
        -- omitting them entirely (not even null) must flow through to add_slot()/
        configure_timing()'s own cascade defaults, not raise."""
        path = _write_yaml(tmp_path, _single_protocol_yaml())

        protocols, duration = load_protocol(path)

        assert duration is None
        # pulse_rep_int defaults to pulse_dur, pulse_train_dur to pulse_rep_int, etc.
        assert protocols[0].pulse_rep_int == 45
        assert protocols[0].pulse_train_dur == 45

    def test_loads_multiple_protocols_and_returns_total_alternating_duration_ms(self, tmp_path):
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
      pulse_dur: 45
      pulse_rep_int: 100
      trigger_option: TriggerWholeProtocol
  - slots:
      - transducer_serial: {TRANSDUCER_2}
        focus_option: {FOCUS_OPTION}
        focus_value: 80
        power_option: {POWER_OPTION}
        power_value: 0.5
    timing:
      pulse_dur: 45
      pulse_rep_int: 150
      trigger_option: TriggerWholeProtocol
total_alternating_duration_ms: 80000
""")

        protocols, duration = load_protocol(path)

        assert len(protocols) == 2
        assert duration == 80000
        assert protocols[0].pulse_rep_int == 100
        assert protocols[1].pulse_rep_int == 150

    def test_engineering_mode_python_parameter_reaches_every_protocol(self, tmp_path):
        """engineering_mode is deliberately not a file field -- confirm the Python-level
        parameter actually reaches TUSProtocol, by using an engineering-only power option
        ('Voltage [V]') that would otherwise raise RuntimeError."""
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

        protocols, _ = load_protocol(path, engineering_mode=True)

        assert protocols[0].slots[0].volt == [5]


class TestFileErrors:

    def test_exits_when_file_missing(self, tmp_path):
        with pytest.raises(SystemExit):
            load_protocol(str(tmp_path / 'does_not_exist.yaml'))

    def test_exits_when_yaml_malformed(self, tmp_path):
        path = _write_yaml(tmp_path, 'driving_sys_serial: [unclosed')

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_top_level_is_not_a_mapping(self, tmp_path):
        path = _write_yaml(tmp_path, '- just\n- a\n- list\n')

        with pytest.raises(SystemExit):
            load_protocol(path)


class TestMissingRequiredKeys:

    def test_exits_when_driving_sys_serial_missing(self, tmp_path):
        path = _write_yaml(tmp_path, 'protocols: []\n')

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_protocols_key_missing(self, tmp_path):
        path = _write_yaml(tmp_path, f'driving_sys_serial: {DS_SERIAL}\n')

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_protocols_is_empty(self, tmp_path):
        path = _write_yaml(tmp_path, f'driving_sys_serial: {DS_SERIAL}\nprotocols: []\n')

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_slots_key_missing_from_protocol(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - timing:
      pulse_dur: 45
""")

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_timing_key_missing_from_protocol(self, tmp_path):
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

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_slot_missing_a_required_field(self, tmp_path):
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

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_timing_missing_pulse_dur(self, tmp_path):
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

        with pytest.raises(SystemExit):
            load_protocol(path)


class TestUnknownKeys:

    def test_exits_when_top_level_has_an_unknown_key(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols: []
some_typo: 1
""")

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_protocol_has_an_unknown_key(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots: []
    timing: {{}}
    some_typo: 1
""")

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_slot_has_an_unknown_key(self, tmp_path):
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

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_timing_has_a_typo_d_key(self, tmp_path):
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

        with pytest.raises(SystemExit):
            load_protocol(path)

    @pytest.mark.parametrize('yaml_snippet', [
        'driving_sys_serial: {ds}\nengineering_mode: true\nprotocols: []\n',
        ('driving_sys_serial: {ds}\nprotocols:\n  - slots: []\n    timing: {{}}\n    '
         'engineering_mode: true\n'),
    ])
    def test_exits_with_dedicated_message_when_engineering_mode_is_a_file_field(
            self, tmp_path, yaml_snippet):
        """engineering_mode is deliberately not a file field anywhere in this schema (top-level
        or per-protocol) -- a researcher adding it should get a message pointing at the correct
        Python-level parameter, not the generic 'unknown key' message."""
        path = _write_yaml(tmp_path, yaml_snippet.format(ds=DS_SERIAL))

        with pytest.raises(SystemExit) as exc_info:
            load_protocol(path)

        assert 'engineering_mode' in str(exc_info.value)
        assert 'load_protocol' in str(exc_info.value)


class TestStructuralTypeErrors:

    def test_exits_when_protocols_is_not_a_list(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  slots: []
  timing: {{}}
""")

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_slots_is_not_a_list(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      transducer_serial: {TRANSDUCER_1}
    timing:
      pulse_dur: 45
""")

        with pytest.raises(SystemExit):
            load_protocol(path)

    def test_exits_when_a_slot_entry_is_not_a_mapping(self, tmp_path):
        path = _write_yaml(tmp_path, f"""
driving_sys_serial: {DS_SERIAL}
protocols:
  - slots:
      - {TRANSDUCER_1}
    timing:
      pulse_dur: 45
""")

        with pytest.raises(SystemExit):
            load_protocol(path)


class TestDelegatedSemanticValidation:
    """load_protocol() must not re-implement any of this -- TUSProtocol/add_slot() already
    sys.exit() clearly. These tests confirm the existing library messages surface unchanged,
    proving load_protocol() doesn't swallow or double-validate them."""

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

        with pytest.raises(SystemExit) as exc_info:
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

        with pytest.raises(SystemExit) as exc_info:
            load_protocol(path)

        assert 'NOT-A-REAL-TRANSDUCER' in str(exc_info.value)

    def test_engineering_only_power_option_without_engineering_mode_surfaces_the_existing_error(
            self, tmp_path):
        """Unlike most other TUSProtocol/add_slot() validation failures (sys.exit()),
        engineering-mode violations specifically raise RuntimeError -- confirm load_protocol()
        lets that propagate unchanged too, rather than converting or swallowing it."""
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

        with pytest.raises(RuntimeError) as exc_info:
            load_protocol(path)

        assert 'engineering_mode' in str(exc_info.value).lower()
