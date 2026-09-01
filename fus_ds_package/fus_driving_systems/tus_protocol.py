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
import sys

# Own packages
from fus_driving_systems import driving_system as ds
from fus_driving_systems.transducer_slot import TransducerSlot

from fus_driving_systems.calc_utils import validate_value
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.utils import get_config_value


# Which driving system serials have already had their (static, never changing within a process)
# info logged once -- see TUSProtocol.__init__. Module-level rather than per-instance: a script
# typically constructs many TUSProtocol objects for the same driving system over a session (one
# per trial/condition), and this info is about the driving system, not any one of them.
_logged_driving_systems = set()


class TUSProtocol():
    """
    Class representing a TUS (transcranial ultrasound) protocol.

    Everything genuinely per-transducer (transducer, focus, power, operating frequency,
    dephasing) lives on one or more TransducerSlot objects instead of directly on TUSProtocol --
    see self.slots/self.add_slot(). A TUSProtocol always has an explicit driving system (no
    config-fallback default: the caller must say which one) and starts with zero slots; call
    add_slot() at least once before sending it anywhere. There is no single-slot delegation on
    TUSProtocol itself (no protocol.press/protocol.transducer/etc.) -- every per-transducer
    attribute is always addressed via protocol.slots[i].<attribute>, whether there's one slot or
    several, so a script is never in doubt about which access style applies to a given driving
    system.

    buffer_num and trigger_option/n_triggers are not attributes of this class. There is exactly
    one hardware buffer and one trigger event per send_protocol()/wait_for_trigger()/
    execute_protocol() call, whether it's given a single protocol or several interleaved ones --
    so these are call-level parameters of those methods instead (see their own docstrings), not
    per-protocol properties. Ramping stays here, since some driving system could in principle
    support per-protocol ramping even while interleaving -- IGT specifically doesn't, but that's
    a fact about IGT's hardware, not a reason to model ramping as call-level for every driving
    system.

    Attributes:
        _driving_sys (DrivingSystem): The driving system associated with the protocol.
        _slots (list(TransducerSlot)): The transducer slot(s) of this protocol -- see add_slot().
        _timing_param (dict.):
            _pulse_dur (float): Pulse duration of the protocol [ms].
            _pulse_rep_int (float): Pulse repetition interval of the protocol [ms].
            _pulse_ramp_shape (str): Shape of the ramping for the pulse.
            _pulse_ramp_dur (float): Ramp duration for the pulse [ms].
            _pulse_train_dur (float): Pulse train duration [ms].
            _pulse_train_rep_int (float): Pulse train repetition interval [ms].
            _pulse_train_rep_dur (float): Pulse train repetition duration [ms].

    Methods:
        info(): Returns a formatted string containing information about the protocol.
        get_ds_serials(): Returns a list of serial numbers for available driving systems.
        get_tran_serials(): Returns a list of serial numbers for available transducers.
        getters (attribute name without _) for above attributes. Every _timing_param field has a
        getter only -- configure_timing() is the only way to set any of them, precisely because
        they cascade/interact with each other and are prone to ordering hazards if set
        individually and out of order.
    """

    def __init__(self, driving_sys_serial, engineering_mode=False):
        """
        Initializes a TUSProtocol object with default values and loads configuration settings.

        Parameters:
            driving_sys_serial (str): Serial number of the driving system this protocol is for.
                                      Required -- there is no config-fallback default, since
                                      that default only ever existed to pre-fill a GUI dropdown
                                      (SonoRover One), not to pick silently for a script.
            engineering_mode (bool): Whether engineering-only power/focus options may be set
                                     directly. See _requires_engineering_mode() on TransducerSlot.
        """

        self._engineering_mode = engineering_mode

        self._driving_sys = ds.DrivingSystem()
        self._driving_sys.set_ds_info(driving_sys_serial)

        # Logged once per driving system serial per process (not per protocol, and not in
        # __str__() below) -- this is static config info (see ds_config.ini), unrelated to any
        # one protocol, so repeating it on every protocol validation/send would only add clutter
        # (GitHub issue #140). Logging it once, here, still puts it near the start of any log
        # file for a given driving system, which is what it's actually useful for: spotting an
        # unexpected config change/mismatch when reviewing a log later.
        if driving_sys_serial not in _logged_driving_systems:
            get_logger().debug(f'Driving system info:\n {self._driving_sys}')
            _logged_driving_systems.add(driving_sys_serial)

        # Transducer slot(s) -- see add_slot(). Call it at least once before using this protocol.
        self._slots = []

        back_up_ramp_shape = get_config_value(get_logger(), config, 'Ramp', 'Options',
                                              '').split('\n')[0]
        # Timing parameters
        self._timing_param = {
            # # Pulse
            'pulse_dur': float(get_config_value(get_logger(), config, 'Timing', 'Pulse_dur_ms',
                                                0.25)),  # [ms]
            'pulse_rep_int': float(get_config_value(
                get_logger(), config, 'Timing', 'Pulse_rep_int_ms', 20)),  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            'pulse_ramp_shape': get_config_value(get_logger(), config, 'Ramp', 'Default option',
                                                 back_up_ramp_shape),
            'pulse_ramp_dur': float(get_config_value(
                get_logger(), config, 'Timing', 'Pulse_ramp_dur_ms', 0)),  # [ms]

            # # Pulse train
            'pulse_train_dur': float(get_config_value(get_logger(), config, 'Timing',
                                                      'Pulse_train_dur_ms', 20)),  # [ms]
            'pulse_train_rep_int': float(get_config_value(get_logger(), config, 'Timing',
                                                          'Pulse_train_rep_int_ms', 20)),  # [ms]

            # Pulse train repetition
            'pulse_train_rep_dur': float(get_config_value(get_logger(), config, 'Timing',
                                                          'Pulse_train_rep_dur', 20)),  # [ms]

            }

    def __str__(self):
        """
        Returns a formatted string containing information about the protocol.

        Returns:
            str: Formatted information about the protocol.
        """
        info = ''

        for i, slot in enumerate(self._slots):
            info += f"--- Transducer slot {i} (counting from 0, i.e. slots[{i}]) --- \n "
            info += str(slot)

        info += f"Pulse duration [ms]: {self._timing_param['pulse_dur']} \n "
        info += f"Pulse repetition interval [ms]: {self._timing_param['pulse_rep_int']} \n "

        info += f"Pulse ramp shape: {self._timing_param['pulse_ramp_shape']} \n "
        info += f"Pulse ramp duration [ms]: {self._timing_param['pulse_ramp_dur']} \n "

        info += f"Pulse train duration [ms]: {self._timing_param['pulse_train_dur']} \n "

        info = (info + "Pulse train repetition interval [ms]:" +
                f" {self._timing_param['pulse_train_rep_int']} \n ")

        info = (info + "Pulse train repetition duration [ms]:"
                + f" {self._timing_param['pulse_train_rep_dur']} \n ")

        return info

    @property
    def driving_sys(self):
        """
        Getter method for the driving system. Read-only -- set once, at construction, and never
        changed afterward. Swapping which physical driving system a TUSProtocol targets mid-
        experiment isn't a realistic scenario (it would mean swapping the actual connected
        hardware), and reusing existing slots' focus/power values against a different driving
        system's calibration curves is risky even if it were: the same numeric value can mean a
        very different actual physical output once its calibration is a different pair
        entirely. Construct a new TUSProtocol and re-add_slot() every transducer instead.

        Returns:
            DrivingSystem: The driving system associated with the protocol.
        """

        return self._driving_sys

    @property
    def slots(self):
        """
        Getter method for this protocol's transducer slot(s).

        Returns:
            list(TransducerSlot): The transducer slot(s) of this protocol, in the order they
            were added.
        """

        return self._slots

    def get_power_options(self):
        """
        Returns a list of power options available for this protocol's driving system --
        available before any slot has been added yet, since add_slot() itself needs a valid
        power_option to call. Same list as any already-added slot's own get_power_options() (see
        TransducerSlot.get_power_options()), since it's simply forwarded from the same
        DrivingSystem.

        Returns:
            List[str]: Available power options, e.g. 'Global power [mW]', 'Max. pressure in free
            water [MPa]', 'Voltage [V]' or 'Amplitude [%]'.
        """

        return self._driving_sys.power_options

    def get_focus_options(self):
        """
        Returns a list of focus options available for this protocol's driving system --
        available before any slot has been added yet, since add_slot() itself needs a valid
        focus_option to call. Same list as any already-added slot's own get_focus_options() (see
        TransducerSlot.get_focus_options()), since it's simply forwarded from the same
        DrivingSystem.

        Returns:
            List[str]: Available focus options, e.g. 'Focus wrt exit plane [mm]' or 'Focus wrt
            mid bowl [mm]'.
        """

        return self._driving_sys.focus_options

    def add_slot(self, transducer_serial, focus_option, focus_value, power_option, power_value,
                 oper_freq=None, dephasing_degree=None):
        """
        Adds and fully configures one transducer slot: the transducer plus the focus and power
        parameter to drive it with. transducer_serial/focus_option/focus_value/power_option/
        power_value are all required -- a slot can never be added half-configured, which is what
        used to make the order transducer/focus/power were set in matter (a transducer change
        discarding a focus already chosen, focus/power set before a calibration curve was even
        loaded, etc.). oper_freq/dephasing_degree are optional -- unlike focus/power, neither has
        a calibration-ordering hazard (oper_freq already gets a sensible default from the
        transducer's own fund_freq; dephasing_degree's default is simply "no dephasing"), so
        there's no correctness reason they must be set here rather than on the returned slot
        afterward -- only offered as kwargs for convenience.

        To swap an already-added slot's transducer for a different one later, call
        protocol.slots[slot_index].update_transducer(...) directly -- same required arguments as
        here, since the new transducer's calibration curve/geometric range differ from the old
        one's, so old focus/power numbers can't just be assumed to still be correct.

        Parameters:
            transducer_serial (str): Serial number of the transducer for this slot. Must be
                                     compatible with this protocol's driving system (see
                                     DrivingSystem.tran_comp).
            focus_option (str): Which focus parameter to set, e.g. one of self.get_focus_options()
                                (as offered by this protocol's driving system, see
                                DrivingSystem.focus_options) -- 'Focus wrt exit plane [mm]' or
                                'Focus wrt mid bowl [mm]'.
            focus_value (float): The focus value [mm] for focus_option.
            power_option (str): Which power parameter to set, e.g. one of self.get_power_options()
                                (as offered by this protocol's driving system, see
                                DrivingSystem.power_options) -- 'Global power [mW]', 'Max.
                                pressure in free water [MPa]', 'Voltage [V]' or 'Amplitude [%]'.
            power_value (float or list(float)): The power value for power_option.
            oper_freq (int): Operating frequency [kHz]. Defaults to the transducer's own
                             fundamental frequency when not given.
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
                                            Defaults to None (no dephasing) when not given.

        Returns:
            TransducerSlot: The newly added, fully configured slot.
        """

        if len(self._slots) >= self._driving_sys.max_tran_slots:
            message = (f'{self._driving_sys.serial} supports at most ' +
                       f'{self._driving_sys.max_tran_slots} simultaneous transducer slot(s).')
            get_logger().critical(message)
            sys.exit(message)

        slot = TransducerSlot(self._driving_sys, self._engineering_mode)
        slot.update_transducer(transducer_serial, focus_option, focus_value, power_option,
                               power_value, oper_freq, dephasing_degree)

        self._slots.append(slot)
        self._validate_channel_count()

        return slot

    def _validate_channel_count(self):
        """
        Fails fast once the combined elements of all slots added so far exceeds this driving
        system's available channels -- deliberately not an exact-equality check here, since
        add_slot() may still be called again for a driving system with more than one slot
        (DrivingSystem.max_tran_slots > 1). Exact equality is enforced once, authoritatively, at
        actual send-time (see ControlDrivingSystem implementations' send_protocol()), which is
        also where "at least one slot must exist" is enforced.
        """

        total_elements = sum(slot.transducer.elements for slot in self._slots)
        if total_elements > self._driving_sys.available_ch:
            message = (f'Number of available channels ({self._driving_sys.available_ch}) is ' +
                       f'exceeded by the combined elements of the {len(self._slots)} ' +
                       f'transducer slot(s) ({total_elements}).')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def pulse_dur(self):
        """
        Getter method for the pulse duration -- see configure_timing(), the only way to set it.

        Returns:
            float: The pulse duration [ms].
        """

        return self._timing_param['pulse_dur']

    @property
    def pulse_rep_int(self):
        """
        Getter method for the pulse repetition interval -- see configure_timing(), the only way
        to set it.

        Returns:
            float: The pulse repetition interval [ms].
        """

        return self._timing_param['pulse_rep_int']

    def get_ramp_shapes(self):
        """
        Returns a list of available ramp shapes for pulse modulation.

        Returns:
            List[str]: Available ramp shapes.
        """

        return get_config_value(get_logger(), config, 'Ramp', 'Options', '').split('\n')

    @property
    def pulse_ramp_shape(self):
        """
        Getter method for the pulse ramp shape -- see configure_timing(), the only way to set it.

        Returns:
            str: The pulse ramp shape.
        """

        return self._timing_param['pulse_ramp_shape']

    @property
    def pulse_ramp_dur(self):
        """
        Getter method for the pulse ramp duration -- see configure_timing(), the only way to set
        it.

        Returns:
            float: The pulse ramp duration [ms].
        """

        return self._timing_param['pulse_ramp_dur']

    @property
    def pulse_train_dur(self):
        """
        Getter method for the pulse train duration -- see configure_timing(), the only way to
        set it.

        Returns:
            float: The pulse train duration [ms].
        """

        return self._timing_param['pulse_train_dur']

    @property
    def pulse_train_rep_int(self):
        """
        Getter method for the pulse train repetition interval -- see configure_timing(), the
        only way to set it.

        Returns:
            float: The pulse train repetition interval [ms].
        """

        return self._timing_param['pulse_train_rep_int']

    @property
    def pulse_train_rep_dur(self):
        """
        Getter method for the pulse train repetition duration -- see configure_timing(), the
        only way to set it.

        Returns:
            float: The pulse train repetition duration [ms].
        """

        return self._timing_param['pulse_train_rep_dur']

    def configure_timing(self, pulse_dur, pulse_rep_int=None, pulse_train_dur=None,
                         pulse_ramp_shape=None, pulse_ramp_dur=None,
                         pulse_train_rep_int=None, pulse_train_rep_dur=None):
        """
        The only way to set any timing parameter -- pulse_dur, pulse_rep_int, pulse_train_dur,
        pulse_train_rep_int, pulse_train_rep_dur, pulse_ramp_shape and pulse_ramp_dur all have
        getters only. There used to be a separate setter per parameter, each cascading its own
        value forward to every level above it (pulse_dur -> pulse_rep_int -> pulse_train_dur ->
        pulse_train_rep_int -> pulse_train_rep_dur), so calling them in the wrong order (e.g.
        pulse_train_dur before pulse_dur) silently clobbered an earlier value. Funneling every
        change through this one method removes that hazard at the source, rather than chasing
        each new ordering combination as it turns up.

        Trigger configuration (trigger_option/n_triggers) is not part of this method -- it's a
        parameter of IGT.wait_for_trigger() instead. pulse_train_rep_int/pulse_train_rep_dur
        below describe how many
        times this protocol's own pulse train repeats as a purely internal timing fact,
        independent of how the whole thing eventually gets triggered -- when trigger_option ends
        up being 'TriggerOnePulseTrain' at execute time, wait_for_trigger() overrides the actual
        repetition count from n_triggers instead and these two are simply not used for anything,
        harmless whether set here or not.

        pulse_dur is the only required parameter. Every level above it defaults to the level
        directly below it when not given (pulse_rep_int defaults to pulse_dur, pulse_train_dur to
        pulse_rep_int), so a single pulse train, repeated once, is already a complete,
        self-consistent result without giving anything else. pulse_ramp_shape/pulse_ramp_dur left
        as None do NOT inherit whatever was configured before -- they reset to their own safe/off
        default ("no ramping" and a ramp duration of 0) every single call, exactly like
        pulse_dur's own family resets to "repeat once" rather than reusing a stale value.

        pulse_train_rep_int/pulse_train_rep_dur may be given together, or just one of the two,
        or neither -- resolved in that order, not independently: pulse_train_rep_int defaults to
        pulse_train_dur (back-to-back repetition, no gap) when not given; only then does
        pulse_train_rep_dur default to that (possibly just-defaulted) interval when not given,
        i.e. "repeat exactly once" at whatever interval is now known. This means giving only
        pulse_train_rep_dur (a total span to repeat over) fills that span back-to-back, not "once"
        -- deriving pulse_train_rep_int to just match the given pulse_train_rep_dur instead would
        make the given value trivially self-referential (always exactly one repetition, no matter
        what was actually asked for). Giving only pulse_train_rep_int, or neither, both still
        collapse to "repeat exactly once".

        Parameters:
            pulse_dur (float): Pulse duration [ms].
            pulse_rep_int (float): Pulse repetition interval [ms].
            pulse_train_dur (float): Pulse train duration [ms].
            pulse_ramp_shape (str): Selected pulse ramp shape, e.g. one of
                                    self.get_ramp_shapes(). Defaults to "no ramping" when not
                                    given.
            pulse_ramp_dur (float): Ramp duration [ms]. Defaults to 0 when not given.
            pulse_train_rep_int (float): Pulse train repetition interval [ms].
            pulse_train_rep_dur (float): Pulse train repetition duration [s] -- see
                                        pulse_train_rep_int above.
        """

        # --- one pulse's own shape ---
        validate_value(pulse_dur, 'Pulse duration [ms] (pulse_dur)', True, True, True, False)
        self._timing_param['pulse_dur'] = pulse_dur

        if pulse_rep_int is None:
            pulse_rep_int = pulse_dur
        validate_value(pulse_rep_int, 'Pulse repetition interval [ms] (pulse_rep_int)',
                       True, True, True, False)
        self._timing_param['pulse_rep_int'] = pulse_rep_int

        rect_ramp = get_config_value(get_logger(), config, 'Ramp', 'option.rect',
                                     'Rectangular - no ramping')
        if pulse_ramp_shape is None:
            pulse_ramp_shape = rect_ramp
        if pulse_ramp_shape not in self.get_ramp_shapes():
            message = f'{pulse_ramp_shape} is not an available ramping option.'
            get_logger().critical(message)
            sys.exit(message)
        self._timing_param['pulse_ramp_shape'] = pulse_ramp_shape

        if pulse_ramp_dur is None:
            pulse_ramp_dur = 0
        validate_value(pulse_ramp_dur, 'Pulse ramp duration [ms] (pulse_ramp_dur)',
                       True, True, False, False)
        self._timing_param['pulse_ramp_dur'] = pulse_ramp_dur

        # --- the pulse train built from repeating that pulse ---
        if pulse_train_dur is None:
            pulse_train_dur = pulse_rep_int
        validate_value(pulse_train_dur, 'Pulse train duration [ms] (pulse_train_dur)',
                       True, True, True, False)
        self._timing_param['pulse_train_dur'] = pulse_train_dur

        # --- how the pulse train itself repeats -- a purely internal timing fact, independent
        # of how (or whether) the whole thing ends up externally triggered (see this method's
        # own docstring). pulse_train_rep_int is resolved FIRST, then pulse_train_rep_dur is
        # resolved using whatever pulse_train_rep_int turned out to be. Four cases:
        #   - neither given: both default to pulse_train_dur -> repeats exactly once.
        #   - only pulse_train_rep_int given: pulse_train_rep_dur defaults to match it ->
        #     still exactly once, just at that interval instead of pulse_train_dur.
        #   - only pulse_train_rep_dur given: pulse_train_rep_int defaults to
        #     pulse_train_dur, so the pulse train repeats back-to-back until it fills that
        #     total duration (e.g. pulse_train_rep_dur=5 s with pulse_train_dur=200 ms means
        #     25 repetitions, not 1).
        #   - both given: used exactly as given.
        if pulse_train_rep_int is None:
            pulse_train_rep_int = pulse_train_dur
        if pulse_train_rep_dur is None:
            pulse_train_rep_dur = pulse_train_rep_int / 1e3

        validate_value(pulse_train_rep_int,
                       'Pulse train repetition interval [ms] (pulse_train_rep_int)',
                       True, True, True, False)
        self._timing_param['pulse_train_rep_int'] = pulse_train_rep_int
        validate_value(pulse_train_rep_dur,
                       'Pulse train repetiton duration [s] (pulse_train_rep_dur)',
                       True, True, True, False)
        # convert pulse train repetition duration in seconds to milliseconds
        self._timing_param['pulse_train_rep_dur'] = pulse_train_rep_dur * 1e3
