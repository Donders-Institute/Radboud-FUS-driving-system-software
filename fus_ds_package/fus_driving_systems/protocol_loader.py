# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Margely Cornelissen, Stein Fekkes (Radboud University) and Erik Dumont (Image
Guided Therapy)

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

**Attribution Notice**:
If you use this kit in your research or project, please refer to the 'How to Cite' section in the
README.md file of https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basic packages
import sys

import yaml

# Own packages
from fus_driving_systems.tus_protocol import TUSProtocol
from fus_driving_systems.config.logging_config import get_logger


_REQUIRED_TOP_LEVEL_KEYS = ('driving_sys_serial', 'protocols')
_OPTIONAL_TOP_LEVEL_KEYS = ('total_alternating_duration_ms',)

_REQUIRED_PROTOCOL_KEYS = ('slots', 'timing')

_REQUIRED_SLOT_KEYS = ('transducer_serial', 'focus_option', 'focus_value', 'power_option',
                       'power_value')
_OPTIONAL_SLOT_KEYS = ('oper_freq', 'dephasing_degree')

_REQUIRED_TIMING_KEYS = ('pulse_dur',)
_OPTIONAL_TIMING_KEYS = ('pulse_rep_int', 'pulse_train_dur', 'trigger_option',
                         'pulse_ramp_shape', 'pulse_ramp_dur', 'n_triggers',
                         'pulse_train_rep_int', 'pulse_train_rep_dur')


def _require_mapping(value, context):
    """Returns value, or exits if it isn't a mapping (dict) -- e.g. a researcher wrote a list or
    a bare scalar where key: value pairs were expected."""

    if not isinstance(value, dict):
        message = f'{context} must be a mapping (key: value pairs), got {type(value).__name__}.'
        get_logger().critical(message)
        sys.exit(message)

    return value


def _require_list(value, context):
    """Returns value, or exits if it isn't a non-empty list."""

    if not isinstance(value, list) or not value:
        message = f'{context} must be a non-empty list.'
        get_logger().critical(message)
        sys.exit(message)

    return value


def _require_key(mapping, key, context):
    """Returns mapping[key], or exits with a clear message naming the missing key and context."""

    if key not in mapping:
        message = f"Missing required key '{key}' in {context}."
        get_logger().critical(message)
        sys.exit(message)

    return mapping[key]


def _reject_unknown_keys(mapping, known_keys, context):
    """Exits if mapping has any key outside known_keys -- catches a typo'd key immediately
    (e.g. 'puls_dur'), rather than it silently doing nothing, since every optional key is read
    via .get() elsewhere. Also flags a literal 'engineering_mode' key with a dedicated message:
    it's deliberately not a file field anywhere in this schema, only a Python-level
    load_protocol() parameter, so a researcher adding it here would otherwise get a generic
    "unknown key" message that doesn't explain why."""

    if 'engineering_mode' in mapping:
        message = ("'engineering_mode' is not a protocol-file field -- set it as a Python-level "
                   "parameter instead: load_protocol(yaml_path, engineering_mode=True).")
        get_logger().critical(message)
        sys.exit(message)

    unknown = set(mapping) - set(known_keys)
    if unknown:
        message = (f'Unknown key(s) {sorted(unknown)} in {context} -- check for typos. ' +
                   f'Expected one of: {sorted(known_keys)}.')
        get_logger().critical(message)
        sys.exit(message)


def _build_slot(protocol, slot_def, slot_index, protocol_index):
    """Adds one slot to protocol, described by slot_def (one entry of a protocol's own 'slots'
    list)."""

    context = f'protocols[{protocol_index}].slots[{slot_index}]'
    slot_def = _require_mapping(slot_def, context)
    _reject_unknown_keys(slot_def, _REQUIRED_SLOT_KEYS + _OPTIONAL_SLOT_KEYS, context)

    transducer_serial = _require_key(slot_def, 'transducer_serial', context)
    focus_option = _require_key(slot_def, 'focus_option', context)
    focus_value = _require_key(slot_def, 'focus_value', context)
    power_option = _require_key(slot_def, 'power_option', context)
    power_value = _require_key(slot_def, 'power_value', context)

    protocol.add_slot(transducer_serial, focus_option, focus_value, power_option, power_value,
                      oper_freq=slot_def.get('oper_freq'),
                      dephasing_degree=slot_def.get('dephasing_degree'))


def _configure_timing(protocol, timing_def, protocol_index):
    """Applies one protocol's 'timing' mapping via configure_timing()."""

    context = f'protocols[{protocol_index}].timing'
    timing_def = _require_mapping(timing_def, context)
    _reject_unknown_keys(timing_def, _REQUIRED_TIMING_KEYS + _OPTIONAL_TIMING_KEYS, context)

    pulse_dur = _require_key(timing_def, 'pulse_dur', context)

    protocol.configure_timing(
        pulse_dur,
        pulse_rep_int=timing_def.get('pulse_rep_int'),
        pulse_train_dur=timing_def.get('pulse_train_dur'),
        trigger_option=timing_def.get('trigger_option'),
        pulse_ramp_shape=timing_def.get('pulse_ramp_shape'),
        pulse_ramp_dur=timing_def.get('pulse_ramp_dur'),
        n_triggers=timing_def.get('n_triggers'),
        pulse_train_rep_int=timing_def.get('pulse_train_rep_int'),
        pulse_train_rep_dur=timing_def.get('pulse_train_rep_dur'),
    )


def load_protocol(yaml_path, engineering_mode=False):
    """
    Parses a YAML protocol-definition file into ready-to-use TUSProtocol object(s).

    engineering_mode is deliberately a Python-level parameter here, not a YAML field -- it must
    be set by editing the calling script, never the YAML file a researcher edits.

    Semantic validation (unknown driving-system/transducer serial, invalid focus/power/trigger
    option, out-of-range timing value) is not duplicated here -- TUSProtocol/add_slot()/
    configure_timing() already exit with a clear message for all of these. This function only
    validates the file's own structure: required keys present, no typo'd/unknown keys.

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file.
        engineering_mode (bool): Passed straight to every TUSProtocol this file describes.

    Returns:
        tuple(list(TUSProtocol), float or None): The protocol(s) described by the file, and
            total_alternating_duration_ms (None if the file describes only one protocol).
    """

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        message = f'Could not read protocol file {yaml_path}: {e}'
        get_logger().critical(message)
        sys.exit(message)

    data = _require_mapping(data, 'the top-level protocol file')
    _reject_unknown_keys(data, _REQUIRED_TOP_LEVEL_KEYS + _OPTIONAL_TOP_LEVEL_KEYS,
                         'the top-level protocol file')

    driving_sys_serial = _require_key(data, 'driving_sys_serial', 'the top-level protocol file')
    protocol_defs = _require_list(_require_key(data, 'protocols', 'the top-level protocol file'),
                                  "'protocols'")

    protocols = []
    for protocol_index, protocol_def in enumerate(protocol_defs):
        context = f'protocols[{protocol_index}]'
        protocol_def = _require_mapping(protocol_def, context)
        _reject_unknown_keys(protocol_def, _REQUIRED_PROTOCOL_KEYS, context)

        slot_defs = _require_list(_require_key(protocol_def, 'slots', context),
                                  f'{context}.slots')
        timing_def = _require_key(protocol_def, 'timing', context)

        protocol = TUSProtocol(driving_sys_serial, engineering_mode)
        for slot_index, slot_def in enumerate(slot_defs):
            _build_slot(protocol, slot_def, slot_index, protocol_index)
        _configure_timing(protocol, timing_def, protocol_index)

        protocols.append(protocol)

    return protocols, data.get('total_alternating_duration_ms')
