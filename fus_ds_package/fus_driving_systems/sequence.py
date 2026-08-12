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

# Own packages
from fus_driving_systems import driving_system as ds
from fus_driving_systems.transducer_slot import TransducerSlot

from fus_driving_systems.calc_utils import validate_value
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.utils import get_config_value


class Sequence():
    """
    Class representing an ultrasound sequence.

    Everything genuinely per-transducer (transducer, focus, power, operating frequency,
    dephasing) lives on one or more TransducerSlot objects instead of directly on Sequence --
    see self.slots/self.add_slot(). A Sequence always has an explicit driving system (no
    config-fallback default: the caller must say which one) and starts with zero slots; call
    add_slot() at least once before sending it anywhere. There is no single-slot delegation on
    Sequence itself (no seq.press/seq.transducer/etc.) -- every per-transducer attribute is
    always addressed via seq.slots[i].<attribute>, whether there's one slot or several, so a
    script is never in doubt about which access style applies to a given driving system.

    Attributes:
        _buffer_num (int): Which of the driving system's hardware buffers this sequence targets,
                        starting at 0. Only used by IGT, to pre-load a sequence into a specific
                        buffer ahead of time and send/trigger it independently later -- see
                        DrivingSystem.max_buffers for how many buffers a given driving system
                        actually has (only 0 is valid for a driving system with no real buffer
                        concept at all, i.e. max_buffers == 1).
        _driving_sys (DrivingSystem): The driving system associated with the sequence.
        _trigger_option (str): chosen trigger option -- wait_for_trigger is derived from this,
                               not stored separately (see the wait_for_trigger property).
        _n_triggers (int): number of times a trigger will be sent.
        _slots (list(TransducerSlot)): The transducer slot(s) of this sequence -- see add_slot().
        _timing_param (dict.):
            _pulse_dur (float): Pulse duration of the sequence [ms].
            _pulse_rep_int (float): Pulse repetition interval of the sequence [ms].
            _pulse_ramp_shape (str): Shape of the ramping for the pulse.
            _pulse_ramp_dur (float): Ramp duration for the pulse [ms].
            _pulse_train_dur (float): Pulse train duration [ms].
            _pulse_train_rep_int (float): Pulse train repetition interval [ms].
            _pulse_train_rep_dur (float): Pulse train repetition duration [ms].

    Methods:
        info(): Returns a formatted string containing information about the sequence.
        get_ds_serials(): Returns a list of serial numbers for available driving systems.
        get_tran_serials(): Returns a list of serial numbers for available transducers.
        getters (attribute name without _) for above attributes. Every _timing_param field, plus
        _trigger_option/_n_triggers, has a getter only -- configure_timing() is the only way to
        set any of them, precisely because they cascade/interact with each other and are prone to
        ordering hazards if set individually and out of order.
    """

    def __init__(self, driving_sys_serial, engineering_mode=False):
        """
        Initializes a Sequence object with default values and loads configuration settings.

        Parameters:
            driving_sys_serial (str): Serial number of the driving system this sequence is for.
                                      Required -- there is no config-fallback default, since
                                      that default only ever existed to pre-fill a GUI dropdown
                                      (SonoRover One), not to pick silently for a script.
            engineering_mode (bool): Whether engineering-only power/focus options may be set
                                     directly. See _requires_engineering_mode() on TransducerSlot.
        """

        self._engineering_mode = engineering_mode

        self._buffer_num = 0

        self._driving_sys = ds.DrivingSystem()
        self._driving_sys.set_ds_info(driving_sys_serial)

        back_up_trigger_option = get_config_value(get_logger(), config, 'Trigger', 'Options',
                                                  '').split('\n')[0]

        self._trigger_option = get_config_value(get_logger(), config, 'Trigger', 'Default option',
                                                back_up_trigger_option)

        self._n_triggers = int(get_config_value(
            get_logger(), config, 'Trigger', 'Default n_triggers', 0))

        # Transducer slot(s) -- see add_slot(). Call it at least once before using this sequence.
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
        Returns a formatted string containing information about the sequence.

        Returns:
            str: Formatted information about the sequence.
        """
        info = ''

        info += f"Buffer number (for IGT purposes): {self._buffer_num} \n "
        info += str(self._driving_sys)

        info += f"Wait for trigger: {self.wait_for_trigger} \n "
        info += f"Trigger option: {self._trigger_option} \n "
        info += f"Number of times a trigger is sent: {self._n_triggers} \n "

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
    def buffer_num(self):
        """
        Getter method for the buffer number.

        Returns:
            int: Which of the driving system's hardware buffers this sequence targets,
                 starting at 0. See DrivingSystem.max_buffers for how many this driving system
                 actually has.
        """

        return self._buffer_num

    @buffer_num.setter
    def buffer_num(self, buffer_num):
        """
        Sets the buffer number.

        Parameters:
            buffer_num (int): Which of the driving system's hardware buffers this sequence
                              targets, starting at 0. Must be within
                              [0, driving_sys.max_buffers).
        """

        validate_value(buffer_num, 'Buffer number (buffer_num)', True, True, False, False)

        if buffer_num >= self._driving_sys.max_buffers:
            message = (f'Buffer number {buffer_num} is not valid for driving system ' +
                       f'{self._driving_sys.serial} -- it has {self._driving_sys.max_buffers} ' +
                       'buffer(s), so buffer_num must be between 0 and ' +
                       f'{self._driving_sys.max_buffers - 1}.')
            get_logger().critical(message)
            sys.exit(message)

        self._buffer_num = buffer_num

    @property
    def driving_sys(self):
        """
        Getter method for the driving system. Read-only -- set once, at construction, and never
        changed afterward. Swapping which physical driving system a Sequence targets mid-
        experiment isn't a realistic scenario (it would mean swapping the actual connected
        hardware), and reusing existing slots' focus/power values against a different driving
        system's calibration curves is risky even if it were: the same numeric value can mean a
        very different actual physical output once its calibration is a different pair
        entirely. Construct a new Sequence and re-add_slot() every transducer instead.

        Returns:
            DrivingSystem: The driving system associated with the sequence.
        """

        return self._driving_sys

    @property
    def wait_for_trigger(self):
        """
        Gets the wait_for_trigger parameter -- derived from trigger_option, not stored
        independently: True whenever trigger_option is anything other than the config's
        designated "no trigger" option (option.none). There is no setter -- to stop waiting for
        a trigger, set trigger_option to that "no trigger" option instead (mirroring how there is
        no separate "is ramping enabled" flag either, see pulse_ramp_shape).

        Returns:
            bool: Whether the driving system is currently configured to wait for a trigger.
        """
        none_option = get_config_value(get_logger(), config, 'Trigger', 'option.none', 'None')
        return self._trigger_option != none_option

    def get_trigger_options(self):
        """
        Returns a list of available trigger options.

        Returns:
            List[str]: Available trigger options.
        """

        return get_config_value(get_logger(), config, 'Trigger', 'Options', '').split('\n')

    @property
    def trigger_option(self):
        """
        Gets the trigger_option parameter -- see configure_timing(), the only way to set it.

        Returns:
            str: The chosen trigger option.
        """
        return self._trigger_option

    @property
    def n_triggers(self):
        """
        Gets the n_triggers parameter -- see configure_timing(), the only way to set it.

        Returns:
            int: The number of times a trigger will be sent.
        """
        return self._n_triggers

    @property
    def slots(self):
        """
        Getter method for this sequence's transducer slot(s).

        Returns:
            list(TransducerSlot): The transducer slot(s) of this sequence, in the order they
            were added.
        """

        return self._slots

    def get_power_options(self):
        """
        Returns a list of power options available for this sequence's driving system --
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
        Returns a list of focus options available for this sequence's driving system --
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
        seq.slots[slot_index].update_transducer(...) directly -- same required arguments as
        here, since the new transducer's calibration curve/geometric range differ from the old
        one's, so old focus/power numbers can't just be assumed to still be correct.

        Parameters:
            transducer_serial (str): Serial number of the transducer for this slot. Must be
                                     compatible with this sequence's driving system (see
                                     DrivingSystem.tran_comp).
            focus_option (str): Which focus parameter to set, e.g. one of self.get_focus_options()
                                (as offered by this sequence's driving system, see
                                DrivingSystem.focus_options) -- 'Focus wrt exit plane [mm]' or
                                'Focus wrt mid bowl [mm]'.
            focus_value (float): The focus value [mm] for focus_option.
            power_option (str): Which power parameter to set, e.g. one of self.get_power_options()
                                (as offered by this sequence's driving system, see
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
        actual send-time (see ControlDrivingSystem implementations' send_sequence()), which is
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
                         trigger_option=None, pulse_ramp_shape=None, pulse_ramp_dur=None,
                         n_triggers=None, pulse_train_rep_int=None, pulse_train_rep_dur=None):
        """
        The only way to set any timing/trigger parameter -- pulse_dur, pulse_rep_int,
        pulse_train_dur, pulse_train_rep_int, pulse_train_rep_dur, pulse_ramp_shape,
        pulse_ramp_dur, trigger_option and n_triggers all have getters only. There used to be a
        separate setter per parameter, each cascading its own value forward to every level above
        it (pulse_dur -> pulse_rep_int -> pulse_train_dur -> pulse_train_rep_int ->
        pulse_train_rep_dur), so calling them in the wrong order (e.g. pulse_train_dur before
        pulse_dur) silently clobbered an earlier value -- plus a second, easy-to-miss ordering
        hazard between trigger_option and pulse_train_rep_dur specifically (see n_triggers
        below). Funneling every change through this one method removes both hazards at the
        source, rather than chasing each new ordering combination as it turns up.

        pulse_dur is the only required parameter. Every level above it defaults to the level
        directly below it when not given (pulse_rep_int defaults to pulse_dur, pulse_train_dur to
        pulse_rep_int), so a single pulse train, repeated once, is already a complete,
        self-consistent result without giving anything else. trigger_option/pulse_ramp_shape/
        pulse_ramp_dur left as None do NOT inherit whatever was configured before -- they reset
        to their own safe/off default (the config's "no trigger" option; "no ramping" and a ramp
        duration of 0) every single call, exactly like pulse_dur's own family resets to "repeat
        once" rather than reusing a stale value. This matters most for trigger_option: since it
        decides whether the driving system waits for an external trigger at all (see
        wait_for_trigger), silently inheriting whatever an earlier, unrelated call (or an
        institution's own config default) happened to leave it at would be a real behavior
        change hiding behind an omitted argument -- resetting to "no trigger" instead means
        omitting it is always the same, safe, predictable choice. Pass trigger_option explicitly
        every time a trigger is actually wanted.

        n_triggers and (pulse_train_rep_int and/or pulse_train_rep_dur) are two mutually
        exclusive ways of saying "how many times does the pulse train repeat", and which one
        applies is decided by trigger_option, not left for the caller to match up.
        'TriggerOnePulseTrain' fires exactly one pulse train per external trigger received -- the
        driving system needs to know in advance how many triggers to expect, so n_triggers is
        required (not optional) for this option specifically, and pulse_train_rep_int/
        pulse_train_rep_dur don't apply at all. Every other trigger_option -- 'None' (no trigger
        at all) or 'TriggerWholeProtocol' (one trigger fires the entire, already
        fully-timed sequence at once, equivalent to executing it directly but gated behind a
        single external trigger) alike -- uses pulse_train_rep_int/pulse_train_rep_dur instead;
        n_triggers isn't valid here and is instead forced to 1 for
        'TriggerWholeProtocol' specifically (exactly one trigger is what that option
        needs), purely for ControlDrivingSystem implementations' own logging of "how many
        triggers are expected" -- it's never read to decide anything else on the hardware side
        for that trigger mode. Giving n_triggers together with either duration argument, or
        omitting n_triggers under 'TriggerOnePulseTrain', exits with a clear message.

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
            trigger_option (str): The chosen trigger option, e.g. one of
                                  self.get_trigger_options(). Defaults to the config's "no
                                  trigger" option when not given -- never inherited from an
                                  earlier call.
            pulse_ramp_shape (str): Selected pulse ramp shape, e.g. one of
                                    self.get_ramp_shapes(). Defaults to "no ramping" when not
                                    given.
            pulse_ramp_dur (float): Ramp duration [ms]. Defaults to 0 when not given.
            n_triggers (int): Number of times a trigger will be sent -- required when
                              trigger_option is 'TriggerOnePulseTrain' (one pulse train fires per
                              trigger), not valid for any other trigger_option.
            pulse_train_rep_int (float): Pulse train repetition interval [ms] -- only valid when
                                        trigger_option is anything other than
                                        'TriggerOnePulseTrain'.
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

        # --- how the pulse train itself repeats -- decided by which trigger mode applies ---
        # wait_for_trigger is derived from trigger_option, not set separately -- see its property.
        none_trigger = get_config_value(get_logger(), config, 'Trigger', 'option.none', 'None')
        if trigger_option is None:
            trigger_option = none_trigger
        if trigger_option not in self.get_trigger_options():
            message = f'{trigger_option} is not an available trigger option.'
            get_logger().critical(message)
            sys.exit(message)
        self._trigger_option = trigger_option

        rep_int_given = pulse_train_rep_int is not None
        rep_dur_given = pulse_train_rep_dur is not None

        seq_trigger = get_config_value(get_logger(), config, 'Trigger', 'option.seq',
                                       'TriggerOnePulseTrain')
        if self._trigger_option == seq_trigger:
            # Triggering per whole pulse train: n_triggers says how many times the trigger fires.
            # pulse_train_rep_int/pulse_train_rep_dur don't apply to this mode at all -- they
            # simply default to pulse_train_dur below, matching the "repeat once" default.
            if rep_int_given or rep_dur_given:
                message = ("pulse_train_rep_int/pulse_train_rep_dur don't apply when " +
                           f"trigger_option is '{seq_trigger}' -- give n_triggers instead.")
                get_logger().critical(message)
                sys.exit(message)
            # n_triggers is required here, unlike everywhere else in this method -- one pulse
            # train fires per trigger received, so the driving system genuinely needs to know in
            # advance how many triggers to expect; there is no sensible default to fall back to.
            if n_triggers is None:
                message = (f"n_triggers is required when trigger_option is '{seq_trigger}' -- " +
                           'it tells the driving system how many triggers to expect (one pulse ' +
                           'train fires per trigger).')
                get_logger().critical(message)
                sys.exit(message)
            validate_value(n_triggers, 'Number of anticipated triggers (n_triggers)',
                           True, True, True, False)
            self._n_triggers = n_triggers
            pulse_train_rep_int = pulse_train_dur
            pulse_train_rep_dur = pulse_train_dur / 1e3  # seconds -- this parameter's own unit
        else:
            # Every other trigger_option -- 'None' (no trigger at all) or
            # 'TriggerWholeProtocol' alike -- decides how many pulse train repetitions
            # happen via pulse_train_rep_int/pulse_train_rep_dur instead; n_triggers doesn't
            # apply here.
            if n_triggers is not None:
                message = (f"n_triggers only applies when trigger_option is '{seq_trigger}' " +
                           '-- give pulse_train_rep_int/pulse_train_rep_dur instead.')
                get_logger().critical(message)
                sys.exit(message)

            # pulse_train_rep_int is resolved FIRST, then pulse_train_rep_dur is resolved using
            # whatever pulse_train_rep_int turned out to be. Four cases:
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

            ptr_trigger = get_config_value(get_logger(), config, 'Trigger', 'option.ptr',
                                           'TriggerWholeProtocol')
            if self._trigger_option == ptr_trigger:
                # Purely for ControlDrivingSystem implementations' own logging of "how many
                # triggers are expected" -- never used to decide anything on the hardware side
                # for this trigger mode.
                self._n_triggers = 1

        validate_value(pulse_train_rep_int,
                       'Pulse train repetition interval [ms] (pulse_train_rep_int)',
                       True, True, True, False)
        self._timing_param['pulse_train_rep_int'] = pulse_train_rep_int
        validate_value(pulse_train_rep_dur,
                       'Pulse train repetiton duration [s] (pulse_train_rep_dur)',
                       True, True, True, False)
        # convert pulse train repetition duration in seconds to milliseconds
        self._timing_param['pulse_train_rep_dur'] = pulse_train_rep_dur * 1e3
