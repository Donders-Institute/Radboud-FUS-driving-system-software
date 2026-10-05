# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from collections import namedtuple

from fus_driving_systems import protocol_loader
from fus_driving_systems.exceptions import FDSError, FDSValidationError
from fus_driving_systems.tus_protocol import TUSProtocol

LoadResult = namedtuple('LoadResult', ['protocol', 'failed_slots'])
# failed_slots: list of (slot_def, FDSError) pairs, one per slot that failed to construct, in
# file order; see load()'s own docstring for why this doesn't just raise instead.


def load(yaml_path):
    """
    Loads yaml_path for the Planning tab's own single-protocol editor. Rejects an interleaved
    file (more than one 'protocols' entry) outright, rather than silently showing only the
    first one: editing several interleaved protocols side by side is a genuinely different
    editing mode this single-protocol editor doesn't support yet.

    Unlike protocol_loader.load_protocol(), a slot whose own values fail add_slot()'s semantic
    validation (e.g. a power value exceeding the configured safety limit) doesn't abort the
    whole load: that slot is skipped rather than added, every other slot and the timing still
    load normally, and the raw slot_def plus the exception that stopped it are returned in
    failed_slots instead. PlanningTab.load_protocol() uses that to show a SlotEditor pre-filled
    with those raw values and the failure inline, exactly like a failed manual Apply would,
    rather than losing the whole file over one bad slot.

    Parameters:
        yaml_path (str): Path to the YAML protocol-definition file.

    Returns:
        LoadResult: protocol (TUSProtocol, containing only the slots that loaded successfully,
            with timing already configured) and failed_slots (see this module's own note on
            LoadResult).

    Raises:
        FDSValidationError: If the file describes more than one protocol (interleaved).
        FDSError: Whatever parse_protocol_file()/apply_validated_timing() themselves raise for
            a genuine file-structural problem, or an invalid timing block. There's no partial
            protocol to recover in either case (the first because there's nothing to have
            constructed yet, the second because every slot depends on timing existing at all).
    """

    (driving_sys_serial, protocol_defs, *_rest) = protocol_loader.parse_protocol_file(yaml_path)
    if len(protocol_defs) > 1:
        message = (f'{yaml_path} describes {len(protocol_defs)} interleaved protocols; the '
                   'Planning tab can only edit a single protocol at a time.')
        raise FDSValidationError(message)

    protocol_def = protocol_defs[0]
    protocol = TUSProtocol(driving_sys_serial)

    failed_slots = []
    for slot_def in protocol_def['slots']:
        try:
            protocol_loader.add_validated_slot(protocol, slot_def)
        except FDSError as e:
            failed_slots.append((slot_def, e))

    protocol_loader.apply_validated_timing(protocol, protocol_def['timing'])

    return LoadResult(protocol, failed_slots)


def save(protocol, yaml_path):
    """Thin wrapper around protocol_loader.save_protocol(), for a consistent import surface with
    load() above (this module is the Planning tab's own single entry point for file I/O)."""

    protocol_loader.save_protocol(protocol, yaml_path)


def approve(yaml_path):
    """Thin wrapper around protocol_loader.approve_protocol()."""

    protocol_loader.approve_protocol(yaml_path)
