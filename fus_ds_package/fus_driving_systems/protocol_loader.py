# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basic packages
import hashlib

import yaml

# Own packages
from fus_driving_systems.tus_protocol import TUSProtocol
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSSafetyError, FDSValidationError


_REQUIRED_TOP_LEVEL_KEYS = ('driving_sys_serial', 'protocols')
# trigger_option/n_triggers/buffer_num are top-level (whole-file), not per-protocol 'timing:'
# fields -- they're parameters of IGT.send_protocol()/wait_for_trigger()/execute_protocol(), so
# there is exactly one value for the whole file, the same way total_alternating_duration_ms
# already is.
_OPTIONAL_TOP_LEVEL_KEYS = ('total_alternating_duration_ms', 'trigger_option', 'n_triggers',
                            'buffer_num')

_REQUIRED_PROTOCOL_KEYS = ('slots', 'timing')

_REQUIRED_SLOT_KEYS = ('transducer_serial', 'focus_option', 'focus_value', 'power_option',
                       'power_value')
_OPTIONAL_SLOT_KEYS = ('oper_freq', 'dephasing_degree')

_REQUIRED_TIMING_KEYS = ('pulse_dur',)
_OPTIONAL_TIMING_KEYS = ('pulse_rep_int', 'pulse_train_dur',
                         'pulse_ramp_shape', 'pulse_ramp_dur',
                         'pulse_train_rep_int', 'pulse_train_rep_dur')


def _require_mapping(value, context):
    """Returns value, or raises FDSValidationError if it isn't a mapping (dict) -- e.g. a
    researcher wrote a list or a bare scalar where key: value pairs were expected."""

    if not isinstance(value, dict):
        message = f'{context} must be a mapping (key: value pairs), got {type(value).__name__}.'
        get_logger().critical(message)
        raise FDSValidationError(message)

    return value


def _require_list(value, context):
    """Returns value, or raises FDSValidationError if it isn't a non-empty list."""

    if not isinstance(value, list) or not value:
        message = f'{context} must be a non-empty list.'
        get_logger().critical(message)
        raise FDSValidationError(message)

    return value


def _require_key(mapping, key, context):
    """Returns mapping[key], or raises FDSValidationError with a clear message naming the
    missing key and context."""

    if key not in mapping:
        message = f"Missing required key '{key}' in {context}."
        get_logger().critical(message)
        raise FDSValidationError(message)

    return mapping[key]


def _reject_unknown_keys(mapping, known_keys, context):
    """Raises FDSValidationError if mapping has any key outside known_keys -- catches a typo'd
    key immediately
    (e.g. 'puls_dur'), rather than it silently doing nothing, since every optional key is read
    via .get() elsewhere. Also flags a literal 'engineering_mode' key with a dedicated message:
    it's deliberately not a file field anywhere in this schema, only a Python-level
    load_protocol() parameter, so a researcher adding it here would otherwise get a generic
    "unknown key" message that doesn't explain why."""

    if 'engineering_mode' in mapping:
        message = ("'engineering_mode' is not a protocol-file field -- set it as a Python-level "
                   "parameter instead: load_protocol(yaml_path, engineering_mode=True).")
        get_logger().critical(message)
        raise FDSValidationError(message)

    unknown = set(mapping) - set(known_keys)
    if unknown:
        message = (f'Unknown key(s) {sorted(unknown)} in {context} -- check for typos. ' +
                   f'Expected one of: {sorted(known_keys)}.')
        get_logger().critical(message)
        raise FDSValidationError(message)


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
        pulse_ramp_shape=timing_def.get('pulse_ramp_shape'),
        pulse_ramp_dur=timing_def.get('pulse_ramp_dur'),
        pulse_train_rep_int=timing_def.get('pulse_train_rep_int'),
        pulse_train_rep_dur=timing_def.get('pulse_train_rep_dur'),
    )


def _compute_file_hash(raw_bytes):
    """Returns raw_bytes' SHA-256 hex digest."""

    return hashlib.sha256(raw_bytes).hexdigest()


def _hash_sidecar_path(yaml_path):
    """Returns the sidecar hash-file path for yaml_path -- '<yaml_path>.sha256'."""

    return f'{yaml_path}.sha256'


def _verify_hash(yaml_path, raw_bytes, require_hash):
    """Protection against an accidental edit to yaml_path: if a sidecar '<yaml_path>.sha256'
    file exists (written by approve_protocol()), its hash must match yaml_path's current
    content, or this raises FDSSafetyError. If no sidecar exists, this raises FDSSafetyError
    only when require_hash -- otherwise it silently does nothing, since hash protection is
    opt-in by default, per protocol file."""

    sidecar_path = _hash_sidecar_path(yaml_path)
    try:
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            expected_hash = f.read().split()[0]
    except FileNotFoundError:
        if require_hash:
            message = (f'{yaml_path} has not been approved yet ({sidecar_path} is missing), but '
                       f'this script requires an approved protocol (require_hash=True). Run: '
                       f'python -m fus_driving_systems.approve_protocol {yaml_path}')
            get_logger().critical(message)
            raise FDSSafetyError(message)
        return

    actual_hash = _compute_file_hash(raw_bytes)
    if actual_hash != expected_hash:
        message = (f'{yaml_path} does not match its approved hash ({sidecar_path}) -- it has '
                   f'been edited since it was last approved. If this edit is intentional, '
                   f'review it, then run: python -m fus_driving_systems.approve_protocol '
                   f'{yaml_path}')
        get_logger().critical(message)
        raise FDSSafetyError(message)


def approve_protocol(yaml_path):
    """
    Computes yaml_path's current SHA-256 hash and writes it to a sidecar '<yaml_path>.sha256'
    file (sha256sum-compatible format), so load_protocol() will detect any future edit to the
    file. This is the only way that sidecar is ever written -- load_protocol() never writes one
    itself. Hash protection is opt-in by default: a protocol file with no sidecar is loaded
    without any check at all, unless the calling script passes require_hash=True to
    load_protocol().

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file to approve.
    """

    with open(yaml_path, 'rb') as f:
        raw_bytes = f.read()

    sidecar_path = _hash_sidecar_path(yaml_path)
    with open(sidecar_path, 'w', encoding='utf-8') as f:
        f.write(f'{_compute_file_hash(raw_bytes)}  {yaml_path}\n')

    get_logger().info(f'Approved {yaml_path} -- wrote {sidecar_path}.')


def load_protocol(yaml_path, engineering_mode=False, require_hash=False):
    """
    Parses a YAML protocol-definition file into ready-to-use TUSProtocol object(s).

    engineering_mode and require_hash are deliberately Python-level parameters here, not YAML
    fields -- both must be set by editing the calling script, never the YAML file a researcher
    edits (a researcher could otherwise turn off a safeguard simply by editing the file it's
    meant to protect).

    Semantic validation (unknown driving-system/transducer serial, invalid focus/power/trigger
    option, out-of-range timing value) is not duplicated here -- TUSProtocol/add_slot()/
    configure_timing() already raise a clear FDSValidationError for all of these. This function
    only validates the file's own structure: required keys present, no typo'd/unknown keys.

    If yaml_path has a sidecar '<yaml_path>.sha256' file (written by approve_protocol()), this
    raises FDSSafetyError when yaml_path's content no longer matches it -- protection against an
    accidental edit. A protocol file with no sidecar is loaded without any check at all, unless
    require_hash is True, in which case a missing sidecar also raises FDSSafetyError (e.g. it
    was never approved, or the sidecar was lost/not copied alongside the file).

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file.
        engineering_mode (bool): Passed straight to every TUSProtocol this file describes.
        require_hash (bool): If True, yaml_path must have a matching, approved '.sha256'
            sidecar -- a missing sidecar raises FDSSafetyError, instead of silently loading
            unchecked.

    Returns:
        tuple(list(TUSProtocol), float or None, str or None, int or None, int): The protocol(s)
            described by the file; total_alternating_duration_ms (None if the file describes
            only one protocol); trigger_option and n_triggers (None if the file omits them --
            meant to be forwarded straight into IGT.wait_for_trigger(), see its own docstring for
            why these live at the top level, not inside any one protocol's 'timing:'); and
            buffer_num (0 if the file omits it), meant to be forwarded into
            send_protocol()/wait_for_trigger()/execute_protocol() the same way.
    """

    try:
        with open(yaml_path, 'rb') as f:
            raw_bytes = f.read()
    except OSError as e:
        message = f'Could not read protocol file {yaml_path}: {e}'
        get_logger().critical(message)
        raise FDSValidationError(message) from e

    _verify_hash(yaml_path, raw_bytes, require_hash)

    try:
        data = yaml.safe_load(raw_bytes)
    except yaml.YAMLError as e:
        message = f'Could not read protocol file {yaml_path}: {e}'
        get_logger().critical(message)
        raise FDSValidationError(message) from e

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

    return (protocols, data.get('total_alternating_duration_ms'), data.get('trigger_option'),
            data.get('n_triggers'), data.get('buffer_num', 0))
