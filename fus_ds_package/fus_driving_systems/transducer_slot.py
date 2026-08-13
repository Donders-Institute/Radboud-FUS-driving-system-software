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
from fus_driving_systems import transducer as tran

from fus_driving_systems.calc_utils import (validate_value, extract_and_define_pp,
                                            safe_evaluate_pp, find_x_for_y_in_pp,
                                            format_or_unavailable)
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
from fus_driving_systems.utils import get_config_value


class TransducerSlot:
    """
    Class representing a single transducer, and everything about how it's driven, within a
    TUSProtocol -- a TUSProtocol holds one or more of these (one per physically connected
    transducer).

    Only ever constructed by TUSProtocol.add_slot(), which requires the transducer serial, the
    chosen focus option/value, and the chosen power option/value all together -- a slot can
    never exist half-configured (transducer picked but focus/power not yet chosen), which is
    what used to make the order power/focus/transducer were set in matter.

    Attributes:
        driving_sys (DrivingSystem): The driving system this slot's transducer is connected to
                                     (shared with the owning TUSProtocol, not a copy).
        _engineering_mode (bool): Whether TUSProtocol(engineering_mode=True) was set.
        _transducer (Transducer): The transducer associated with this slot.
        _oper_freq (int): Operating frequency of this slot [kHz].
        _dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
        None = no dephasing. If the list is equal to the number of elements, the phases based on
        the focus wrt bowl middle are overridden.
        _chosen_power (str): The chosen power parameter like amplitude or global power.
        _global_power (float): [SC] global power [W].
        _press (float): [IGT] maximum pressure in free water [MPa].
        _volt (float): [IGT] voltage [V].
        _ampl (float): [IGT] amplitude [%].
        _chosen_focus (str): The chosen focus parameter (wrt exit plane or mid bowl).
        _focus_wrt_exit_plane (float): Focal depth of this slot w.r.t. exit plane respresenting
                                       the FWHM middle [mm].
        _focus_wrt_mid_bowl (float): Focal depth of this slot w.r.t. transducer bowl middle
                                     respresenting the FWHM middle [mm].
        _ds_tran_combo (str): combination of driving system and transducer serial numbers.
        _conv_param (dict): Conversion parameters using piecewise polynomial functions for pressure
                           compensation with increasing focal depth.
            focus_curve_pp: Piecewise polynomial function for focus conversion
            power_curve_pp: Piecewise polynomial function for power conversion
            eq_curve_pp: Piecewise polynomial function for normalization factor calculation
            volt_curve_pp: Piecewise polynomial function for voltage conversion
        _eq_factor (float): [IGT] normalized pressure based on chosen focal depth wrt exit
                            plane [-]
        _eq_press_mpa (float): [IGT] equalized pressure based on chosen focal depth wrt exit
                               plane [MPa]
        _input_press_mpa (float): [IGT] input pressure based on chosen focal depth wrt exit
                                  plane [MPa]
        _calculated_ampl (float): [IGT] calculated amplitude to reach desired pressure on chosen
                                  focal depth wrt exit plane [-]

    Methods:
        getters and setters (attribute name without _) for above attributes.
    """

    def __init__(self, driving_sys, engineering_mode=False):
        """
        Initializes a bare TransducerSlot. Not meant to be called directly by application code --
        use TUSProtocol.add_slot() instead, which finishes configuring it (transducer, focus,
        power) before handing it back.

        Parameters:
            driving_sys (DrivingSystem): The driving system this slot's transducer will be
                                         connected to (the same object the owning TUSProtocol
                                         holds).
            engineering_mode (bool): Whether TUSProtocol(engineering_mode=True) was set.
        """

        self.driving_sys = driving_sys
        self._engineering_mode = engineering_mode

        # None, not a config-driven placeholder like it used to be here: every one of these is
        # always overwritten before it can ever be read -- either unconditionally, by the
        # transducer setter or configure() (both always run immediately after construction, see
        # TUSProtocol.add_slot()), or, for the power fields below, by whichever setter the chosen
        # power_option actually dispatches to (its own siblings included -- see e.g. press's
        # setter zeroing _ampl/_volt/_global_power for the same "0 looks like a genuine value"
        # reason None is used here instead of 0).
        self._chosen_power = None
        self._global_power = None  # SC: global power [W]
        self._press = None  # IGT: maximum pressure in free water [MPa]
        self._volt = None  # IGT: voltage [V]
        self._ampl = None  # IGT: amplitude [%]
        self._eq_factor = None  # IGT: normalized pressure
        self._input_press_mpa = None  # IGT: input pressure in free water [MPa]
        self._eq_press_mpa = None  # IGT: equalized pressure in free water [MPa]
        self._calculated_ampl = None  # IGT: calculated amplitude [%]

        # Degree used to dephase every nth element based on chosen degree. (None = no dephasing).
        self._dephasing_degree = None

        self._transducer = tran.Transducer()
        self._oper_freq = 0  # [kHz], set for real once transducer is assigned

        self._chosen_focus = None
        self._focus_wrt_mid_bowl = None
        self._focus_wrt_exit_plane = None

        # If applicable, retrieve conversion parameters
        self._conv_param = {
            "focus_curve_pp": None,
            "power_curve_pp": None,
            "eq_curve_pp": None,
            "volt_curve_pp": None,
            }

        # Set for real once transducer is assigned -- see _combo_is_active()'s docstring.
        self._ds_tran_combo = None

        # Paths to the four conversion-curve JSON files, populated by _update_conv_param() once
        # an active combo is known -- declared here purely so every instance attribute has one
        # canonical place it's introduced.
        self.eq_curve_file = None
        self.focus_curve_file = None
        self.power_curve_file = None
        self.volt_curve_file = None

    def __str__(self):
        """
        Returns a formatted string containing information about this slot.

        Returns:
            str: Formatted information about this slot.
        """
        info = ''

        info += str(self._transducer)

        info += "Chosen power option: "
        opt_glob_pow = get_config_value(get_logger(), config, 'Power', 'Option.glob_pow',
                                        'Global power [mW]')
        opt_ampl = get_config_value(get_logger(), config, 'Power', 'Option.ampl', 'Amplitude [%]')
        opt_press = get_config_value(get_logger(), config, 'Power', 'Option.press',
                                     'Max. pressure in free water [MPa]')
        opt_volt = get_config_value(get_logger(), config, 'Power', 'Option.volt', 'Voltage [V]')

        if self.chosen_power == opt_glob_pow:
            info += f"Global power [W]: {self._global_power} \n "
        elif self.chosen_power == opt_ampl:
            info += f"Amplitude [%]: {self._ampl} \n "
        elif self.chosen_power == opt_press:
            info += f"Maximum pressure in free water [MPa]: {self._press} \n "
            info += f"Input pressure in free water [MPa]: {self._input_press_mpa} \n "
            info += f"Equalized pressure in free water [MPa]: {self._eq_press_mpa} \n "
            info += f"Calculated amplitude [%]: {self._calculated_ampl} \n "
        elif self.chosen_power == opt_volt:
            info += f"Voltage [V]: {self._volt} \n "
        else:
            info += "Unknown power option \n "

        if self._combo_is_active():

            if self.chosen_power != opt_press and len(self._ampl) == 1:
                info += f"Maximum pressure in free water [MPa]: {self._press} \n "

            if self.chosen_power != opt_volt:
                info += f"Voltage [V]: {self._volt} \n "

            if self.chosen_power != opt_ampl:
                info += f"Amplitude [%]: {self._ampl} \n "

            # Information about piecewise polynomial fits
            info += "Conversion parameters using piecewise polynomial fits:\n "

            if self._conv_param["volt_curve_pp"] is not None:
                info += ("- Voltage to amplitude conversion: Using piecewise polynomial fit " +
                         f"of {self.volt_curve_file}\n ")

            if self._conv_param["power_curve_pp"] is not None:
                info += ("- Pressure to amplitude conversion: Using piecewise polynomial " +
                         f"fit of {self.power_curve_file}\n ")

            if self._conv_param["focus_curve_pp"] is not None:
                info += ("- Focus conversion: Using piecewise polynomial fit of " +
                         f"{self.focus_curve_file}\n ")

            if self._conv_param["eq_curve_pp"] is not None:
                info += ("- Normalization factor calculation: Using piecewise polynomial " +
                         f"fit of {self.eq_curve_file}\n ")

            info += ("Normalized pressure [-] based on chosen focal depth wrt exit plane of " +
                     f"{self._focus_wrt_exit_plane} [mm]: {self._eq_factor} \n ")

        elif self.chosen_power in self.driving_sys.native_power_params:
            info += (f"{self.chosen_power} is already {self.driving_sys.serial}'s native " +
                     "power parameter -- no pressure correction needed. \n ")
        else:
            info += ("Pressure correction with an increasing focal depth not available in " +
                     "the configuration file for this driving system and transducer " +
                     "combination. \n ")

        info += f"Operating frequency [kHz]: {self._oper_freq} \n "
        info += f"Focal depth wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n "
        info += f"Focal depth wrt bowl middle [mm]: {self._focus_wrt_mid_bowl} \n "
        info += f"Dephasing degree (None = no dephasing): {self.dephasing_degree} \n "

        return info

    @property
    def transducer(self):
        """
        Getter method for the transducer. Read-only -- see update_transducer(), the only way to
        set it (assigning a transducer without immediately re-configuring focus/power, whose
        calibration curve and geometric range are transducer-specific, would leave the slot
        half-configured).

        Returns:
            Transducer: The transducer associated with this slot.
        """

        return self._transducer

    def _set_transducer(self, serial):
        """
        Sets the transducer based on the provided serial number. Only called by
        update_transducer().

        Parameters:
            serial (str): Serial number of the transducer.
        """

        if serial not in self.driving_sys.tran_comp:
            message = (f'{serial} is not compatible with {self.driving_sys.serial}. Use one ' +
                       f'of the following instead: {self.driving_sys.tran_comp}.')
            get_logger().critical(message)
            sys.exit(message)

        self._transducer.set_transducer_info(serial)

        # Default operating frequency from the new transducer's own fundamental frequency --
        # add_slot()'s own oper_freq parameter relies on this as its fallback when not given.
        self._oper_freq = int(self._transducer.fund_freq)

        # Focus resets to None rather than being derived from the new transducer (this used to
        # default to the transducer's own min_foc specifically to serve SonoRover One's GUI, a
        # transducer dropdown auto-filling a focus display field -- SonoRover needs a rewrite
        # against this API regardless, so it should read Transducer.min_foc directly for that
        # instead of depending on this setter). Nothing in FDS's own TUSProtocol.add_slot() flow
        # ever observes this intermediate state: configure() always sets the real focus right
        # after. On an already-configured slot, changing the transducer invalidates whatever
        # focus was chosen for the old one (different geometry) -- resetting to None makes that
        # explicit rather than silently keeping a stale, no-longer-meaningful value.
        self._chosen_focus = None
        self._focus_wrt_exit_plane = None
        self._focus_wrt_mid_bowl = None

        self._refresh_combo()

    def _validate_element_count(self):
        """
        Fails fast if this slot's transducer has more elements than this driving system's
        channels-per-slot allow. Slots are always evenly divided, so that per-slot ceiling is
        simply available_ch / max_tran_slots -- there is no separate config key for it.
        """

        max_elements_per_slot = self.driving_sys.available_ch / self.driving_sys.max_tran_slots
        if self.transducer.elements > max_elements_per_slot:
            message = (f'{self.transducer.serial} has {self.transducer.elements} elements, ' +
                       f'more than the {max_elements_per_slot:.0f} channels available per ' +
                       f'slot on {self.driving_sys.serial} ({self.driving_sys.available_ch} ' +
                       f'available channels / {self.driving_sys.max_tran_slots} slots).')
            get_logger().critical(message)
            sys.exit(message)

    def update_transducer(self, transducer_serial, focus_option, focus_value, power_option,
                          power_value, oper_freq=None, dephasing_degree=None):
        """
        Assigns this slot's transducer, then (re-)applies focus and power -- required together
        with transducer_serial, since the new transducer's calibration curve and geometric
        range differ from any previous one's, so a focus/power value chosen before can't just be
        assumed to still be correct. Used both by TUSProtocol.add_slot() (right after constructing
        a bare slot) and directly by application code to swap an already-added slot's transducer
        later, e.g. protocol.slots[0].update_transducer(...).

        Parameters:
            transducer_serial (str): Serial number of the transducer. Must be compatible with
                                     this slot's driving system (see DrivingSystem.tran_comp).
            focus_option (str): Which focus parameter to set -- see TUSProtocol.add_slot().
            focus_value (float): The focus value [mm] for focus_option.
            power_option (str): Which power parameter to set -- see TUSProtocol.add_slot().
            power_value (float or list(float)): The power value for power_option.
            oper_freq (int): Operating frequency [kHz]. Defaults to the transducer's own
                             fundamental frequency when not given.
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
                                            Always defaults to None (no dephasing) when not
                                            given, rather than carrying over from a previous
                                            transducer -- a dephasing list is sized to a specific
                                            transducer's element count, so one built for a
                                            different transducer isn't safe to assume here.
        """

        self._set_transducer(transducer_serial)
        self._validate_element_count()

        if oper_freq is not None:
            self.oper_freq = oper_freq
        self.dephasing_degree = dephasing_degree

        self.configure(focus_option, focus_value, power_option, power_value)

    @property
    def oper_freq(self):
        """
        Getter method for the operating frequency.

        Returns:
            int: The operating frequency [kHz].
        """

        return self._oper_freq

    @oper_freq.setter
    def oper_freq(self, oper_freq):
        """
        Setter method for the operating frequency.

        Parameters:
            oper_freq (int): Operating frequency [kHz].
        """

        validate_value(oper_freq, 'Operating frequency [kHz] (oper_freq)',
                       True, True, True, False)
        self._oper_freq = int(oper_freq)

    def get_power_options(self):
        """
        Returns a list of power options actually available for this slot's driving system --
        not every power option the package knows about in general (see DrivingSystem.
        power_options, which this simply forwards).

        Returns:
            List[str]: Available power options.
        """

        return self.driving_sys.power_options

    def _requires_engineering_mode(self, section, option):
        """
        Determines whether setting the given power/focus option directly requires
        TUSProtocol(engineering_mode=True).

        Which options are engineering-only is an institutional safety policy, not a hardware
        property, so it's read from a config key ('Engineering-only options', under the given
        'Power'/'Focus' section) instead of being hardcoded here -- a different institution
        using this package can configure a different set, or none at all.

        Parameters:
            section (str): 'Power' or 'Focus'.
            option (str): The specific power/focus option being set.

        Returns:
            bool: True if engineering_mode is required to set this option directly.
        """

        engineering_only = get_config_value(
            get_logger(), config, section, 'Engineering-only options', '').split('\n')
        return option in engineering_only

    def _non_engineering_options(self, section):
        """
        Returns which of this driving system's power/focus options can be set right now,
        without TUSProtocol(engineering_mode=True) -- used to make an "engineering_mode required"
        error message actionable. A hardcoded suggested alternative could be wrong: it might not
        even be offered by this driving system, or a given institution could have configured it
        as engineering-only too (see _requires_engineering_mode()).

        Parameters:
            section (str): 'Power' or 'Focus'.

        Returns:
            List[str]: This driving system's own section options, minus whichever of them
            'Engineering-only options' names.
        """

        options = (self.driving_sys.power_options if section == 'Power'
                   else self.driving_sys.focus_options)
        return [option for option in options
                if not self._requires_engineering_mode(section, option)]

    @property
    def chosen_power(self):
        """
        Getter method for the chosen_power. Read-only -- there is no setter, since setting
        which power option is "chosen" without also setting its actual value (only
        _set_power()/configure() do both together) would leave this claiming an option is
        active when it was never actually given a value.

        Returns:
            str: The chosen power parameter.
        """

        return self._chosen_power

    @property
    def global_power(self):
        """
        Getter method for the global_power. Read-only -- see _set_power()/configure(), the only
        way to set it (setting power in isolation, without an already-correct focus, silently
        produces wrong derived values on driving systems that need a calibration curve to
        convert one to the other).

        Returns:
            float: The global power [W] for SC.
        """

        return self._global_power

    def _reset_power_fields(self):
        """
        Sets every parameter that determines the intensity to None -- 0 would look like a
        genuine, computed value for a power option that isn't even active right now. Shared by
        all four power setters so a future addition to this set only needs updating here.

        Also resets _input_press_mpa/_eq_press_mpa/_calculated_ampl -- the logging-only fields
        _convert_press_to_ampl() populates as a side effect of press's setter specifically. Only
        that one setter ever assigns them, so without this reset they'd survive untouched across
        a later switch to a different power option, still describing the previous press value
        rather than the driving system's actual, currently active choice.
        """

        self._global_power = None
        self._press = None
        self._volt = None
        self._ampl = None
        self._input_press_mpa = None
        self._eq_press_mpa = None
        self._calculated_ampl = None

    def _set_global_power(self, global_power):
        """
        Sets the global_power. Only called by _set_power() (see configure()).

        Parameters:
            global_power (float): The global power [W] for SC.
        """

        self._reset_power_fields()

        power_option = get_config_value(get_logger(), config, 'Power', 'Option.glob_pow',
                                        'Global power [mW]')

        if self._requires_engineering_mode('Power', power_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{power_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Power")}.')

        if power_option in self.driving_sys.power_options:
            validate_value(global_power, 'Global power [W] (global_power)',
                           True, True, False, False)
            self._global_power = global_power
            self._chosen_power = power_option
        else:
            message = ('Global power parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def press(self):
        """
        Getter method for the maximum pressure in free water. Read-only -- see
        _set_power()/configure(), the only way to set it (setting power in isolation, without
        an already-correct focus, silently produces wrong derived values on driving systems
        that need a calibration curve to convert one to the other).

        Returns:
            float: The maximum pressure in free water [MPa] for IGT.
        """

        return self._press

    def _set_press(self, press):
        """
        Sets the maximum pressure in free water. Only called by _set_power() (see configure()).

        Parameters:
            press (float): The maximum pressure in free water [MPa] for IGT.
        """

        self._reset_power_fields()

        power_option = get_config_value(get_logger(), config, 'Power', 'Option.press',
                                        'Max. pressure in free water [MPa]')

        if self._requires_engineering_mode('Power', power_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{power_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Power")}.')

        if power_option in self.driving_sys.power_options:
            # Fail fast: check whether this driving system can accept press at all before
            # validating anything about the specific value -- amplitude is not press's native
            # power parameter for every driving system, and converting to it requires an active
            # calibration, since there's no other way to produce a value this driving system's
            # hardware actually accepts.
            if (power_option not in self.driving_sys.native_power_params
                    and not self._combo_is_active()):
                message = ('No active calibration available to convert maximum pressure in ' +
                           f'free water to {self.driving_sys.native_power_params} for ' +
                           f'{self._ds_tran_combo}.')
                get_logger().critical(message)
                sys.exit(message)

            validate_value(press, 'Maximum pressure in free water [MPa] (press)',
                           True, True, False, False)

            max_press = float(get_config_value(get_logger(), config, 'Power',
                                               'Maximum pressure allowed in free water [MPa]',
                                               1.4))
            if press > max_press:
                message = (f'The set maximum pressure in free water of {press} [MPa] is ' +
                           f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                           ' your value.')
                get_logger().critical(message)
                sys.exit(message)

            self._press = press

            self._chosen_power = power_option

            if self._combo_is_active():
                # self._ampl is already None from the top of this setter -- if
                # _convert_press_to_ampl() raises below, it stays that way rather than some
                # stale value from before.
                result = self._convert_press_to_ampl(self._press, self._eq_factor)
                self._ampl = result['ampl']
                self._press = result['press']
                self._input_press_mpa = result['input_press_mpa']
                self._eq_press_mpa = result['eq_press_mpa']
                self._calculated_ampl = result['calculated_ampl']

                self._volt = self._convert_ampl_to_volt(self._ampl)

                get_logger().debug('New maximum pressure in free water value of ' +
                                   f'{self._press:.2f} [MPa] results in a voltage of ' +
                                   f'{format_or_unavailable(self._volt[0])} [V] and ' +
                                   f'an amplitude of {self._ampl[0]:.2f} [%].')
        else:
            message = ('Pressure parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def volt(self):
        """
        Getter method for the voltage. Read-only -- see _set_power()/configure(), the only way
        to set it (setting power in isolation, without an already-correct focus, silently
        produces wrong derived values on driving systems that need a calibration curve to
        convert one to the other).

        Returns:
            float: The voltage [V] for IGT.
        """

        return self._volt

    def _set_volt(self, volt):
        """
        Sets the voltage. Only called by _set_power() (see configure()).

        Parameters:
            volt (float): The voltage [V] for IGT.
        """

        self._reset_power_fields()

        power_option = get_config_value(
            get_logger(), config, 'Power', 'Option.volt', 'Voltage [V]')

        if self._requires_engineering_mode('Power', power_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{power_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Power")}.')

        if power_option in self.driving_sys.power_options:
            # Fail fast: check whether this driving system can accept volt at all before
            # validating anything about the specific value -- amplitude is not volt's native
            # power parameter for every driving system, and converting to it requires an active
            # calibration, since there's no other way to produce a value this driving system's
            # hardware actually accepts.
            if (power_option not in self.driving_sys.native_power_params
                    and not self._combo_is_active()):
                message = ('No active calibration available to convert voltage to ' +
                           f'{self.driving_sys.native_power_params} for ' +
                           f'{self._ds_tran_combo}.')
                get_logger().critical(message)
                sys.exit(message)

            if not isinstance(volt, list):
                volt = [volt]

            # Check if enough voltage entries are given
            n_entries = len(volt)
            if n_entries not in (self.driving_sys.available_ch, 1):
                message = (f'Number of voltage entries ({n_entries}) does not correspond to ' +
                           f'number of transducer elements ({self.driving_sys.available_ch}). ' +
                           'Only enter one voltage value or n-values equal to the number of ' +
                           'transducer elements.')
                get_logger().critical(message)
                sys.exit(message)

            validate_value(volt, 'Voltage [V] (volt)', True, True, False, False, True)

            self._volt = volt

            self._chosen_power = power_option

            if self._combo_is_active():
                # self._ampl is already None from the top of this setter -- if
                # _convert_volt_to_ampl() raises below, it stays that way rather than some stale
                # value from before.
                self._ampl = self._convert_volt_to_ampl(self._volt, self._eq_factor)

                # self._ampl/self._volt are always lists (even for a single value) -- format
                # them as such rather than special-casing the single-entry case.
                round_ampl = [f'{x:.2f}' for x in self._ampl]
                round_volt = [f'{x:.2f}' for x in self._volt]

                if n_entries == 1:
                    # _convert_volt_to_ampl() above always converts toward amplitude
                    # specifically, not necessarily this driving system's native power
                    # parameter in general, so this pressure is only derived for the log
                    # line below -- EXCEPT its
                    # max-pressure-exceeded check (inside _convert_ampl_to_press) is a deliberate
                    # exception to that: exceeding the configured safe limit is a safety
                    # decision for the engineer, not merely a logging concern, so it's
                    # intentionally left free to sys.exit() here same as anywhere else.
                    self._press = self._convert_ampl_to_press_for_logging(
                        self._ampl, self._eq_factor, '_volt', '_ampl')

                    get_logger().debug(
                        f'New voltage value of {round_volt} [V] results in a ' +
                        'maximum pressure in free water of ' +
                        f'{format_or_unavailable(self._press)} ' +
                        f' [MPa] and an amplitude of {round_ampl} [%].')
                else:
                    get_logger().debug(
                        'Pressure cannot be calculated when multiple voltages ' +
                        'are given.')
                    get_logger().debug(
                        f'New voltage value of {round_volt} [V] results in an ' +
                        f'amplitude of {round_ampl} [%].')

        else:
            message = ('Voltage parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def ampl(self):
        """
        Getter method for the amplitude. Read-only -- see _set_power()/configure(), the only way
        to set it (setting power in isolation, without an already-correct focus, silently
        produces wrong derived values on driving systems that need a calibration curve to
        convert one to the other).

        Returns:
            float: The amplitude array [%] for IGT: one value represents the value for all
            elements.
        """

        return self._ampl

    def _set_ampl(self, ampl):
        """
        Sets the amplitude. Only called by _set_power() (see configure()).

        Parameters:
            ampl (list(float)): The amplitude array [%] for IGT: one value represents the value
            for all elements.
        """

        self._reset_power_fields()

        power_option = get_config_value(get_logger(), config, 'Power',
                                        'Option.ampl', 'Amplitude [%]')

        if self._requires_engineering_mode('Power', power_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{power_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Power")}.')

        if power_option in self.driving_sys.power_options:
            # Fail fast: check whether this driving system can accept ampl at all before
            # validating anything about the specific value -- voltage is not ampl's native
            # power parameter for every driving system, and converting to it requires an active
            # calibration, since there's no other way to produce a value this driving system's
            # hardware actually accepts.
            if (power_option not in self.driving_sys.native_power_params
                    and not self._combo_is_active()):
                message = ('No active calibration available to convert amplitude to ' +
                           f'{self.driving_sys.native_power_params} for ' +
                           f'{self._ds_tran_combo}.')
                get_logger().critical(message)
                sys.exit(message)

            if not isinstance(ampl, list):
                ampl = [ampl]

            # Check if enough amplitude entries are given
            n_entries = len(ampl)
            if n_entries not in (self.driving_sys.available_ch, 1):
                message = (f'Number of amplitude entries ({n_entries}) does not correspond to ' +
                           f'number of transducer elements ({self.driving_sys.available_ch}). ' +
                           'Only enter one amplitude value or n-values equal to the number of ' +
                           'transducer elements.')
                get_logger().critical(message)
                sys.exit(message)

            validate_value(ampl, 'Amplitude [%] (ampl)', True, True, False, False, True)

            self._ampl = ampl

            self._chosen_power = power_option

            if self._combo_is_active():
                # Convert amplitude to voltage for logging
                self._volt = self._convert_ampl_to_volt(self._ampl)

                # self._ampl/self._volt are always lists (even for a single value) -- format
                # them as such rather than special-casing the single-entry case.
                round_ampl = [f'{x:.2f}' for x in self._ampl]
                # self._convert_ampl_to_volt() above can leave a None entry (calibration doesn't
                # cover this amplitude) -- this call is logging-only regardless (nothing
                # downstream currently sends self._volt to hardware), so a missing voltage
                # here only degrades the log message, never raises.
                round_volt = [format_or_unavailable(x) for x in self._volt]

                if n_entries == 1:
                    # Convert amplitude to pressure for logging -- EXCEPT
                    # _convert_ampl_to_press()'s own max-pressure-exceeded check is a deliberate
                    # exception to "logging-only": exceeding the configured safe limit
                    # is a safety decision for the engineer, not merely a logging
                    # concern, so it's intentionally left free to sys.exit() here same
                    # as anywhere else.
                    self._press = self._convert_ampl_to_press_for_logging(
                        self._ampl, self._eq_factor, '_ampl', '_volt')

                    get_logger().debug(
                        f'New amplitude value of {round_ampl} [%] results in a ' +
                        'maximum pressure in free water of ' +
                        f'{format_or_unavailable(self._press)} ' +
                        f'[MPa] and a voltage of {round_volt} [V].')
                else:
                    get_logger().debug(
                        'Amplitude array is given. Pressure cannot ' +
                        'be calculated for logging purposes.')
                    get_logger().debug(
                        f'New amplitude value of {round_ampl} [%] results in a ' +
                        f'voltage of {round_volt} [V].')
        else:
            message = ('Amplitude parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            get_logger().critical(message)
            sys.exit(message)

    def configure(self, focus_option, focus_value, power_option, power_value):
        """
        Sets this slot's focus and power together, in one call, always in the same safe order
        (focus first, then power -- compensation equations may need the just-updated focus to
        convert power correctly). Used by TUSProtocol.add_slot() to configure a brand new slot, and
        equally usable directly on an already-added slot (self.slots[i].configure(...)) to
        change its focus/power later -- e.g. mid-experiment -- without constructing an entirely
        new TUSProtocol just for that.

        Parameters:
            focus_option (str): Which focus parameter to set, e.g. one of self.get_focus_options()
                                -- 'Focus wrt exit plane [mm]' or 'Focus wrt mid bowl [mm]'.
            focus_value (float): The focus value [mm] for focus_option.
            power_option (str): Which power parameter to set, e.g. one of self.get_power_options()
                                -- 'Global power [mW]', 'Max. pressure in free water [MPa]',
                                'Voltage [V]' or 'Amplitude [%]'.
            power_value (float or list(float)): The power value for power_option.
        """

        self._set_focus(focus_option, focus_value)
        self._set_power(power_option, power_value)

    def _set_focus(self, focus_option, focus_value):
        """
        Sets focus_option's value on this slot, by forwarding to whichever of its two focus
        properties focus_option actually names.

        Parameters:
            focus_option (str): 'Focus wrt exit plane [mm]' or 'Focus wrt mid bowl [mm]'
                                (whichever config value 'Option.exit'/'Option.bowl' resolve to).
            focus_value (float): The focus value [mm].
        """

        exit_opt = get_config_value(get_logger(), config, 'Focus', 'Option.exit',
                                    'Focus wrt exit plane [mm]')
        bowl_opt = get_config_value(get_logger(), config, 'Focus', 'Option.bowl',
                                    'Focus wrt mid bowl [mm]')

        if focus_option == exit_opt:
            self._set_focus_wrt_exit_plane(focus_value)
        elif focus_option == bowl_opt:
            self._set_focus_wrt_mid_bowl(focus_value)
        else:
            message = (f'{focus_option} is not a valid focus option. Use one of: ' +
                       f'{exit_opt}, {bowl_opt}.')
            get_logger().critical(message)
            sys.exit(message)

    def _set_power(self, power_option, power_value):
        """
        Sets power_option's value on this slot, by forwarding to whichever of its four power
        properties power_option actually names.

        Parameters:
            power_option (str): 'Global power [mW]', 'Max. pressure in free water [MPa]',
                                'Voltage [V]' or 'Amplitude [%]' (whichever config value
                                'Option.glob_pow'/'Option.press'/'Option.volt'/'Option.ampl'
                                resolve to).
            power_value (float or list(float)): The power value.
        """

        glob_pow_opt = get_config_value(get_logger(), config, 'Power', 'Option.glob_pow',
                                        'Global power [mW]')
        press_opt = get_config_value(get_logger(), config, 'Power', 'Option.press',
                                     'Max. pressure in free water [MPa]')
        volt_opt = get_config_value(get_logger(), config, 'Power', 'Option.volt', 'Voltage [V]')
        ampl_opt = get_config_value(get_logger(), config, 'Power', 'Option.ampl', 'Amplitude [%]')

        if power_option == glob_pow_opt:
            self._set_global_power(power_value)
        elif power_option == press_opt:
            self._set_press(power_value)
        elif power_option == volt_opt:
            self._set_volt(power_value)
        elif power_option == ampl_opt:
            self._set_ampl(power_value)
        else:
            message = (f'{power_option} is not a valid power option. Use one of: ' +
                       f'{glob_pow_opt}, {press_opt}, {volt_opt}, {ampl_opt}.')
            get_logger().critical(message)
            sys.exit(message)

    def get_focus_options(self):
        """
        Returns a list of focus options actually available for this slot's driving system --
        not every focus option the package knows about in general (see DrivingSystem.
        focus_options, which this simply forwards).

        Returns:
            List[str]: Available focus options.
        """

        return self.driving_sys.focus_options

    @property
    def chosen_focus(self):
        """
        Getter method for the chosen_focus. Read-only -- there is no setter, since setting
        which focus option is "chosen" without also setting its actual value (only
        _set_focus()/configure() do both together) would leave this claiming an option is
        active when it was never actually given a value.

        Returns:
            str: The chosen focus parameter.
        """

        return self._chosen_focus

    @property
    def focus_wrt_exit_plane(self):
        """
        Getter method for the focal depth w.r.t. the exit plane representing the middle of the
        FWHM. Read-only -- see _set_focus()/configure(), the only way to set it (setting focus
        in isolation, with a power value already chosen for the old focus, silently produces
        wrong derived values on driving systems that need a calibration curve to convert one to
        the other).

        Returns:
            float: The focal depth [mm] w.r.t. the exit plane representing the middle of the FWHM.
        """

        return self._focus_wrt_exit_plane

    def _set_focus_wrt_exit_plane(self, focus):
        """
        Sets the focal depth w.r.t. the exit plane representing the middle of the FWHM. Only
        called by _set_focus() (see configure()).

        Parameters:
            focus (float): Focal depth [mm] w.r.t. the exit plane representing the middle of the
            FWHM.
        """

        focus_option = get_config_value(get_logger(), config, 'Focus', 'Option.exit',
                                        'Focus wrt exit plane [mm]')

        if self._requires_engineering_mode('Focus', focus_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{focus_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Focus")}.')

        if focus_option in self.driving_sys.focus_options:
            # Fail fast: check whether this driving system can accept focus_wrt_exit_plane
            # right now, before validating anything about the specific value -- mid bowl is not
            # exit plane's native focus parameter for every driving system, and converting to it
            # requires an active calibration, since there's no other way to produce a value
            # this driving system's hardware actually accepts.
            if (focus_option not in self.driving_sys.native_focus_params
                    and not self._combo_is_active()):
                message = ('No active calibration available to convert focus wrt exit plane ' +
                           f'to {self.driving_sys.native_focus_params} for ' +
                           f'{self._ds_tran_combo}.')
                get_logger().critical(message)
                sys.exit(message)

            validate_value(focus, 'Focus wrt exit plane [mm] (focus_wrt_exit_plane)',
                           True, True, False, False)

            if self._combo_is_active():
                # Ask focus_curve_pp itself whether this value is within its calibrated range,
                # rather than proxying via self._transducer.min_foc/max_foc -- those are
                # overwritten from eq_curve_pp's breaks (see _update_conv_param()), a different
                # curve. The two happen to have identical domains for every combo shipped today,
                # but nothing enforces that, so ask the curve that's actually about to be
                # evaluated (see issue #93).
                calc_mid_bowl, range_status = safe_evaluate_pp(
                    self._conv_param['focus_curve_pp'], focus)

                if range_status != 'in_range':
                    if focus_option not in self.driving_sys.native_focus_params:
                        # Mid bowl is native here -- it's what's actually sent to hardware, so
                        # an imprecise geometric approximation for it is not an acceptable
                        # fallback (unlike the native case below, where mid bowl is purely
                        # informational and never sent anywhere).
                        x_min = self._conv_param['focus_curve_pp'].x[0]
                        x_max = self._conv_param['focus_curve_pp'].x[-1]
                        message = (
                            f'Focus wrt exit plane of {focus} [mm] is outside of the active ' +
                            f"calibration curve's limits ({x_min:.2f} - {x_max:.2f} [mm]), " +
                            f'and {focus_option} is not native for {self._ds_tran_combo} -- ' +
                            'there is no way to accurately produce ' +
                            f'{self.driving_sys.native_focus_params} from this focus value.')
                        get_logger().critical(message)
                        sys.exit(message)

                    get_logger().warning(
                        f'Focus wrt exit plane of {focus} [mm] is outside of the active ' +
                        'calibration curve\'s range. Focus wrt mid bowl will be calculated ' +
                        f'based on exit plane distance of {self._transducer.exit_plane_dist} ' +
                        '[mm].')
                    calc_mid_bowl = focus + self._transducer.exit_plane_dist

                self._focus_wrt_mid_bowl = calc_mid_bowl
            else:
                # Check if focus is within the transducer's own physical range -- no curve to
                # consult here.
                if focus < self._transducer.min_foc or focus > self._transducer.max_foc:
                    message = (f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                               f'focus range of {self._transducer.min_foc} and ' +
                               f'{self._transducer.max_foc} [mm] of transducer ' +
                               f'{self._transducer.name}.')
                    get_logger().critical(message)
                    sys.exit(message)

                # Native and no curve available -- fall back to the simple, always-valid
                # geometric offset (only reached when native, since non-native + inactive
                # exits above).
                self._focus_wrt_mid_bowl = focus + self._transducer.exit_plane_dist

            self._chosen_focus = focus_option
            self._focus_wrt_exit_plane = focus

            get_logger().debug(
                f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

            if self._combo_is_active():
                # Needed as an input to _set_power()'s own calculation, which always runs right
                # after this within the same configure() call. ampl/press/volt are deliberately
                # not also recomputed/logged here (same reasoning already applied to
                # _update_conv_param()) -- _set_focus() only ever runs from configure(), which
                # always calls _set_power() immediately after, so any value computed here would
                # only ever describe a transient state _set_power() is about to replace (or, for
                # global_power, reset to None) regardless of which power option that turns out
                # to be.
                self._eq_factor = self._calc_eq_factor(self._focus_wrt_exit_plane)
        else:
            message = ('Focus wrt exit plane parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.focus_options}.')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def focus_wrt_mid_bowl(self):
        """
        Getter method for the focal depth w.r.t. middle of the transducer bowl representing the
        middle of the FWHM. Read-only -- see _set_focus()/configure(), the only way to set it
        (setting focus in isolation, with a power value already chosen for the old focus,
        silently produces wrong derived values on driving systems that need a calibration curve
        to convert one to the other).

        Returns:
            float: The focal depth [mm] w.r.t. middle of the transducer bowl representing the
            middle of the FWHM.
        """

        return self._focus_wrt_mid_bowl

    def _set_focus_wrt_mid_bowl(self, focus):
        """
        Sets the focal depth w.r.t. middle of the transducer bowl representing the middle of
        the FWHM. Only called by _set_focus() (see configure()).

        Parameters:
            focus (float): Focal depth [mm] w.r.t. middle of the transducer bowl representing the
            middle of the FWHM.
        """

        focus_option = get_config_value(get_logger(), config, 'Focus', 'Option.bowl',
                                        'Focus wrt mid bowl [mm]')

        if self._requires_engineering_mode('Focus', focus_option) and not self._engineering_mode:
            raise RuntimeError(
                f'{focus_option} mode is disabled. Enable engineering_mode, or use one of ' +
                f'the following options instead: {self._non_engineering_options("Focus")}.')

        if focus_option in self.driving_sys.focus_options:
            # Fail fast: check whether this driving system can accept focus_wrt_mid_bowl right
            # now, before validating anything about the specific value -- exit plane is not mid
            # bowl's native focus parameter for every driving system, and converting to it
            # requires an active calibration, since there's no other way to produce a value
            # this driving system's hardware actually accepts.
            if (focus_option not in self.driving_sys.native_focus_params
                    and not self._combo_is_active()):
                message = ('No active calibration available to convert focus wrt mid bowl ' +
                           f'to {self.driving_sys.native_focus_params} for ' +
                           f'{self._ds_tran_combo}.')
                get_logger().critical(message)
                sys.exit(message)

            validate_value(focus, 'Focus wrt mid bowl [mm] (focus_wrt_mid_bowl)',
                           True, True, False, False)

            if self._combo_is_active():
                target_y_value = focus
                self._focus_wrt_exit_plane, status = find_x_for_y_in_pp(
                    self._conv_param['focus_curve_pp'], target_y_value)

                if status:
                    get_logger().debug(
                        f"Found x value: {self._focus_wrt_exit_plane} for y = " +
                        f"{target_y_value}")

                    # Verify
                    calc_y = self._conv_param['focus_curve_pp'](self._focus_wrt_exit_plane)
                    get_logger().debug(
                        f"Verification: pp({self._focus_wrt_exit_plane}) = {calc_y}")
                else:
                    if focus_option not in self.driving_sys.native_focus_params:
                        # Mid bowl is not native here -- exit plane is what's actually native
                        # and would be sent to hardware, so an imprecise geometric approximation
                        # for it is not an acceptable fallback (unlike the native case below,
                        # where exit plane is purely informational and never sent anywhere).
                        message = (
                            f'Could not find an x value for y = {target_y_value} in the ' +
                            'active calibration curve, and ' +
                            f'{focus_option} is not native for {self._ds_tran_combo} -- ' +
                            'there is no way to accurately produce ' +
                            f'{self.driving_sys.native_focus_params} from this focus value.')
                        get_logger().critical(message)
                        sys.exit(message)

                    get_logger().warning(
                        f"Could not find an x value for y = {target_y_value}. " +
                        'Focus wrt exit plane will be calculated based on ' +
                        'exit plane distance of ' +
                        f'{self._transducer.exit_plane_dist} [mm].')

                    self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist
            else:
                # Native and no curve available -- fall back to the simple, always-valid
                # geometric offset (only reached when native, since non-native + inactive
                # exits above).
                self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

            # Check if focus is within range if compensation equations are not applicable
            if (self._focus_wrt_exit_plane < self._transducer.min_foc
                    or self._focus_wrt_exit_plane > self._transducer.max_foc):
                message = (
                    f'Focus wrt exit plane of {self._focus_wrt_exit_plane} [mm] is not ' +
                    'within the set ' +
                    f'focus range of {self._transducer.min_foc} and ' +
                    f'{self._transducer.max_foc} [mm] of transducer ' +
                    f'{self._transducer.name}.')
                get_logger().critical(message)
                sys.exit(message)

            self._chosen_focus = focus_option

            self._focus_wrt_mid_bowl = focus

            get_logger().debug(
                f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

            if self._combo_is_active():
                # Needed as an input to _set_power()'s own calculation, which always runs right
                # after this within the same configure() call. ampl/press/volt are deliberately
                # not also recomputed/logged here (same reasoning already applied to
                # _update_conv_param()) -- _set_focus() only ever runs from configure(), which
                # always calls _set_power() immediately after, so any value computed here would
                # only ever describe a transient state _set_power() is about to replace (or, for
                # global_power, reset to None) regardless of which power option that turns out
                # to be.
                self._eq_factor = self._calc_eq_factor(self._focus_wrt_exit_plane)
        else:
            message = ('Focus wrt mid bowl parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.focus_options}.')
            get_logger().critical(message)
            sys.exit(message)

    @property
    def dephasing_degree(self):
        """
        Getter method for the dephasing degree.

        Returns:
            list(float): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases
            based on the focus are overriden.
        """

        return self._dephasing_degree

    @dephasing_degree.setter
    def dephasing_degree(self, dephasing_degree):
        """
        Setter method for the dephasing degree.

        Parameters:
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases
            based on the focus wrt middle of the transducer bowl are overriden.
        """

        self._dephasing_degree = dephasing_degree

    @property
    def eq_factor(self):
        """
        Getter method for the normalized pressure based on chosen focal depth wrt exit plane [-].

        Returns:
            float: The normalized pressure based on chosen focal depth wrt exit plane [-].
        """

        return self._eq_factor

    @property
    def input_press_mpa(self):
        """
        Getter method for the desired maximum pressure in free water at chosen focal depth wrt exit
        plane [MPa].

        Returns:
            float: The desired maximum pressure in free water at chosen focal depth wrt exit plane
            [MPa].
        """

        return self._input_press_mpa

    @property
    def eq_press_mpa(self):
        """
        Getter method for the equalized pressure at chosen focal depth wrt exit plane [MPa]
        (= desired pressure * eq_factor).

        Returns:
            float: The equalized pressure at chosen focal depth wrt exit plane [MPa]
            (= desired pressure * eq_factor).
        """

        return self._eq_press_mpa

    @property
    def calculated_ampl(self):
        """
        Getter method for the calculated amplitude to reach desired pressure at chosen focal depth
        wrt exit plane [-].

        Returns:
            float: The calculated amplitude to reach desired pressure at chosen focal depth wrt
            exit plane [-].
        """

        return self._calculated_ampl

    def _combo_is_active(self):
        """
        Determines whether an active calibration exists for this slot's driving-system/transducer
        pair -- i.e. whether curve-based power/focus conversion is actually possible right now.

        Returns:
            bool: True only if an 'Equipment.Combination.<ds_tran_combo>' section exists for the
            current pair AND its 'Active?' key is True. False (no warning) when the section is
            simply absent -- normal for equipment that never needs curve-based conversion at all.
        """

        section = 'Equipment.Combination.' + self._ds_tran_combo
        if section not in config:
            return False
        return get_config_value(get_logger(), config, section, 'Active?', 'True') == 'True'

    def _refresh_combo(self):
        """
        Recomputes this slot's ds_tran_combo (driving system serial + transducer serial) and, if
        an active calibration now exists for that pair, reloads its conversion parameters.

        Called whenever either half of the pair could have changed: this slot's own transducer
        setter, and TUSProtocol.driving_sys's setter (once per existing slot, since driving_sys is
        shared -- mutated in place -- across every slot of the same TUSProtocol).
        """

        combo_sign = get_config_value(get_logger(), config, 'Equipment', 'Combination sign', '~')
        self._ds_tran_combo = combo_sign.join([self.driving_sys.serial, self._transducer.serial])
        if self._combo_is_active():
            self._update_conv_param()

    def _update_conv_param(self):
        """
        (Re)loads this slot's four calibration curves (focus/power/voltage/equalization) from
        the active combo's config files, and refreshes the transducer's min_foc/max_foc from the
        equalization curve's breaks. Only called by _refresh_combo(), itself only called by
        _set_transducer() -- which always resets focus to None right before this runs, so
        eq_factor is never computed here; _set_focus()'s own setters do that once configure()
        provides a real focus value moments later.

        min_foc/max_foc are deliberately sourced from the equalization curve alone, not e.g. the
        intersection of every curve's own domain -- that would make which curve ends up as the
        binding constraint vary per transducer, turning min_foc/max_foc into a moving target
        instead of one predictable thing. Every actual curve evaluation is independently
        range-checked against its own domain anyway (see safe_evaluate_pp usages elsewhere in
        this class), so nothing relies on eq_curve_pp's domain being an accurate stand-in for any
        other curve's. The warning below only exists to flag likely-bad calibration data early
        (see issue #93), not to guard correctness.
        """

        section_name = 'Equipment.Combination.' + self._ds_tran_combo

        self.eq_curve_file = get_config_value(get_logger(), config, section_name,
                                              'EqualizationCurveFit json file', None, True)

        self.focus_curve_file = get_config_value(get_logger(), config, section_name,
                                                 'FocusCurveFit json file', None, True)

        self.power_curve_file = get_config_value(get_logger(), config, section_name,
                                                 'PowerCurveFit json file', None, True)

        self.volt_curve_file = get_config_value(get_logger(), config, section_name,
                                                'VoltageCurveFit json file', None, True)

        eq_pp, eq_breaks = extract_and_define_pp(self.eq_curve_file, return_breaks=True)
        focus_pp = extract_and_define_pp(self.focus_curve_file)

        self._conv_param = {
            "focus_curve_pp": focus_pp,
            "power_curve_pp": extract_and_define_pp(self.power_curve_file),
            "eq_curve_pp": eq_pp,
            "volt_curve_pp": extract_and_define_pp(self.volt_curve_file),
            }

        self.transducer.min_foc = min(eq_breaks)
        self.transducer.max_foc = max(eq_breaks)

        # focus_curve_pp shares the same x-axis (focus wrt exit plane) as eq_curve_pp -- the only
        # other curve that does (power_curve_pp/volt_curve_pp are on a different axis entirely,
        # not comparable here). A mismatch doesn't produce a wrong result anywhere (every curve
        # evaluation checks its own domain independently), but it likely means this combo's
        # calibration data has a real problem worth looking at.
        focus_min, focus_max = focus_pp.x[0], focus_pp.x[-1]
        if focus_min < self.transducer.min_foc or focus_max > self.transducer.max_foc:
            get_logger().warning(
                f"focus_curve_pp's domain ({focus_min:.2f} - {focus_max:.2f} [mm]) for " +
                f"{self._ds_tran_combo} extends beyond the equalization curve's own domain " +
                f"({self.transducer.min_foc:.2f} - {self.transducer.max_foc:.2f} [mm]) that " +
                "min_foc/max_foc are derived from -- some focus_wrt_exit_plane values may be " +
                "accepted by one curve and rejected by the other. Check this combo's " +
                "calibration data.")

    def _calc_eq_factor(self, focus_wrt_exit_plane):
        """
        Calculate equalization factor of the pressure vs. focal depth wrt exit plane [mm] equation.

        Parameters:
            focus_wrt_exit_plane (float): Focal depth wrt exit plane [mm].

        Returns:
            float: The equalization factor [-].
        """

        try:
            eq_factor, range_status = safe_evaluate_pp(
                self._conv_param['eq_curve_pp'], focus_wrt_exit_plane)
        except (TypeError, ValueError) as e:
            # safe_evaluate_pp's own range comparison is what actually raises here (a string,
            # for instance, can't be compared with '<') -- pp(x_value) itself would silently
            # return NaN rather than raise (extrapolate=False), so this is reachable only for a
            # focus_wrt_exit_plane that isn't numeric at all, never for a merely out-of-range one.
            message = (f'{e} \n Focus wrt exit plane of {focus_wrt_exit_plane} is not a valid ' +
                       'numeric value.')
            get_logger().critical(message)
            sys.exit(message)

        if range_status != 'in_range':
            x_min = self._conv_param['eq_curve_pp'].x[0]
            x_max = self._conv_param['eq_curve_pp'].x[-1]
            message = (
                f'Focus wrt exit plane of {focus_wrt_exit_plane} [mm] is outside of the ' +
                f"active calibration curve's limits ({x_min:.2f} - {x_max:.2f} [mm]).")
            get_logger().critical(message)
            sys.exit(message)

        return eq_factor

    def _convert_ampl_to_volt(self, ampl):
        """
        Convert amplitude [%] to voltage [V] for the given amplitude values.

        Parameters:
            ampl (list(float)): Amplitude [%] entries to convert.

        Returns:
            list(float or None): Voltage [V] for each entry, or None where the calibration curve
            doesn't cover that amplitude.
        """

        volt = []
        for a in ampl:
            volt_value, status = find_x_for_y_in_pp(self._conv_param['volt_curve_pp'], a)

            if status:
                get_logger().debug(f"Found x value: {volt_value} for y = {a}")

                # Verify
                calc_y = self._conv_param['volt_curve_pp'](volt_value)
                get_logger().debug(f"Verification: pp({volt_value}) = {calc_y}")

            else:
                # None, not 0: 0 would look like a genuine, calculated voltage to any later
                # read of self._volt, when really no value could be found at all.
                volt_value = None
                get_logger().error(f"Could not find a voltage value for amplitude = {a}")

            volt.append(volt_value)

        return volt

    def _convert_press_to_ampl(self, press, eq_factor):
        """
        Convert maximum pressure in free water to amplitude [%] for the given pressure value.

        Parameters:
            press (float): Maximum pressure in free water [MPa].
            eq_factor (float): Equalization factor [-] for the current focal depth.

        Returns:
            dict: 'ampl' (list(float)), plus 'press' (float, unchanged from the given value even
            when ampl had to be clamped to 0% -- see the calc_ampl < 0 branch below for why),
            'input_press_mpa', 'eq_press_mpa', and 'calculated_ampl' (all logging-only accessory
            fields).
        """

        press_pa = press * 1e6  # convert to Pa

        x_value = press_pa * eq_factor
        calc_ampl, range_status = safe_evaluate_pp(self._conv_param['power_curve_pp'], x_value)

        # Save additional information for logging purposes
        input_press_mpa = press
        eq_press_mpa = x_value / 1e6
        calculated_ampl = calc_ampl

        if range_status in ("above_range", "below_range"):
            x_min_mpa = self._conv_param['power_curve_pp'].x[0] / 1e6
            x_max_mpa = self._conv_param['power_curve_pp'].x[-1] / 1e6
            # Converted back to press-MPa (dividing the curve's own Pa-based limits by
            # eq_factor) -- the user sets press, not the internal "equalized pressure" this
            # curve is actually fit against, so the bounds shown must be in the units they
            # actually control. These bounds are specific to the current focal depth (eq_factor
            # is derived from it) -- they shift if focus changes.
            press_min = x_min_mpa / eq_factor
            press_max = x_max_mpa / eq_factor
            message = (
                f'Maximum pressure in free water of {input_press_mpa} [MPa] is outside of ' +
                'the calibration curve\'s range at the current focal depth (equalization ' +
                f'factor {eq_factor:.4f}) -- must be between {press_min:.2f} and ' +
                f'{press_max:.2f} [MPa] for this chosen focal depth. Change input value.')
            get_logger().critical(message)
            sys.exit(message)

        if calc_ampl > 100:
            clamped_ampl = [100]
            # Provisional values, computed purely to describe the rejected request in the
            # message below -- this request is being rejected outright, so unlike the <0 case,
            # nothing here is kept.
            press_for_msg = self._convert_ampl_to_press(clamped_ampl, eq_factor)
            volt_for_msg = self._convert_ampl_to_volt(clamped_ampl)

            message = (f'Calculated amplitude of {calc_ampl:.2f} exceeds 100%. A pressure ' +
                       f'of {format_or_unavailable(press_for_msg)} [MPa] and/or a voltage ' +
                       f'of {format_or_unavailable(volt_for_msg[0])} [V] will result in an ' +
                       'amplitude of 100% at the current focal depth. Change input value.')
            get_logger().critical(message)
            sys.exit(message)

        if calc_ampl < 0:
            get_logger().debug(
                f'Calculated amplitude of {calc_ampl:.2f} is below 0%, so cut off ' +
                'the amplitude at 0%.')
            ampl = [0]
            # press is validated non-negative before this method is ever called (see press's
            # own setter), and the domain check above already exits for anything genuinely
            # outside the curve's range -- so reaching this branch at all means press was
            # already a legitimate request, just close enough to this curve's own effective
            # floor that its fit dips slightly negative there. Keep press exactly as given
            # rather than re-deriving it through an independent inverse lookup
            # (_convert_ampl_to_press -> find_x_for_y_in_pp), which is subject to the exact same
            # curve-fit imprecision approached from the other direction -- e.g. a genuine
            # press=0 request would otherwise come back as some small non-zero "corrected"
            # value purely from that round-trip, even though 0 was already the right answer.
        else:
            ampl = [round(float(calc_ampl), 2)]

        return {
            'ampl': ampl,
            'press': press,
            'input_press_mpa': input_press_mpa,
            'eq_press_mpa': eq_press_mpa,
            'calculated_ampl': calculated_ampl,
            }

    def _convert_volt_to_ampl(self, volt, eq_factor):
        """
        Convert voltage [V] to amplitude [%] for the given voltage values.

        Parameters:
            volt (list(float)): Voltage [V] entries to convert.
            eq_factor (float): Equalization factor [-] for the current focal depth -- only used
                to describe a rejected (>100%) request in its error message.

        Returns:
            list(float): Amplitude [%] for each entry.
        """

        ampl = []
        for v in volt:
            calc_ampl, range_status = safe_evaluate_pp(self._conv_param['volt_curve_pp'], v)

            if range_status in ("above_range", "below_range"):
                # A voltage outside the calibration curve's own domain -- same treatment as
                # _convert_press_to_ampl()'s domain check, not the calc_ampl > 100/< 0 clamps
                # below (those are for an in-range voltage whose curve-fit result happens to
                # spill slightly past 0/100, not for a voltage the curve was never fit to
                # describe at all).
                x_min = self._conv_param['volt_curve_pp'].x[0]
                x_max = self._conv_param['volt_curve_pp'].x[-1]
                message = (f'Voltage of {v} [V] is outside of pp limits ({x_min:.2f} - ' +
                           f'{x_max:.2f} [V]). Change input value.')
                get_logger().critical(message)
                sys.exit(message)

            if calc_ampl > 100:
                # Provisional values, computed purely to describe the rejected request in the
                # message below -- this request is being rejected outright.
                press_for_msg = self._convert_ampl_to_press([100], eq_factor)
                volt_for_msg = self._convert_ampl_to_volt([100])

                message = ('Calculated amplitude exceeds 100%. A pressure of ' +
                           f'{format_or_unavailable(press_for_msg)} [MPa] and/or a voltage of ' +
                           f'{format_or_unavailable(volt_for_msg[0])} [V] will result in an ' +
                           'amplitude of 100% at the current focal depth. Change input value.')

                get_logger().critical(message)
                sys.exit(message)

            if calc_ampl < 0:
                get_logger().debug(
                    f'Calculated amplitude of {calc_ampl:.2f} is below 0%, so cut off ' +
                    'the amplitude at 0%.')
                calc_ampl = 0

            ampl.append(round(float(calc_ampl), 2))

        return ampl

    def _convert_ampl_to_press(self, ampl, eq_factor):
        """
        Convert amplitude [%] to maximum pressure in free water for the given amplitude value.
        Only meaningful for a single value: a multi-channel amplitude array has no one pressure
        that represents it, so this rejects more than one entry outright rather than silently
        deriving a value from just the first and ignoring the rest.

        Parameters:
            ampl (list(float)): Amplitude [%], exactly one entry.
            eq_factor (float): Equalization factor [-] for the current focal depth.

        Returns:
            float or None: Maximum pressure in free water [MPa], or None if the calibration
            curve doesn't cover this amplitude.
        """

        if len(ampl) != 1:
            message = ('_convert_ampl_to_press() only produces a meaningful result for a single ' +
                       f'amplitude value -- got {len(ampl)} entries, which has no one ' +
                       'pressure that represents the whole array.')
            get_logger().critical(message)
            sys.exit(message)

        target_y_value = ampl[0]
        press_pa_with_eq_fact, status = find_x_for_y_in_pp(self._conv_param['power_curve_pp'],
                                                           target_y_value)

        if status:
            get_logger().debug(f"Found x value: {press_pa_with_eq_fact} for y = {target_y_value}")

            # Verify
            calc_y = self._conv_param['power_curve_pp'](press_pa_with_eq_fact)
            get_logger().debug(f"Verification: pp({press_pa_with_eq_fact}) = {calc_y}")

            press_mpa = (press_pa_with_eq_fact / eq_factor) * 1e-6
            max_press = float(get_config_value(
                get_logger(), config, 'Power',
                'Maximum pressure allowed in free water [MPa]', 1.4))
            if press_mpa > max_press:
                message = (f'The set maximum pressure in free water of {press_mpa} [MPa] is ' +
                           f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                           ' your value.')
                get_logger().critical(message)
                sys.exit(message)

            return press_mpa  # MPa

        get_logger().error(f"Could not find a pressure value for amplitude = {target_y_value}")
        return None

    def _convert_ampl_to_press_for_logging(self, ampl, eq_factor, *sibling_fields):
        """
        Calls _convert_ampl_to_press() purely to produce a log line (the value actually sent to
        hardware was already determined independently by the caller). If the derived pressure
        exceeds the configured maximum, _convert_ampl_to_press() exits -- the whole request is
        being rejected in that case, so self._press (every caller assigns this method's return
        value to it) and `sibling_fields` (e.g. '_volt', '_ampl') are all cleared to None too, so
        none of them look like a valid, current result afterwards, before the exit is re-raised.
        This clearing used to happen inside _convert_ampl_to_press() itself (an upfront
        self._press = None reset) -- now that it's a pure function with no self._press of its
        own to protect, this wrapper is what has to guarantee it instead.

        Parameters:
            ampl (list(float)): Amplitude [%] to derive the pressure from.
            eq_factor (float): Equalization factor [-] for the current focal depth.
            sibling_fields (str): Names of self's attributes to clear to None on exit.

        Returns:
            float or None: See _convert_ampl_to_press().
        """

        try:
            return self._convert_ampl_to_press(ampl, eq_factor)
        except SystemExit:
            self._press = None
            for field in sibling_fields:
                setattr(self, field, None)
            raise
