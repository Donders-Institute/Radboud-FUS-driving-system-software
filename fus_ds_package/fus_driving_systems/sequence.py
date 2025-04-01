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

# Miscellaneous packages
import json
import numpy as np
import pkg_resources
from scipy.interpolate import PPoly
from scipy import optimize


# Own packages
from fus_driving_systems import driving_system as ds
from fus_driving_systems import transducer as tran

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import logger
from fus_driving_systems.utils import get_config_value


class Sequence():
    """
    Class representing an ultrasound sequence.

    Attributes:
        _seq_num (int): Number of sequence starting at zero. Currently only used to differentiate
                        and send multiple sequences to the IGT system.
        _equip_combos (list): List of driving system and transducer combinations that require
        pressure compensation with an increasing focal depth.
        _driving_sys (DrivingSystem): The driving system associated with the sequence.
        _wait_for_trigger (bool): Boolean indicating if the driving system is waiting for a trigger.
        _trigger_option (str): chosen trigger option.
        _n_triggers (int): number of times a trigger will be sent.
        _transducer (Transducer): The transducer associated with the sequence.
        _oper_freq (int): Operating frequency of the sequence [kHz].
        _dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
        None = no dephasing. If the list is equal to the number of elements, the phases based on
        the focus wrt bowl middle are overridden.
        _chosen_power (str): The chosen power parameter like amplitude or global power.
        _global_power (float): [SC] global power [W].
        _press (float): [IGT] maximum pressure in free water [MPa].
        _volt (float): [IGT] voltage [V].
        _ampl (float): [IGT] amplitude [%].
        _chosen_focus (str): The chosen focus parameter (wrt exit plane or mid bowl).
        _focus_wrt_exit_plane (float): Focal depth of the sequence w.r.t. exit plane respresenting
                                       the FWHM middle [mm].
        _focus_wrt_mid_bowl (float): Focal depth of the sequence w.r.t. transducer bowl middle
                                     respresenting the FWHM middle [mm].
        _ds_tran_combo (str): combination of driving system and transducer serial numbers.
        _conv_param (dict): Conversion parameters using piecewise polynomial functions for pressure
                           compensation with increasing focal depth.
            focus_curve_pp: Piecewise polynomial function for focus conversion
            power_curve_pp: Piecewise polynomial function for power conversion
            eq_curve_pp: Piecewise polynomial function for normalization factor calculation
            volt_curve_pp: Piecewise polynomial function for voltage conversion
        _eq_factor (float): [IGT] normalized pressure based on chosen focal depth wrt exit plane [-]
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
        getters and setters (attribute name without _) for above attributes.
    """

    def __init__(self):
        """
        Initializes a Sequence object with default values and loads configuration settings.
        """

        self._seq_num = 0

        # Equipment parameters
        self._equip_combos = get_config_value(logger, config, 'Equipment', 'Combinations',
                                              '').split('\n')

        self._driving_sys = ds.DrivingSystem()
        back_up_default_ds = ds.get_ds_serials()[0]
        def_ds_serial = get_config_value(logger, config, 'Equipment',
                                         'Default driving system serial', back_up_default_ds)
        self.driving_sys = def_ds_serial

        self._wait_for_trigger = get_config_value(logger, config, 'Trigger',
                                                  'Default wait_for_trigger', 'False') == 'True'

        back_up_trigger_option = get_config_value(logger, config, 'Trigger', 'Options',
                                                  '').split('\n')[0]

        self._trigger_option = get_config_value(logger, config, 'Trigger', 'Default option',
                                                back_up_trigger_option)

        self._n_triggers = int(get_config_value(logger, config, 'Trigger', 'Default n_triggers',
                                                0))

        # set a temporary focus wrt mid bowl and operating frequency to set a default transducer
        self._chosen_power = None

        self._global_power = int(get_config_value(logger, config, 'Power', 'Default.glob_pow',
                                                  0))  # SC: global power [W]
        self._press = int(get_config_value(logger, config, 'Power', 'Default.press',
                                           0))  # IGT: maximum pressure in free water [MPa]
        self._volt = int(get_config_value(logger, config, 'Power', 'Default.volt',
                                          0))  # IGT: voltage [V]
        self._ampl = int(get_config_value(logger, config, 'Power', 'Default.ampl',
                                          0))  # IGT: amplitude [%]

        self._eq_factor = int(get_config_value(logger, config, 'Power', 'Default.eq_factor',
                                               0))  # IGT: normalized pressure

        self._focus_wrt_mid_bowl = int(get_config_value(logger, config, 'Focus', 'Default.bowl',
                                                        50))  # [mm]

        # Degree used to dephase every nth elemen based on chosen degree. (None = no dephasing).
        self._dephasing_degree = None

        self._transducer = tran.Transducer()
        back_up_default_tran = tran.get_tran_serials()[0]
        def_tran_serial = get_config_value(logger, config, 'Equipment', 'Default transducer serial',
                                           back_up_default_tran)
        self.transducer = def_tran_serial

        self._oper_freq = self.transducer.fund_freq  # [kHz]

        back_up_focus_option = self.get_focus_options()[0]
        self._chosen_focus = get_config_value(logger, config, 'Focus', 'Default option',
                                              back_up_focus_option)

        self._focus_wrt_exit_plane = self._focus_wrt_mid_bowl - self._transducer.exit_plane_dist

        # If applicable, retrieve conversion parameters
        self._conv_param = {
            "focus_curve_pp": None,
            "power_curve_pp": None,
            "eq_curve_pp": None,
            "volt_curve_pp": None,
            }

        combo_sign = get_config_value(logger, config, 'Equipment', 'Combination sign', '~')
        self._ds_tran_combo = combo_sign.join([self._driving_sys.serial, self._transducer.serial])
        if self.driving_sys.require_conv_eq:
            if self._ds_tran_combo in self._equip_combos:
                self._update_conv_param()

        back_up_ramp_shape = get_config_value(logger, config, 'Ramp', 'Options',
                                              '').split('\n')[0]
        # Timing parameters
        self._timing_param = {
            # # Pulse
            'pulse_dur': float(get_config_value(logger, config, 'Timing', 'Pulse_dur_ms',
                                                0.25)),  # [ms]
            'pulse_rep_int': float(get_config_value(logger, config, 'Timing', 'Pulse_rep_int_ms',
                                                    20)),  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            'pulse_ramp_shape': get_config_value(logger, config, 'Ramp', 'Default option',
                                                 back_up_ramp_shape),
            'pulse_ramp_dur': float(get_config_value(logger, config, 'Timing', 'Pulse_ramp_dur_ms',
                                                     0)),  # [ms]

            # # Pulse train
            'pulse_train_dur': float(get_config_value(logger, config, 'Timing',
                                                      'Pulse_train_dur_ms', 20)),  # [ms]
            'pulse_train_rep_int': float(get_config_value(logger, config, 'Timing',
                                                          'Pulse_train_rep_int_ms', 20)),  # [ms]

            # Pulse train repetition
            'pulse_train_rep_dur': float(get_config_value(logger, config, 'Timing',
                                                          'Pulse_train_rep_dur', 20)),  # [ms]

            }

    def __str__(self):
        """
        Returns a formatted string containing information about the sequence.

        Returns:
            str: Formatted information about the sequence.
        """
        info = ''

        info += f"Sequence number/buffer (for IGT purposes): {self._seq_num} \n "
        info += str(self._driving_sys)

        info += f"Wait for trigger: {self._wait_for_trigger} \n "
        info += f"Trigger option: {self._trigger_option} \n "
        info += f"Number of times a trigger is sent: {self._n_triggers} \n "

        info += str(self._transducer)

        info += "Chosen power option: "
        opt_glob_pow = get_config_value(logger, config, 'Power', 'Option.glob_pow',
                                        'Global power [mW]')
        opt_ampl = get_config_value(logger, config, 'Power', 'Option.ampl', 'Amplitude [%]')
        opt_press = get_config_value(logger, config, 'Power', 'Option.press',
                                     'Max. pressure in free water [MPa]')
        opt_volt = get_config_value(logger, config, 'Power', 'Option.volt', 'Voltage [V]')

        if self.chosen_power == opt_glob_pow:
            info += f"Global power [W]: {self._global_power} \n "
        elif self.chosen_power == opt_ampl:
            info += f"Amplitude [%]: {self._ampl} \n "
        elif self.chosen_power == opt_press:
            info += f"Maximum pressure in free water [MPa]: {self._press} \n "
        elif self.chosen_power == opt_volt:
            info += f"Voltage [V]: {self._volt} \n "
        else:
            info += "Unknown power option \n "

        if self.driving_sys.require_conv_eq:
            if self._ds_tran_combo in self._equip_combos:

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
                    info += ("- Pressure to amplitude conversion: Using piecewise polynomial fit " +
                             f"of {self.power_curve_file}\n ")

                if self._conv_param["focus_curve_pp"] is not None:
                    info += ("- Focus conversion: Using piecewise polynomial fit of " +
                             f"{self.focus_curve_file}\n ")

                if self._conv_param["eq_curve_pp"] is not None:
                    info += ("- Normalization factor calculation: Using piecewise polynomial fit " +
                             f"of {self.eq_curve_file}\n ")

                info += ("Normalized pressure [-] based on chosen focal depth wrt exit plane of " +
                         f"{self._focus_wrt_exit_plane} [mm]: {self._eq_factor} \n ")

            else:
                info += ("Pressure correction with an increasing focal depth not available in the" +
                         " configuration file for this driving system and transducer combination!" +
                         " \n ")

        info += f"Operating frequency [kHz]: {self._oper_freq} \n "
        info += f"Focal depth wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n "
        info += f"Focal depth wrt bowl middle [mm]: {self._focus_wrt_mid_bowl} \n "
        info += f"Dephasing degree (None = no dephasing): {self.dephasing_degree} \n "

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
    def seq_num(self):
        """
        Getter method for the sequence number.

        Returns:
            seq_num: Number of sequence starting at zero. Currently only used to
                           differentiate and send multiple sequences to the IGT system.
        """

        return self._seq_num

    @seq_num.setter
    def seq_num(self, seq_num):
        """
        Sets the sequence number.

        Parameters:
            seq_num (int): Number of sequence starting at zero. Currently only used to
                           differentiate and send multiple sequences to the IGT system.
        """

        is_validated = validate_value(seq_num, 'Sequence number (seq_num)',
                                      True, True, False, False)
        if is_validated:
            self._seq_num = seq_num

    @property
    def driving_sys(self):
        """
        Getter method for the driving system.

        Returns:
            DrivingSystem: The driving system associated with the sequence.
        """

        return self._driving_sys

    @driving_sys.setter
    def driving_sys(self, serial):
        """
        Sets the driving system based on the provided serial number.

        Parameters:
            serial (str): Serial number of the driving system.
        """

        self._driving_sys.set_ds_info(serial)

        # Check if transducer is initialized
        if hasattr(self, '_transducer'):
            # Update equipment combo
            combo_sign = get_config_value(logger, config, 'Equipment', 'Combination sign', '~')
            self._ds_tran_combo = combo_sign.join([self._driving_sys.serial,
                                                   self._transducer.serial])
            if self.driving_sys.require_conv_eq:
                if self._ds_tran_combo in self._equip_combos:
                    # New equipment selected, update conversion parameters
                    self._update_conv_param()

    @property
    def wait_for_trigger(self):
        """
        Gets the wait_for_trigger parameter.

        Returns:
            bool: The boolean indicating if the driving system is waiting for a trigger.
        """
        return self._wait_for_trigger

    @wait_for_trigger.setter
    def wait_for_trigger(self, wait_for_trigger):
        """
        Sets the wait_for_trigger parameter.

        Args:
            value (bool): The boolean indicating if the driving system is waiting for a trigger.
        """

        is_validated = validate_value(wait_for_trigger, 'Wait for trigger (wait_for_trigger)',
                                      False, False, False, True)
        if is_validated:
            self._wait_for_trigger = wait_for_trigger

    def get_trigger_options(self):
        """
        Returns a list of available trigger options.

        Returns:
            List[str]: Available trigger options.
        """

        return get_config_value(logger, config, 'Trigger', 'Options', '').split('\n')

    @property
    def trigger_option(self):
        """
        Gets the trigger_option parameter.

        Returns:
            str: The chosen trigger option.
        """
        return self._trigger_option

    @trigger_option.setter
    def trigger_option(self, trigger_option):
        """
        Sets the trigger_option parameter.

        Args:
            value (str):  The chosen trigger option.
        """

        if trigger_option not in self.get_trigger_options():
            message = f'{trigger_option} is not an available option.'
            logger.critical(message)
            sys.exit(message)
        else:
            self._trigger_option = trigger_option

    @property
    def n_triggers(self):
        """
        Gets the n_triggers parameter.

        Returns:
            int: The number of times a trigger will be sent.
        """
        return self._n_triggers

    @n_triggers.setter
    def n_triggers(self, n_triggers):
        """
        Sets the n_triggers parameter.

        Args:
            value (int): The number of times a trigger will be sent.
        """

        is_validated = validate_value(n_triggers, 'Number of anticipated triggers (n_triggers)',
                                      True, True, True, False)
        if is_validated:
            self._n_triggers = n_triggers

            # set temporarily the pulse train repetition parameters equal to
            # the pulse train duration to prevent default being lower than
            # pulse train duration
            self.pulse_train_rep_int = self.pulse_train_dur
            self.pulse_train_rep_dur = self.pulse_train_dur / 1e3  # convert from ms to s

    @property
    def transducer(self):
        """
        Getter method for the transducer.

        Returns:
            Transducer: The transducer associated with the sequence.
        """

        return self._transducer

    @transducer.setter
    def transducer(self, serial):
        """
        Sets the transducer based on the provided serial number.

        Parameters:
            serial (str): Serial number of the transducer.
        """

        self._transducer.set_transducer_info(serial)

        # set new default operating frequency and focus based on chosen transducer
        self._oper_freq = int(self._transducer.fund_freq)
        self._focus_wrt_exit_plane = self._transducer.min_foc  # [mm]

        # Check if driving system is initialized
        if hasattr(self, '_driving_sys'):
            # Update equipment combo
            combo_sign = get_config_value(logger, config, 'Equipment', 'Combination sign', '~')
            self._ds_tran_combo = combo_sign.join([self._driving_sys.serial,
                                                   self._transducer.serial])
            if self.driving_sys.require_conv_eq:
                if self._ds_tran_combo in self._equip_combos:
                    # New equipment selected, update conversion parameters
                    self._update_conv_param()
                    self._focus_wrt_mid_bowl = self._conv_param['focus_curve_pp'](self._focus_wrt_exit_plane)
                else:
                    self._focus_wrt_mid_bowl = (self._focus_wrt_exit_plane +
                                                self._transducer.exit_plane_dist)
            else:
                self._focus_wrt_mid_bowl = (self._focus_wrt_exit_plane +
                                            self._transducer.exit_plane_dist)

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

        is_validated = validate_value(oper_freq, 'Operating frequency [kHz] (oper_freq)',
                                      True, True, True, False)
        if is_validated:
            self._oper_freq = int(oper_freq)

    def get_power_options(self):
        """
        Returns a list of available power options.

        Returns:
            List[str]: Available power options.
        """

        return get_config_value(logger, config, 'Power', 'Options', '').split('\n')

    @property
    def chosen_power(self):
        """
        Getter method for the chosen_power.

        Returns:
            str: The chosen power parameter.
        """

        return self._chosen_power

    @chosen_power.setter
    def chosen_power(self, chosen_power):
        """
        Setter method for the chosen_power.

        Parameters:
            chosen_power (str): The chosen power parameter.
        """

        if chosen_power not in self.get_power_options():
            message = f'{chosen_power} is not an available option.'
            logger.critical(message)
            sys.exit(message)
        else:
            self._chosen_power = chosen_power

    @property
    def global_power(self):
        """
        Getter method for the global_power.

        Returns:
            float: The global power [W] for SC.
        """

        return self._global_power

    @global_power.setter
    def global_power(self, global_power):
        """
        Setter method for the global_power.

        Parameters:
            global_power (float): The global power [W] for SC.
        """

        # set other parameters determine the intensity to None
        self._ampl = 0
        self._global_power = 0

        power_option = get_config_value(logger, config, 'Power', 'Option.glob_pow',
                                        'Global power [mW]')

        if power_option in self.driving_sys.power_options:
            is_validated = validate_value(global_power, 'Global power [W] (global_power)',
                                          True, True, False, False)
            if is_validated:
                self._global_power = global_power
                self._chosen_power = power_option
        else:
            message = ('Global power parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            logger.critical(message)
            sys.exit(message)

    @property
    def press(self):
        """
        Getter method for the maximum pressure in free water.

        Returns:
            float: The maximum pressure in free water [MPa] for IGT.
        """

        return self._press

    @press.setter
    def press(self, press):
        """
        Setter method for the maximum pressure in free water.

        Parameters:
            press (float): The maximum pressure in free water [MPa] for IGT.
        """

        # set other parameters determine the intensity to None
        self._global_power = 0
        self._press = 0

        power_option = get_config_value(logger, config, 'Power', 'Option.press',
                                        'Max. pressure in free water [MPa]')

        if power_option in self.driving_sys.power_options:
            is_validated = validate_value(press, 'Maximum pressure in free water [MPa] (press)',
                                          True, True, False, False)
            if is_validated:

                max_press = float(get_config_value(logger, config, 'Power',
                                                   'Maximum pressure allowed in free water [MPa]',
                                                   1.4))
                if press > max_press:
                    message = (f'The set maximum pressure in free water of {press} [MPa] is ' +
                               f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                               ' your value.')
                    logger.critical(message)
                    sys.exit(message)

                self._press = press

                self._chosen_power = power_option

                if self.driving_sys.require_conv_eq:
                    if self._ds_tran_combo in self._equip_combos:
                        # Convert required amplitude
                        self._calc_ampl()

                        # Calculate voltage for logging
                        self._calc_volt()

                        logger.debug('New maximum pressure in free water value of ' +
                                     f'{self._press:.2f} [MPa] results in a voltage of ' +
                                     f'{self._volt[0]:.2f} [V] and an amplitude of ' +
                                     f'{self._ampl[0]:.2f} [%].')
                    else:
                        message = ('Conversion equations unknown but required for ' +
                                   f'{self._ds_tran_combo}.')
                        logger.critical(message)
                        sys.exit(message)
        else:
            message = ('Pressure parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            logger.critical(message)
            sys.exit(message)

    @property
    def volt(self):
        """
        Getter method for the voltage.

        Returns:
            float: The voltage [V] for IGT.
        """

        return self._volt

    @volt.setter
    def volt(self, volt):
        """
        Setter method for the voltage.

        Parameters:
            volt (float): The voltage [V] for IGT.
        """

        # set other parameters determine the intensity to None
        self._global_power = 0
        self._volt = 0

        power_option = get_config_value(logger, config, 'Power', 'Option.volt', 'Voltage [V]')

        if power_option in self.driving_sys.power_options:
            if not isinstance(volt, list):
                volt = [volt]

            # Check if enough voltage entries are given
            n_entries = len(volt)
            if n_entries != self.driving_sys.available_ch and n_entries != 1:
                message = (f'Number of voltage entries ({n_entries}) does not correspond to ' +
                           f'number of transducer elements ({self.driving_sys.available_ch}). ' +
                           'Only enter one voltage value or n-values equal to the number of ' +
                           'transducer elements.')
                logger.critical(message)
                sys.exit(message)

            is_validated = validate_value(volt, 'Voltage [V] (volt)', True, True, False, False,
                                          True)

            if is_validated:
                self._volt = volt

                self._chosen_power = power_option

                if self.driving_sys.require_conv_eq:
                    if self._ds_tran_combo in self._equip_combos:
                        # Convert required to amplitude
                        self._calc_ampl_using_volt()

                        if n_entries > 1:
                            round_ampl = [f'{x:.2f}' for x in self._ampl]
                            round_volt = [f'{x:.2f}' for x in self._volt]
                        else:
                            round_ampl = f'{self._ampl[0]:.2f}'
                            round_volt = f'{self._volt[0]:.2f}'

                        if n_entries == 1:
                            # Calculate maximum pressure in free water for logging purposes
                            self._calc_press()

                            logger.debug(f'New voltage value of {round_volt} [V] results in a ' +
                                         f'maximum pressure in free water of {self._press:.2f} ' +
                                         f' [MPa] and an amplitude of {round_ampl} [%].')
                        else:
                            logger.debug('Pressure cannot be calculated when multiple voltages ' +
                                         'are given.')
                            logger.debug(f'New voltage value of {round_volt} [V] results in an ' +
                                         f'amplitude of {round_ampl} [%].')
                    else:
                        message = ('Conversion equations unknown but required for ' +
                                   f'{self._ds_tran_combo}.')
                        logger.critical(message)
                        sys.exit(message)

        else:
            message = ('Voltage parameter is not available for ' +
                       'chosen driving system. Use one of the following options instead: ' +
                       f'{self.driving_sys.power_options}.')
            logger.critical(message)
            sys.exit(message)

    @property
    def ampl(self):
        """
        Getter method for the amplitude.

        Returns:
            float: The amplitude array [%] for IGT: one value represents the value for all elements.
        """

        return self._ampl

    @ampl.setter
    def ampl(self, ampl):
        """
        Setter method for the amplitude.

        Parameters:
            ampl (list(float)): The amplitude array [%] for IGT: one value represents the value
            for all elements.
        """

        # set other parameters that determine the intensity to None
        self._global_power = 0
        self._ampl = 0

        power_option = get_config_value(logger, config, 'Power', 'Option.ampl', 'Amplitude [%]')
        if power_option in self.driving_sys.power_options:
            if not isinstance(ampl, list):
                ampl = [ampl]

            # Check if enough amplitude entries are given
            n_entries = len(ampl)
            if n_entries != self.driving_sys.available_ch and n_entries != 1:
                message = (f'Number of amplitude entries ({n_entries}) does not correspond to ' +
                           f'number of transducer elements ({self.driving_sys.available_ch}). ' +
                           'Only enter one amplitude value or n-values equal to the number of ' +
                           'transducer elements.')
                logger.critical(message)
                sys.exit(message)

            is_validated = validate_value(ampl, 'Amplitude [%] (ampl)',
                                          True, True, False, False, True)

            if is_validated:
                self._ampl = ampl

                self._chosen_power = power_option

                if self.driving_sys.require_conv_eq:
                    if self._ds_tran_combo in self._equip_combos:
                        # Convert amplitude to voltage for logging
                        self._calc_volt()

                        round_ampl = f'{self._ampl[0]:.2f}'
                        round_volt = f'{self._volt[0]:.2f}'

                        if n_entries > 1:
                            # Equipment is not part a combination, so only set amplitude
                            logger.debug(f'New amplitude value of {round_ampl} [%] results in a ' +
                                         f'voltage of {round_volt} [V].')
                            logger.debug('Amplitude array is given. Pressure cannot ' +
                                         'be calculated for logging purposes.')
                        else:
                            # Convert amplitude to pressure for logging
                            self._calc_press()

                            logger.debug(f'New amplitude value of {round_ampl} [%] results in a ' +
                                         f'maximum pressure in free water of {self._press:.2f} ' +
                                         f'[MPa] and a voltage of {round_volt} [V].')
                    else:
                        message = (f'Conversion equations unknown for {self._ds_tran_combo}.')
                        logger.debug(message)

    def get_focus_options(self):
        """
        Returns a list of available focus options.

        Returns:
            List[str]: Available focus options.
        """

        return get_config_value(logger, config, 'Focus', 'Options', '').split('\n')

    @property
    def chosen_focus(self):
        """
        Getter method for the chosen_focus.

        Returns:
            str: The chosen focus parameter.
        """

        return self._chosen_focus

    @chosen_focus.setter
    def chosen_focus(self, chosen_focus):
        """
        Setter method for the chosen_focus.

        Parameters:
            chosen_focus (str): The chosen focus parameter.
        """

        if chosen_focus not in self.get_focus_options():
            message = f'{chosen_focus} is not an available option.'
            logger.critical(message)
            sys.exit(message)
        else:
            self._chosen_focus = chosen_focus

    @property
    def focus_wrt_exit_plane(self):
        """
        Getter method for the focal depth w.r.t. the exit plane representing the middle of the FWHM.

        Returns:
            float: The focal depth [mm] w.r.t. the exit plane representing the middle of the FWHM.
        """

        return self._focus_wrt_exit_plane

    @focus_wrt_exit_plane.setter
    def focus_wrt_exit_plane(self, focus):
        """
        Setter method for the focal depth w.r.t. middle of the transducer bowl and w.r.t. exit plane
        representing the middle of the FWHM.

        Parameters:
            focus (float): Focal depth [mm] w.r.t. the exit plane representing the middle of the
            FWHM.
            TODO: combine setting the focus and power.
        """

        is_validated = validate_value(focus, 'Focus wrt exit plane [mm] (focus_wrt_exit_plane)',
                                      True, True, False, False)

        if is_validated:

            # Check if focus is within range if compensation equations are not applicable
            if focus < self._transducer.min_foc or focus > self._transducer.max_foc:
                message = (f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                           f'focus range of {self._transducer.min_foc} and ' +
                           f'{self._transducer.max_foc} [mm] of transducer ' +
                           f'{self._transducer.name}.')
                logger.critical(message)
                sys.exit(message)

            if self.driving_sys.require_conv_eq:
                if self._ds_tran_combo in self._equip_combos:
                    self._focus_wrt_mid_bowl = self._conv_param['focus_curve_pp'](focus)
                else:
                    message = ('Compensation equations are not available. Focus wrt' +
                               ' mid bowl will be calculated based on exit plane distance of ' +
                               f'{self._transducer.exit_plane_dist} [mm].')
                    logger.warning(message)

                    self._focus_wrt_mid_bowl = focus + self._transducer.exit_plane_dist

            else:
                self._focus_wrt_mid_bowl = focus + self._transducer.exit_plane_dist

            self._chosen_focus = get_config_value(logger, config, 'Focus', 'Option.exit',
                                                  'Focus wrt exit plane [mm]')
            self._focus_wrt_exit_plane = focus

            logger.debug(f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                         f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

        # Check if pressure compensation is available for chosen equipment
        if self.driving_sys.require_conv_eq:
            if self._ds_tran_combo in self._equip_combos:
                # Update normalized pressure based on new focal depth
                self._calc_eq_factor()

                # Update amplitude accordingly
                self._calc_ampl()

                # Update voltage accordingly
                self._calc_volt()

                if len(self._ampl) > 1:
                    round_ampl = [f'{x:.2f}' for x in self._ampl]
                    round_volt = [f'{x:.2f}' for x in self._volt]
                else:
                    round_ampl = f'{self._ampl[0]:.2f}'
                    round_volt = f'{self._volt[0]:.2f}'

                logger.debug(f"New focus wrt exit plane of {self._focus_wrt_exit_plane:.2f} [mm] " +
                             f" results in an equalization factor of {self._eq_factor:.2f} " +
                             "recalcultating the maximum pressure in free water as " +
                             f"{self._press:.2f} [MPa], the voltage as {round_volt} [V], and the " +
                             f"amplitude as {round_ampl} [%].")
            else:
                message = ('Conversion equations unknown but required for ' +
                           f'{self._ds_tran_combo}.')
                logger.critical(message)
                sys.exit(message)

    @property
    def focus_wrt_mid_bowl(self):
        """
        Getter method for the focal depth w.r.t. middle of the transducer bowl representing the
        middle of the FWHM.

        Returns:
            float: The focal depth [mm] w.r.t. middle of the transducer bowl representing the
            middle of the FWHM.
        """

        return self._focus_wrt_mid_bowl

    @focus_wrt_mid_bowl.setter
    def focus_wrt_mid_bowl(self, focus):
        """
        Setter method for the focal depth w.r.t. middle of the transducer bowl representing the
        middle of the FWHM.

        Parameters:
            focus (float): Focal depth [mm] w.r.t. middle of the transducer bowl representing the
            middle of the FWHM.
            noAmplInput (bool): If amplitude is used as input, conversion of the amplitude due to
            the set focus is no needed. Currently used for PCD measurements.
            TODO: combine setting the focus and power.
        """

        is_validated = validate_value(focus, 'Focus wrt mid bowl [mm] (focus_wrt_mid_bowl)',
                                      True, True, False, False)

        if is_validated:
            if self.driving_sys.require_conv_eq:
                if self._ds_tran_combo in self._equip_combos:
                    target_y_value = focus
                    self._focus_wrt_exit_plane, status = find_x_for_y_in_pp(
                        self._conv_param['focus_curve_pp'], target_y_value)

                    if status:
                        logger.debug(f"Found x value: {self._focus_wrt_exit_plane} for y = " +
                                     f"{target_y_value}")

                        # Verify
                        calc_y = self._conv_param['focus_curve_pp'](self._focus_wrt_exit_plane)
                        logger.debug(f"Verification: pp({self._focus_wrt_exit_plane}) = {calc_y}")
                    else:
                        logger.warning(f"Could not find an x value for y = {target_y_value}. " +
                                       'Focus wrt exit plane will be calculated based on exit ' +
                                       f'plane distance of {self._transducer.exit_plane_dist} [mm].')

                        self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

                else:
                    message = ('Compensation equations are not available or applicable. Focus wrt' +
                               ' exit plane will be calculated based on exit plane distance of ' +
                               f'{self._transducer.exit_plane_dist} [mm].')
                    logger.warning(message)

                    self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

            else:

                self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

            # Check if focus is within range if compensation equations are not applicable
            if self._focus_wrt_exit_plane < self._transducer.min_foc or self._focus_wrt_exit_plane > self._transducer.max_foc:
                message = (f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                           f'focus range of {self._transducer.min_foc} and ' +
                           f'{self._transducer.max_foc} [mm] of transducer ' +
                           f'{self._transducer.name}.')
                logger.critical(message)
                sys.exit(message)

            self._chosen_focus = get_config_value(logger, config, 'Focus', 'Option.bowl',
                                                  'Focus wrt mid bowl [mm]')

            self._focus_wrt_mid_bowl = focus

            logger.debug(f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                         f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

        # Check if pressure compensation is available for chosen equipment
        if self.driving_sys.require_conv_eq:
            if self._ds_tran_combo in self._equip_combos:
                # Update normalized pressure based on new focal depth
                self._calc_eq_factor()

                # Update amplitude accordingly
                self._calc_ampl()

                # Update voltage accordingly
                self._calc_volt()

                if len(self._ampl) > 1:
                    round_ampl = [f'{x:.2f}' for x in self._ampl]
                    round_volt = [f'{x:.2f}' for x in self._volt]
                else:
                    round_ampl = f'{self._ampl[0]:.2f}'
                    round_volt = f'{self._volt[0]:.2f}'

                logger.debug(f"New focus wrt mid bowl of {self._focus_wrt_mid_bowl:.2f} [mm] " +
                             f"results in an equalization factor of {self._eq_factor:.2f} " +
                             "recalcultating the maximum pressure in free water as " +
                             f"{self._press:.2f} [MPa], the voltage as {round_volt} [V], and the " +
                             f"amplitude as {round_ampl} [%].")
            else:
                message = ('Conversion equations unknown but required for ' +
                           f'{self._ds_tran_combo}.')
                logger.critical(message)
                sys.exit(message)

    def set_focus_wrt_mid_bowl(self, focus, noAmplInput=True):
        """
        Setter method for the focal depth w.r.t. middle of the transducer bowl representing the
        middle of the FWHM.

        Parameters:
            focus (float): Focal depth [mm] w.r.t. middle of the transducer bowl representing the
            middle of the FWHM.
            noAmplInput (bool): If amplitude is used as input, conversion of the amplitude due to
            the set focus is no needed. Currently used for PCD measurements.
            TODO: combine setting the focus and power.
        """

        is_validated = validate_value(focus, 'Focus wrt mid bowl [mm] (focus_wrt_mid_bowl)',
                                      True, True, False, False)

        if is_validated:
            if self.driving_sys.require_conv_eq:
                if self._ds_tran_combo in self._equip_combos:
                    target_y_value = focus
                    self._focus_wrt_exit_plane, status = find_x_for_y_in_pp(
                        self._conv_param['focus_curve_pp'], target_y_value)

                    if status:
                        logger.debug(f"Found x value: {self._focus_wrt_exit_plane} for y = " +
                                     f"{target_y_value}")

                        # Verify
                        calc_y = self._conv_param['focus_curve_pp'](self._focus_wrt_exit_plane)
                        logger.debug(f"Verification: pp({self._focus_wrt_exit_plane}) = {calc_y}")
                    else:
                        logger.warning(f"Could not find an x value for y = {target_y_value}. " +
                                       'Focus wrt exit plane will be calculated based on exit ' +
                                       f'plane distance of {self._transducer.exit_plane_dist} [mm].')

                        self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

                else:
                    message = ('Compensation equations are not available or applicable. Focus wrt' +
                               ' exit plane will be calculated based on exit plane distance of ' +
                               f'{self._transducer.exit_plane_dist} [mm].')
                    logger.warning(message)

                    self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

            else:

                self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

            # Check if focus is within range if compensation equations are not applicable
            if self._focus_wrt_exit_plane < self._transducer.min_foc or self._focus_wrt_exit_plane > self._transducer.max_foc:
                message = (f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                           f'focus range of {self._transducer.min_foc} and ' +
                           f'{self._transducer.max_foc} [mm] of transducer ' +
                           f'{self._transducer.name}.')
                logger.critical(message)
                sys.exit(message)

            self._chosen_focus = get_config_value(logger, config, 'Focus', 'Option.bowl',
                                                  'Focus wrt mid bowl [mm]')

            self._focus_wrt_mid_bowl = focus

            logger.debug(f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                         f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

        # Check if pressure compensation is available for chosen equipment
        if noAmplInput and self.driving_sys.require_conv_eq:
            if self._ds_tran_combo in self._equip_combos:
                # Update normalized pressure based on new focal depth
                self._calc_eq_factor()

                # Update amplitude accordingly
                self._calc_ampl()

                # Update voltage accordingly
                self._calc_volt()

                if len(self._ampl) > 1:
                    round_ampl = [f'{x:.2f}' for x in self._ampl]
                    round_volt = [f'{x:.2f}' for x in self._volt]
                else:
                    round_ampl = f'{self._ampl[0]:.2f}'
                    round_volt = f'{self._volt[0]:.2f}'

                logger.debug(f"New focus wrt exit plane of {self._focus_wrt_mid_bowl:.2f} [mm] " +
                             f"results in an equalization factor of {self._eq_factor:.2f} " +
                             "recalcultating the maximum pressure in free water as " +
                             f"{self._press:.2f} [MPa], the voltage as {round_volt} [V], and the " +
                             f"amplitude as {round_ampl} [%].")
            else:
                message = ('Conversion equations unknown but required for ' +
                           f'{self._ds_tran_combo}.')
                logger.critical(message)
                sys.exit(message)

    @property
    def dephasing_degree(self):
        """
        Getter method for the dephasing degree.

        Returns:
            list(float): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases based on
            the focus are overriden.
        """

        return self._dephasing_degree

    @dephasing_degree.setter
    def dephasing_degree(self, dephasing_degree):
        """
        Setter method for the dephasing degree.

        Parameters:
            dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases based on
            the focus wrt middle of the transducer bowl are overriden.
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
    def pulse_dur(self):
        """
        Getter method for the pulse duration.

        Returns:
            float: The pulse duration [ms].
        """

        return self._timing_param['pulse_dur']

    @pulse_dur.setter
    def pulse_dur(self, pulse_dur):
        """
        Setter method for the pulse duration.

        Parameters:
            pulse_dur (float): Pulse duration [ms].
        """

        is_validated = validate_value(pulse_dur, 'Pulse duration [ms] (pulse_dur)',
                                      True, True, True, False)
        if is_validated:
            self._timing_param['pulse_dur'] = pulse_dur

            # Set other timing levels equal to new parameter to prevent higher levels being shorter
            # than the lower levels when they are not set
            self.pulse_rep_int = pulse_dur
            self.pulse_train_dur = pulse_dur
            self.pulse_train_rep_int = pulse_dur
            self.pulse_train_rep_dur = pulse_dur / 1e3  # convert from ms to s

    @property
    def pulse_rep_int(self):
        """
        Getter method for the pulse repetition interval.

        Returns:
            float: The pulse repetition interval [ms].
        """

        return self._timing_param['pulse_rep_int']

    @pulse_rep_int.setter
    def pulse_rep_int(self, pulse_rep_int):
        """
        Setter method for the pulse repetition interval.

        Parameters:
            pulse_rep_int (float): Pulse repetition interval [ms].
        """

        is_validated = validate_value(pulse_rep_int,
                                      'Pulse repetition interval [ms] (pulse_rep_int)',
                                      True, True, True, False)
        if is_validated:
            self._timing_param['pulse_rep_int'] = pulse_rep_int

            # Set other timing levels equal to new parameter to prevent higher levels being shorter
            # than the lower levels when they are not set
            self.pulse_train_dur = pulse_rep_int
            self.pulse_train_rep_int = pulse_rep_int
            self.pulse_train_rep_dur = pulse_rep_int / 1e3  # convert from ms to s

    def get_ramp_shapes(self):
        """
        Returns a list of available ramp shapes for pulse modulation.

        Returns:
            List[str]: Available ramp shapes.
        """

        return get_config_value(logger, config, 'Ramp', 'Options', '').split('\n')

    @property
    def pulse_ramp_shape(self):
        """
        Getter method for the pulse ramp shape.

        Returns:
            str: The pulse ramp shape.
        """

        return self._timing_param['pulse_ramp_shape']

    @pulse_ramp_shape.setter
    def pulse_ramp_shape(self, pulse_ramp_shape):
        """
        Setter method for the pulse ramp shape.

        Parameters:
            pulse_ramp_shape (str): Selected pulse ramp shape.
        """

        if pulse_ramp_shape not in self.get_ramp_shapes():
            message = f'{pulse_ramp_shape} is not an available option.'
            logger.critical(message)
            sys.exit(message)

        else:
            self._timing_param['pulse_ramp_shape'] = pulse_ramp_shape

    @property
    def pulse_ramp_dur(self):
        """
        Getter method for the pulse ramp duration.

        Returns:
            float: The pulse ramp duration [ms].
        """

        return self._timing_param['pulse_ramp_dur']

    @pulse_ramp_dur.setter
    def pulse_ramp_dur(self, pulse_ramp_dur):
        """
        Setter method for the pulse ramp duration.

        Parameters:
            pulse_ramp_dur (float): Pulse ramp duration [ms].
        """

        is_validated = validate_value(pulse_ramp_dur,
                                      'Pulse ramp duration [ms] (pulse_ramp_dur)',
                                      True, True, False, False)
        if is_validated:
            self._timing_param['pulse_ramp_dur'] = pulse_ramp_dur

    @property
    def pulse_train_dur(self):
        """
        Getter method for the pulse train duration.

        Returns:
            float: The pulse train duration [ms].
        """

        return self._timing_param['pulse_train_dur']

    @pulse_train_dur.setter
    def pulse_train_dur(self, pulse_train_dur):
        """
        Setter method for the pulse train duration.

        Parameters:
            pulse_train_dur (float): Pulse train duration [ms].
        """

        is_validated = validate_value(pulse_train_dur,
                                      'Pulse train duration [ms] (pulse_train_dur)',
                                      True, True, True, False)
        if is_validated:
            self._timing_param['pulse_train_dur'] = pulse_train_dur

            # Set other timing levels equal to new parameter to prevent higher levels being shorter
            # than the lower levels when they are not set
            self.pulse_train_rep_int = pulse_train_dur
            self.pulse_train_rep_dur = pulse_train_dur / 1e3  # convert from ms to s

    @property
    def pulse_train_rep_int(self):
        """
        Getter method for the pulse train repetition interval.

        Returns:
            float: The pulse train repetition interval [ms].
        """

        return self._timing_param['pulse_train_rep_int']

    @pulse_train_rep_int.setter
    def pulse_train_rep_int(self, pulse_train_rep_int):
        """
        Setter method for the pulse train repetition interval.

        Parameters:
            pulse_train_rep_int (float): Pulse train repetition interval [ms].
        """

        is_validated = validate_value(pulse_train_rep_int,
                                      'Pulse train repetition interval [ms] (pulse_train_rep_int)',
                                      True, True, True, False)
        if is_validated:
            self._timing_param['pulse_train_rep_int'] = pulse_train_rep_int

            # Set other timing levels equal to new parameter to prevent higher levels being shorter
            # than the lower levels when they are not set
            self.pulse_train_rep_dur = pulse_train_rep_int / 1e3  # convert from ms to s

    @property
    def pulse_train_rep_dur(self):
        """
        Getter method for the pulse train repetition duration.

        Returns:
            float: The pulse train repetition duration [ms].
        """

        return self._timing_param['pulse_train_rep_dur']

    @pulse_train_rep_dur.setter
    def pulse_train_rep_dur(self, pulse_train_rep_dur):
        """
        Setter method for the pulse train repetition duration.

        Parameters:
            pulse_train_rep_dur (float): Pulse train repetition duration [s].
        """

        is_validated = validate_value(pulse_train_rep_dur,
                                      'Pulse train repetiton duration [s] (pulse_train_rep_dur)',
                                      True, True, True, False)
        if is_validated:
            # convert pulse train repetition duration in seconds to milliseconds
            self._timing_param['pulse_train_rep_dur'] = pulse_train_rep_dur * 1e3

            if self._trigger_option == get_config_value(logger, config, 'Trigger', 'option.ptr',
                                                        'TriggerOnePulseTrainRepetition'):
                self._n_triggers = 1

    def _update_conv_param(self):
        """
        Update method for the conversion parameters to compensate for decreasing pressure with
        increasing focal depth wrt exit plane.
        """

        section_name = 'Equipment.Combination.' + self._ds_tran_combo

        self.eq_curve_file = get_config_value(logger, config, section_name,
                                              'EqualizationCurveFit json file', None, True)

        self.focus_curve_file = get_config_value(logger, config, section_name,
                                                 'FocusCurveFit json file', None, True)

        self.power_curve_file = get_config_value(logger, config, section_name,
                                                 'PowerCurveFit json file', None, True)

        self.volt_curve_file = get_config_value(logger, config, section_name,
                                                'VoltageCurveFit json file', None, True)

        eq_pp, eq_breaks = extract_and_define_pp(self.eq_curve_file, return_breaks=True)

        self._conv_param = {
            "focus_curve_pp": extract_and_define_pp(self.focus_curve_file),
            "power_curve_pp": extract_and_define_pp(self.power_curve_file),
            "eq_curve_pp": eq_pp,
            "volt_curve_pp": extract_and_define_pp(self.volt_curve_file),
            }

        self.transducer.min_foc = min(eq_breaks)
        self.transducer.max_foc = max(eq_breaks)

        self._calc_eq_factor()

        # Convert to amplitude, assumption that the maximum pressure in free water remains the same
        self._calc_ampl()

        self._calc_volt()

        if len(self._ampl) > 1:
            round_ampl = [f'{x:.2f}' for x in self._ampl]
            round_volt = [f'{x:.2f}' for x in self._volt]
        else:
            round_ampl = f'{self._ampl[0]:.2f}'
            round_volt = f'{self._volt[0]:.2f}'

        logger.debug('New equipment pressure compensation coefficients result in a maximum' +
                     f' pressure in free water of {self._press:.2f} [MPa], a voltage of ' +
                     f'{round_volt} [V] and an amplitude of {round_ampl} [%].')

    def _calc_eq_factor(self):
        """
        Calculate equalization factor of the pressure vs. focal depth wrt exit plane [mm] equation.
        """

        try:
            self._eq_factor = self._conv_param['eq_curve_pp'](self._focus_wrt_exit_plane)
        except ValueError as e:
            message = (f'{e} \n Focus wrt exit plane of {self._focus_wrt_exit_plane} mm is not ' +
                       f'within the limits of {self.transducer.min_foc} and ' +
                       f'{self.transducer.max_foc} [mm].')
            logger.critical(message)
            sys.exit(message)

    def _calc_volt(self):
        """
        Calculate amplitude [%] vs. voltage [V] equation when amplitude is updated.
        """

        volt = []
        for ampl in self._ampl:
            volt_value, status = find_x_for_y_in_pp(self._conv_param['volt_curve_pp'], ampl)

            if status:
                logger.debug(f"Found x value: {volt_value} for y = {ampl}")

                # Verify
                calc_y = self._conv_param['volt_curve_pp'](volt_value)
                logger.debug(f"Verification: pp({volt_value}) = {calc_y}")

            else:
                volt_value = 0
                logger.error(f"Could not find a voltage value for amplitude = {ampl}")

            volt.append(volt_value)

        self._volt = volt

    def _calc_ampl(self):
        """
        Calculate pressure [Pa] vs. amplitude [%] equation when pressure is updated.
        """

        press_pa = self._press * 1e6  # convert to Pa

        x_value = press_pa * self._eq_factor
        calc_ampl, range_status = safe_evaluate_pp(self._conv_param['power_curve_pp'], x_value)

        if range_status == "above_range":
            self._ampl = [100]
            self._calc_press()
            self._calc_volt()

            message = (f'Calculated amplitude exceeds 100%. A pressure of {self._press:.2f} [MPa]' +
                       f' and/or a voltage of {self._volt[0]:.2f} [V] will result in an amplitude' +
                       f' of 100% at focus wrt exit plane of {self._focus_wrt_exit_plane} [mm]. ' +
                       'Change input value.')
            logger.critical(message)
            sys.exit(message)
        elif range_status == "below_range":
            logger.debug('Calculated amplitude below 0%, so cut off the amplitude at 0%.')
            self._ampl = [0]
            self._calc_press()
            self._calc_volt()

        else:
            if calc_ampl < 0:
                calc_ampl = 0
            self._ampl = [round(float(calc_ampl), 2)]

    def _calc_ampl_using_volt(self):
        """
        Calculate voltage [V] vs. amplitude [%] equation when voltage is updated.
        """

        ampl = []
        for volt in self._volt:
            calc_ampl, range_status = safe_evaluate_pp(self._conv_param['volt_curve_pp'], volt)

            if range_status == "above_range":
                self._ampl = [100]
                self._calc_press()
                self._calc_volt()

                message = (f'Calculated amplitude exceeds 100%. A pressure of {self._press:.2f} ' +
                           f'[MPa] and/or a voltage of {self._volt[0]:.2f} [V] will result in an ' +
                           'amplitude of 100% at focus wrt exit plane of ' +
                           f'{self._focus_wrt_exit_plane} [mm]. Change input value.')

                logger.critical(message)
                sys.exit(message)
            elif range_status == "below_range":
                logger.debug(('Calculated amplitude below 0%, so cut off the amplitude at 0% and ' +
                              'recalculate the pressure.'))
                calc_ampl = 0

            if calc_ampl < 0:
                calc_ampl = 0

            ampl.append(round(float(calc_ampl), 2))

        self._ampl = ampl

    def _calc_press(self):
        """
        Calculate pressure [Pa] vs. amplitude [%] equation when amplitude is updated.
        """

        target_y_value = self._ampl[0]
        press_pa_with_eq_fact, status = find_x_for_y_in_pp(self._conv_param['power_curve_pp'],
                                                           target_y_value)

        if status:
            logger.debug(f"Found x value: {press_pa_with_eq_fact} for y = {target_y_value}")

            # Verify
            calc_y = self._conv_param['power_curve_pp'](press_pa_with_eq_fact)
            logger.debug(f"Verification: pp({press_pa_with_eq_fact}) = {calc_y}")

            press_mpa = (press_pa_with_eq_fact / self._eq_factor) * 1e-6
            max_press = float(get_config_value(logger, config, 'Power',
                                               'Maximum pressure allowed in free water [MPa]', 1.4))
            if press_mpa > max_press:
                message = (f'The set maximum pressure in free water of {press_mpa} [MPa] is ' +
                           f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                           ' your value.')
                logger.critical(message)
                sys.exit(message)

            self._press = press_mpa  # convert to MPa
        else:
            self._press = None
            logger.error(f"Could not find a pressure value for amplitude = {target_y_value}")


def validate_value(value, input_param, check_num, check_pos, check_nonzero, check_bool,
                   check_list=False):
    """
    Validates `value` based on specified checks, logs errors if conditions are not met, and exits
    if validation fails.

    Parameters:
        value (any): The value to check.
        input_param (str): Name of the parameter, used in error messages.
        check_num (bool): Checks if value is a number.
        check_pos (bool): Ensures value is non-negative.
        check_nonzero (bool): Ensures value is not zero.
        check_bool (bool): Checks if value is a boolean.
        check_list (bool): Checks if value is a list.

    Returns:
        bool: True if all checks pass; otherwise, logs errors and exits.
    """

    val_messages = []

    if check_list:
        if isinstance(value, list):
            for item in value:
                input_name = 'Items of ' + input_param
                val_messages = _check_parameter(val_messages, item, input_name, check_nonzero,
                                                check_num, check_pos, check_bool)

        else:
            val_messages.append(f'{input_param} should be a list.')
    else:
        val_messages = _check_parameter(val_messages, value, input_param, check_nonzero, check_num,
                                        check_pos, check_bool)

    if val_messages:
        for message in val_messages:
            logger.critical(message)
        sys.exit('Validation of input parameters failed.')

    return True


def _check_parameter(val_messages, value, input_name, check_nonzero, check_num, check_pos,
                     check_bool):
    """
    Checks a single value against specified conditions and appends error messages if any checks
    fail.

    Parameters:
        val_messages (list): List to append error messages to.
        value (any): The value to check.
        input_name (str): Name of the parameter, used in error messages.
        check_nonzero (bool): Ensures value is not zero.
        check_num (bool): Checks if value is a number.
        check_pos (bool): Ensures value is non-negative.
        check_bool (bool): Checks if value is a boolean.

    Returns:
        list: The updated list of error messages.
    """

    if check_nonzero and value == 0:
        val_messages.append(f'{input_name} is not allowed to be zero.')
    if check_num and not isinstance(value, (int, float)):
        val_messages.append(f'{input_name} should be a number.')
    if check_pos and value < 0:
        val_messages.append(f'{input_name} is not allowed to be negative.')
    if check_bool and not isinstance(value, bool):
        val_messages.append(f'{input_name} should be a boolean.')
    return val_messages


def extract_and_define_pp(json_dir, return_breaks=False):
    """
    This function loads polynomial coefficients and breakpoints from a JSON file that was exported
    from MATLAB. It handles potential format inconsistencies and converts the data to be compatible
    with SciPy's PPoly class.

    Parameters:
        json_path (str): Path to the JSON file containing the piecewise polynomial parameters.
        return_breaks (bool): If True, returns both the PPoly object and the breakpoints array.
            Default is False.

    Returns:
        scipy.interpolate.PPoly: A piecewise polynomial object that can be used for interpolation.
        numpy.ndarray, optional: Array of breakpoints if return_breaks=True.

    Raises:
        SystemExit: If xTransform is specified but not 'none', as transforms are not implemented.

    Notes:
        The function expects coefficients in the format used by MATLAB and converts them to
        the format expected by SciPy's PPoly constructor. For linear functions (order=2),
        coefficients are reversed. The resulting PPoly has extrapolation disabled.
    """

    # Load the JSON file
    json_path = pkg_resources.resource_filename('fus_driving_systems', json_dir)
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract only the necessary components
    try:
        xTransform = np.array(data['xTransform'])
        if xTransform.item() != 'none':
            message = 'A transform of the x value is expected, but not implemented.'
            logger.error(message)
            sys.exit(message)
    except KeyError:
        logger.debug('xTransform is not part of the file structure.')
    except TypeError:
        logger.warning('Data structure does not support this type of access.')
    except ValueError as ve:
        logger.warning(f'Error converting xTransform to numpy array: {ve}')
    except Exception as e:
        logger.warning(f'Unknown error checking for xTransform: {str(e)}')

    breaks = np.array(data['FitParams']['breaks'])
    coefs_data = data['FitParams']['coefs']

    order = len(coefs_data[0])

    # Calculate number of pieces from breaks
    pieces = len(breaks) - 1

    logger.debug(f"Extracted order: {order}")
    logger.debug(f"Number of pieces: {pieces}")

    # Convert coefficients to the format expected by PPoly
    # SciPy expects shape (k, m) where k is order and m is pieces
    coefs = np.zeros((order, pieces))
    for i, coef_set in enumerate(coefs_data):
        # For linear functions (order=2), just reverse
        if order == 2:
            coefs[:, i] = coef_set[::-1]
        else:
            # For higher order polynomials, we need to be more careful
            # This assumes MATLAB provides coefficients in descending order
            coefs[:, i] = coef_set

    # Create the PPoly object
    pp = PPoly(coefs, breaks, extrapolate=False)

    if return_breaks:
        return pp, breaks

    return pp


def safe_evaluate_pp(pp, x_value):
    """
    Safely evaluate polynomial with range information
    """

    # Get domain boundaries
    x_min = pp.x[0]
    x_max = pp.x[-1]

    # Determine if value is outside range
    if x_value < x_min:
        return None, "below_range"
    elif x_value > x_max:
        return None, "above_range"
    else:
        return pp(x_value), "in_range"


def find_x_for_y_in_pp(pp, y_value, x_min=None, x_max=None, tol=1e-6):
    """
    Find the x value corresponding to a given y value in a monotonic piecewise polynomial.

    Args:
        pp: Piecewise polynomial object (from scipy.interpolate)
        y_value: Target y value to find the corresponding x value for
        x_min: Minimum x value to consider (defaults to pp.x[0])
        x_max: Maximum x value to consider (defaults to pp.x[-1])
        tol: Tolerance for the root finding algorithm

    Returns:
        tuple: (x_value, status_code)
            - x_value: The x value corresponding to y_value, or None if not found
            - status_code: True if an x value was found, False otherwise
    """
    # Set default bounds if not provided
    if x_min is None:
        x_min = pp.x[0]
    if x_max is None:
        x_max = pp.x[-1]

    # Define the objective function: pp(x) - y_value = 0
    def objective(x):
        return pp(x) - y_value

    try:
        # Check if y_value is within the range of pp
        y_min = pp(x_min)
        y_max = pp(x_max)

        # Determine if pp is increasing or decreasing
        is_increasing = y_max > y_min

        # Check if y_value is within range
        if (is_increasing and (y_value < y_min or y_value > y_max)) or \
           (not is_increasing and (y_value > y_min or y_value < y_max)):
            return None, False

        # Use root finding to find the x value
        result = optimize.brentq(objective, x_min, x_max, xtol=tol)

        # Verify the result
        if abs(pp(result) - y_value) <= tol:
            return result, True
        else:
            return None, False

    except Exception as e:
        logger.error(f"Error finding x value: {e}")
        return None, False
