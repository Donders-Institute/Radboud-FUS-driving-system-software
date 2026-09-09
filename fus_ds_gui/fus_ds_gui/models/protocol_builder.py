# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from fus_driving_systems import transducer
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.exceptions import FDSConfigError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.tus_protocol import TUSProtocol
from fus_driving_systems.utils import get_config_value

# Maps DrivingSystem.manufact (uppercased) to the concrete ControlDrivingSystem subclass that
# actually implements it. Adding a new manufacturer to fus_driving_systems (its own
# ControlDrivingSystem subclass, see the core package's own README) must also register that
# subclass here; this dict is the only place the GUI learns such a class exists at all. CITRUS
# is deliberately absent.
_DRIVING_SYSTEM_CLASSES = {
    'IGT': IGT,
    'SONIC CONCEPTS': SonicConcepts,
}


def _create_ds_instance(driving_system):
    """
    Returns a fresh (unconnected) instance of whichever ControlDrivingSystem subclass actually
    implements driving_system, purely so its own validate_protocol() override (IGT/SonicConcepts
    each add checks beyond the shared base ones) can be called without needing a live connection.

    Raises:
        FDSConfigError: If driving_system's manufacturer has no matching GUI-supported class.
    """

    manufacturer = (driving_system.manufact or '').strip().upper()
    cls = _DRIVING_SYSTEM_CLASSES.get(manufacturer)
    if cls is None:
        message = (f"No GUI support for manufacturer '{driving_system.manufact}' "
                   f"(driving system {driving_system.serial}).")
        get_logger().error(message)
        raise FDSConfigError(message)
    return cls()


def _is_engineering_only(section, option):
    """
    Whether option (one of section's own DrivingSystem.focus_options/power_options entries)
    requires TUSProtocol(engineering_mode=True). Mirrors TransducerSlot._requires_engineering_
    mode()'s own check exactly, duplicated here since that's an instance method on an
    already-configured slot, not reachable before one exists, which is exactly when this needs
    to filter what the Planning tab's dropdowns even offer in the first place (the GUI never
    sets engineering_mode=True, see equipment_panel.py's own module docstring).

    Parameters:
        section (str): 'Power' or 'Focus'.
        option (str): The specific power/focus option being checked.

    Returns:
        bool: True if engineering_mode would be required to set this option directly.
    """

    engineering_only = get_config_value(
        get_logger(), config, section, 'Engineering-only options', '').split('\n')
    return option in engineering_only


class ProtocolBuilder:
    """
    Wraps one TUSProtocol under construction in the Planning tab, plus the glue the backend
    doesn't expose directly: picking the right ControlDrivingSystem subclass to validate
    against, and filtering out engineering-only options (see _is_engineering_only()).

    One instance per selected driving system; the Planning tab replaces it (never mutates it in
    place) whenever the equipment selection changes, since TUSProtocol.driving_sys is itself
    read-only, by design, for the same reason (see TUSProtocol.driving_sys's own docstring).
    """

    def __init__(self, driving_system):
        self.driving_system = driving_system
        self.protocol = TUSProtocol(driving_system.serial, engineering_mode=False)
        self._ds_instance = _create_ds_instance(driving_system)

    def xyz_focus_options(self):
        """
        The two 3D (x, y, z) focus option labels, however they're actually named in config,
        read via the same 'Focus'/'Option.xyz_exit'/'Option.xyz_bowl' lookup
        TransducerSlot._set_focus_xyz() itself uses, so this can never drift out of sync with
        what the backend treats as an xyz option.

        Returns:
            set[str]: The configured xyz-wrt-exit-plane and xyz-wrt-mid-bowl option labels.
        """

        return {
            get_config_value(get_logger(), config, 'Focus', 'Option.xyz_exit',
                             'Focus xyz wrt exit plane [mm]'),
            get_config_value(get_logger(), config, 'Focus', 'Option.xyz_bowl',
                             'Focus xyz wrt mid bowl [mm]'),
        }

    def mid_bowl_focus_option(self):
        """
        The scalar 'wrt mid bowl' focus option label, however it's actually named in config,
        read via the same 'Focus'/'Option.bowl' lookup TransducerSlot._set_focus_wrt_mid_bowl()
        itself uses. Needed because that option's valid range isn't transducer.min_foc/max_foc
        directly (see SlotEditor._update_focus_range()'s own docstring): mid bowl and exit plane
        are offset from each other by exit_plane_dist.

        Returns:
            str: The configured wrt-mid-bowl option label.
        """

        return get_config_value(get_logger(), config, 'Focus', 'Option.bowl',
                                'Focus wrt mid bowl [mm]')

    def focus_options(self, tran=None):
        """
        Parameters:
            tran (Transducer): The transducer this slot would use, if known. Only affects
                whether the two xyz options are offered (see below); every other option this
                driving system offers (once engineering-only ones are already filtered out)
                stays available regardless of which transducer is chosen.

        Returns:
            List[str]: This driving system's focus options, minus any engineering-only ones, and
            minus the two 3D (x, y, z) options unless tran.can_3d_steer is True.
            TransducerSlot._set_focus_xyz() raises FDSValidationError for any transducer that
            isn't configured as 3D-steering-capable, so there is no point offering a choice the
            backend will always reject for one that isn't.
        """

        xyz_options = self.xyz_focus_options()
        can_steer = tran is not None and tran.can_3d_steer
        return [option for option in self.protocol.get_focus_options()
                if not _is_engineering_only('Focus', option)
                and (can_steer or option not in xyz_options)]

    def _has_active_combination(self, tran):
        """
        Mirrors TransducerSlot._combo_is_active()'s own 'Equipment.Combination.<ds><sign><tran>'
        lookup, without needing an actual slot to exist yet: this decides what the Planning
        tab's own dropdowns even offer, before Apply ever creates one.

        Returns:
            bool: True only if an active calibration combo exists for this driving system paired
            with tran.
        """

        combo_sign = get_config_value(get_logger(), config, 'Equipment', 'Combination sign', '~')
        section = 'Equipment.Combination.' + combo_sign.join(
            [self.driving_system.serial, tran.serial])
        if section not in config:
            return False
        return get_config_value(get_logger(), config, section, 'Active?', 'True') == 'True'

    def power_options(self, tran=None):
        """
        Parameters:
            tran (Transducer): The transducer this slot would use, if known. Only affects
                whether non-native power options are offered (see below); every native option is
                available regardless of which transducer is chosen.

        Returns:
            List[str]: This driving system's power options, minus any engineering-only ones, and
            minus any non-native option with no active calibration for (this driving system,
            tran): without one, TransducerSlot can't convert that option to what's actually
            sent to hardware, so offering it would only ever leave ampl unset once applied (see
            IGT.validate_protocol()'s "ampl is None" check).
        """

        can_convert = tran is not None and self._has_active_combination(tran)
        return [option for option in self.protocol.get_power_options()
                if not _is_engineering_only('Power', option)
                and (option in self.driving_system.native_power_params or can_convert)]

    def ramp_shapes(self):
        """
        Returns:
            List[str]: Available pulse ramp shapes (no engineering-only concept applies here).
        """

        return self.protocol.get_ramp_shapes()

    def rectangular_ramp_shape(self):
        """
        The one ramp shape that means "no ramping". Read from config rather than hardcoded, so
        the Planning tab's own ramp-duration auto-disable (see timing_panel.py) can never drift
        out of sync with what configure_timing() itself treats as "no ramping" (see its own
        'Ramp'/'option.rect' lookup).

        Returns:
            str: The configured rectangular (no-ramping) ramp shape label.
        """

        return get_config_value(get_logger(), config, 'Ramp', 'option.rect',
                                'Rectangular - no ramping')

    def supports_dephasing(self):
        """
        Returns:
            bool: True only for an IGT-backed driving system. SonicConcepts's own backend
            (sonic_concepts_ds.py) never reads TransducerSlot.dephasing_degree anywhere, so
            configuring it there would silently have no effect; the GUI hides the whole
            dephasing section in that case rather than let a researcher configure a no-op.
        """

        return isinstance(self._ds_instance, IGT)

    def compatible_transducers(self):
        """
        Returns:
            List[Transducer]: Every active transducer compatible with this driving system (see
            DrivingSystem.tran_comp). transducer.get_tran_list() itself returns every active
            transducer regardless of compatibility, so this filters it down.
        """

        return [tran for tran in transducer.get_tran_list()
                if tran.serial in self.driving_system.tran_comp]

    def can_add_slot(self):
        """
        Returns:
            bool: True if another transducer slot can still be added (see
            DrivingSystem.max_tran_slots).
        """

        return len(self.protocol.slots) < self.driving_system.max_tran_slots

    def add_slot(self, transducer_serial, focus_option, focus_value, power_option, power_value,
                 oper_freq=None, dephasing_degree=None):
        """
        Adds and fully configures one new transducer slot; see TUSProtocol.add_slot() for the
        exact contract (the first five parameters are always required together; oper_freq/
        dephasing_degree are optional, see its own docstring for their defaults).

        Returns:
            TransducerSlot: The newly added slot.
        """

        return self.protocol.add_slot(transducer_serial, focus_option, focus_value,
                                      power_option, power_value, oper_freq, dephasing_degree)

    def configure_timing(self, **kwargs):
        """
        Forwards to TUSProtocol.configure_timing(); see its own docstring for the exact
        parameter contract (pulse_train_rep_dur is in seconds, everything else in milliseconds).
        """

        self.protocol.configure_timing(**kwargs)

    def validate(self):
        """
        Cross-field validation for the current protocol, via whichever concrete driving-system
        class's own validate_protocol() override applies (IGT/SonicConcepts each add checks
        beyond the shared base ones).

        Safe to call before any transducer slot has been added: the shared base checks (timing
        consistency) don't depend on protocol.slots at all, and every override's own per-slot
        checks are written to have nothing to report over an empty protocol.slots, rather than
        raise, so a researcher gets timing feedback immediately, without needing to apply a slot
        first just to unlock it.

        Returns:
            List[str]: Validation error messages, empty if the protocol is currently valid.
        """

        return self._ds_instance.validate_protocol(self.protocol)
