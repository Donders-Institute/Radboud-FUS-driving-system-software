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


def _validate_slot_def(slot_def, slot_index, protocol_index):
    """Structurally validates one slot_def (one entry of a protocol's own 'slots' list):
    required keys present, no typo'd/unknown keys. Doesn't construct anything via add_slot()
    (see add_validated_slot() below for that, a separate step); this only settles whether
    slot_def's own shape is even usable at all.

    Returns:
        dict: slot_def itself, confirmed to be a mapping with every required key present.
    """

    context = f'protocols[{protocol_index}].slots[{slot_index}]'
    slot_def = _require_mapping(slot_def, context)
    _reject_unknown_keys(slot_def, _REQUIRED_SLOT_KEYS + _OPTIONAL_SLOT_KEYS, context)
    for key in _REQUIRED_SLOT_KEYS:
        _require_key(slot_def, key, context)
    return slot_def


def add_validated_slot(protocol, slot_def):
    """
    Adds one already structurally-validated slot_def (see _validate_slot_def(), already run by
    parse_protocol_file()/load_protocol()) to protocol, via add_slot(). This is the one step
    that can still raise for a semantic reason (unknown transducer serial, invalid focus/power
    value, no active calibration, a safety limit exceeded, and so on). A caller that wants to
    recover from exactly that, one slot at a time, rather than aborting an entire file over a
    single bad slot (e.g. the GUI's own protocol_io.load()), calls this itself per slot instead
    of going through load_protocol()'s own all-or-nothing loop.

    Parameters:
        protocol (TUSProtocol): The protocol to add the slot to.
        slot_def (dict): One already-validated slot definition, as returned by
            parse_protocol_file() (each of protocol_defs[i]['slots']).

    Raises:
        FDSError: Whatever add_slot() itself raises for an invalid slot_def.
    """

    protocol.add_slot(slot_def['transducer_serial'], slot_def['focus_option'],
                      slot_def['focus_value'], slot_def['power_option'],
                      slot_def['power_value'], oper_freq=slot_def.get('oper_freq'),
                      dephasing_degree=slot_def.get('dephasing_degree'))


def _validate_timing_def(timing_def, protocol_index):
    """Structurally validates one protocol's 'timing' mapping; see _validate_slot_def()'s own
    docstring for the same reasoning applied to timing instead of a slot.

    Returns:
        dict: timing_def itself, confirmed to be a mapping with 'pulse_dur' present.
    """

    context = f'protocols[{protocol_index}].timing'
    timing_def = _require_mapping(timing_def, context)
    _reject_unknown_keys(timing_def, _REQUIRED_TIMING_KEYS + _OPTIONAL_TIMING_KEYS, context)
    _require_key(timing_def, 'pulse_dur', context)
    return timing_def


def apply_validated_timing(protocol, timing_def):
    """Applies one already structurally-validated timing_def (see _validate_timing_def(),
    already run by parse_protocol_file()/load_protocol()) to protocol, via configure_timing().
    See add_validated_slot()'s own docstring for why this is its own, separate step.

    Parameters:
        protocol (TUSProtocol): The protocol to configure.
        timing_def (dict): One already-validated timing definition, as returned by
            parse_protocol_file() (each of protocol_defs[i]['timing']).

    Raises:
        FDSError: Whatever configure_timing() itself raises for an invalid timing_def.
    """

    protocol.configure_timing(
        timing_def['pulse_dur'],
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

    Raises:
        FDSValidationError: If yaml_path can't be read, or its sidecar can't be written (e.g. a
            missing file, or a permissions error).
    """

    try:
        with open(yaml_path, 'rb') as f:
            raw_bytes = f.read()
    except OSError as e:
        message = f'Could not read protocol file {yaml_path}: {e}'
        get_logger().critical(message)
        raise FDSValidationError(message) from e

    sidecar_path = _hash_sidecar_path(yaml_path)
    try:
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            f.write(f'{_compute_file_hash(raw_bytes)}  {yaml_path}\n')
    except OSError as e:
        message = f'Could not write hash sidecar {sidecar_path}: {e}'
        get_logger().critical(message)
        raise FDSValidationError(message) from e

    get_logger().info(f'Approved {yaml_path} -- wrote {sidecar_path}.')


def _dump_slot(slot):
    """One TransducerSlot's own YAML slot mapping; see save_protocol()'s own docstring. chosen_
    focus/chosen_power (and their own *_value counterparts) return exactly what a caller
    originally passed to add_slot()/update_transducer()/configure(), so this reproduces that
    call's own arguments, not TUSProtocol's internal derived state (focus_wrt_exit_plane and
    focus_wrt_mid_bowl both exist together on a configured slot regardless of which one was
    actually chosen)."""

    focus_value = slot.chosen_focus_value
    if isinstance(focus_value, tuple):
        focus_value = list(focus_value)  # yaml.safe_dump has no representer for tuple.

    return {
        'transducer_serial': slot.transducer.serial,
        'focus_option': slot.chosen_focus,
        'focus_value': focus_value,
        'power_option': slot.chosen_power,
        'power_value': slot.chosen_power_value,
        'oper_freq': slot.oper_freq,
        'dephasing_degree': slot.dephasing_degree,
    }


def _dump_timing(protocol):
    """One TUSProtocol's own fully-resolved timing fields, in the same units configure_timing()
    itself accepts (pulse_train_rep_dur in seconds, everything else in milliseconds). Every
    field is written explicitly, never omitted: TUSProtocol.__init__() already cascades a
    complete, self-consistent set of values the moment a protocol is constructed (see its own
    docstring), so there is never a "not yet set" timing field to leave out here."""

    return {
        'pulse_dur': protocol.pulse_dur,
        'pulse_rep_int': protocol.pulse_rep_int,
        'pulse_train_dur': protocol.pulse_train_dur,
        'pulse_ramp_shape': protocol.pulse_ramp_shape,
        'pulse_ramp_dur': protocol.pulse_ramp_dur,
        'pulse_train_rep_int': protocol.pulse_train_rep_int,
        'pulse_train_rep_dur': protocol.pulse_train_rep_dur / 1e3,
    }


def save_protocol(protocol, yaml_path, trigger_option=None, n_triggers=None, buffer_num=0):
    """
    Writes protocol to yaml_path in the same schema load_protocol() reads, this function's own
    exact inverse for the single-protocol case: save_protocol() then load_protocol() reproduces
    an equivalent protocol. Interleaved multi-protocol files (several 'protocols' entries, see
    load_protocol()'s own Returns section) aren't produced by this function, only ever a single
    protocol.

    Parameters:
        protocol (TUSProtocol): The protocol to write. Must already have at least one slot
            added (see TUSProtocol.add_slot()); load_protocol() itself would reject a
            'slots: []' file the same way, so this is checked here too, to fail at save time
            rather than only on a later, separate load attempt.
        yaml_path (str): Path to write the YAML file to. Overwritten if it already exists.
        trigger_option (str): Written to the file's own top-level 'trigger_option' key; omitted
            entirely when None, matching load_protocol()'s own "not given" case (see
            IGT.wait_for_trigger()'s own parameter of the same name).
        n_triggers (int): Written to the file's own top-level 'n_triggers' key; omitted entirely
            when None.
        buffer_num (int): Written to the file's own top-level 'buffer_num' key; omitted when 0,
            matching load_protocol()'s own default for an absent key.

    Raises:
        FDSValidationError: If protocol has no transducer slots added yet, or yaml_path can't be
            written (e.g. its parent directory doesn't exist, or a permissions error).
    """

    if not protocol.slots:
        message = 'Cannot save a protocol with no transducer slots configured.'
        get_logger().critical(message)
        raise FDSValidationError(message)

    data = {
        'driving_sys_serial': protocol.driving_sys.serial,
        'protocols': [{
            'slots': [_dump_slot(slot) for slot in protocol.slots],
            'timing': _dump_timing(protocol),
        }],
    }
    if trigger_option is not None:
        data['trigger_option'] = trigger_option
    if n_triggers is not None:
        data['n_triggers'] = n_triggers
    if buffer_num:
        data['buffer_num'] = buffer_num

    try:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False)
    except OSError as e:
        message = f'Could not write protocol file {yaml_path}: {e}'
        get_logger().critical(message)
        raise FDSValidationError(message) from e

    get_logger().info(f'Saved protocol to {yaml_path}.')


def parse_protocol_file(yaml_path, require_hash=False):
    """
    Reads and structurally validates yaml_path: required keys present, no typo'd/unknown keys,
    the right shapes (mappings/lists where expected). Does not construct or semantically
    validate anything via TUSProtocol/add_slot()/configure_timing(); load_protocol() itself is
    built directly on top of this, doing exactly that construction step immediately, per
    protocol/slot, and raising on the first problem it finds (see its own docstring).

    A caller that instead wants to recover from one bad slot gracefully, rather than have a
    single invalid slot abort the entire file (e.g. the GUI's own protocol_io.load(), which
    shows the raw values it would have applied and why they failed, instead of losing every
    other slot along with it) calls this directly, then add_validated_slot()/
    apply_validated_timing() itself, one slot/timing block at a time.

    If yaml_path has a sidecar '<yaml_path>.sha256' file (written by approve_protocol()), this
    raises FDSSafetyError when yaml_path's content no longer matches it -- protection against an
    accidental edit. A protocol file with no sidecar is loaded without any check at all, unless
    require_hash is True, in which case a missing sidecar also raises FDSSafetyError (e.g. it
    was never approved, or the sidecar was lost/not copied alongside the file).

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file.
        require_hash (bool): If True, yaml_path must have a matching, approved '.sha256'
            sidecar -- a missing sidecar raises FDSSafetyError, instead of silently loading
            unchecked.

    Returns:
        tuple(str, list(dict), float or None, str or None, int or None, int): driving_sys_serial;
            one dict per protocol, each {'slots': list(dict), 'timing': dict} (both already
            structurally validated and ready for add_validated_slot()/apply_validated_timing());
            then total_alternating_duration_ms (None if the file describes only one protocol);
            trigger_option and n_triggers (None if the file omits them: meant to be forwarded
            straight into IGT.wait_for_trigger(), see its own docstring for why these live at
            the top level, not inside any one protocol's 'timing:'); and buffer_num (0 if the
            file omits it), meant to be forwarded into send_protocol()/wait_for_trigger()/
            execute_protocol() the same way.
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

    validated_protocol_defs = []
    for protocol_index, protocol_def in enumerate(protocol_defs):
        context = f'protocols[{protocol_index}]'
        protocol_def = _require_mapping(protocol_def, context)
        _reject_unknown_keys(protocol_def, _REQUIRED_PROTOCOL_KEYS, context)

        slot_defs = _require_list(_require_key(protocol_def, 'slots', context),
                                  f'{context}.slots')
        timing_def = _require_key(protocol_def, 'timing', context)

        validated_slots = [_validate_slot_def(slot_def, slot_index, protocol_index)
                           for slot_index, slot_def in enumerate(slot_defs)]
        validated_protocol_defs.append({
            'slots': validated_slots,
            'timing': _validate_timing_def(timing_def, protocol_index),
        })

    return (driving_sys_serial, validated_protocol_defs,
            data.get('total_alternating_duration_ms'), data.get('trigger_option'),
            data.get('n_triggers'), data.get('buffer_num', 0))


def load_protocol(yaml_path, engineering_mode=False, require_hash=False):
    """
    Parses a YAML protocol-definition file into ready-to-use TUSProtocol object(s), via
    parse_protocol_file() (see its own docstring for the structural validation this does, and
    for a way to recover from one bad slot instead of this function's own all-or-nothing
    construction below).

    engineering_mode is a deliberately Python-level parameter here, not a YAML field: it must
    be set by editing the calling script, never the YAML file a researcher edits (a researcher
    could otherwise turn off a safeguard simply by editing the file it's meant to protect).

    Semantic validation (unknown driving-system/transducer serial, invalid focus/power/trigger
    option, out-of-range timing value) is not duplicated here; TUSProtocol/add_slot()/
    configure_timing() already raise a clear FDSValidationError for all of these.

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file.
        engineering_mode (bool): Passed straight to every TUSProtocol this file describes.
        require_hash (bool): See parse_protocol_file()'s own docstring.

    Returns:
        tuple(list(TUSProtocol), float or None, str or None, int or None, int): The protocol(s)
            described by the file; total_alternating_duration_ms, trigger_option, n_triggers,
            and buffer_num, matching parse_protocol_file()'s own trailing four return values.
    """

    (driving_sys_serial, protocol_defs, total_alternating_duration_ms, trigger_option,
     n_triggers, buffer_num) = parse_protocol_file(yaml_path, require_hash)

    protocols = []
    for protocol_def in protocol_defs:
        protocol = TUSProtocol(driving_sys_serial, engineering_mode)
        for slot_def in protocol_def['slots']:
            add_validated_slot(protocol, slot_def)
        apply_validated_timing(protocol, protocol_def['timing'])

        protocols.append(protocol)

    return protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num
