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
If you use this kit in your research or project, please include the following attribution:
Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 1.0),
https://github.com/Donders-Institute/Radboud-FUS-measurement-kit
"""

# Basic packages
import sys

# Miscellaneous packages
import math

# Own packages
from fus_driving_systems import driving_system as ds
from fus_driving_systems import transducer as tran

from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import logger


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
        _conv_param (dict): Conversion parameters to compensate for decreasing pressure with
        increasing focal depth.
            voltage [V] vs. amplitude [%] equation (A = a*V + b)
            V2A_a (float): 1st order coefficient of voltage [V] vs. amplitude [%] equation.
            V2A_b (float): 0-order coefficient of voltage [V] vs. amplitude [%] equation.

            pressure [Pa] vs. amplitude [%] equation (A = a*P + b)
            P2A_a (float): 1st order coefficient of pressure [Pa] vs. amplitude [%] equation.
            P2A_b (float): 0-order coefficient of pressure [Pa] vs. amplitude [%] equation.

            FWHM center wrt exit plane [mm] vs. set focus [%] equation (SF = a*FWHMC + b)
            DF2SF_a (float): 1st order coefficient of FWHM center wrt exit plane [mm] vs. set focus
                             [mm] equation.
            DF2SF_b (float): 0-order coefficient of FWHM center wrt exit plane [mm] vs. set focus
                             [mm] equation.

            F2EQF1_low_lim (float): The lower limit of the focus wrt exit plane the equation
                                    accounts for.
            F2EQF1_up_lim (float): The upper limit of the focus wrt exit plane the equation accounts
                                   for.

            for range F2EQF1_low_lim <= focus wrt exit plane <= F2EQF1_up_lim
            normalized pressure vs. focal depth wrt exit plane [mm] equation (EQF1 = F2EQF1_a0 +
                                                                              F2EQF1_a1*f +
                                                                              F2EQF1_a2*f^2 +
                                                                              F2EQF1_a3*f^3 +
                                                                              F2EQF1_a4*f^4 +
                                                                              F2EQF1_a5*f^5 +
                                                                              F2EQF1_a6*f^6 +
                                                                              F2EQF1_a7*f^7
                                                                              ).
            F2EQF1_a0 (float): 0-order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a1 (float): 1st order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a2 (float): 2nd order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a3 (float): 3rd order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a4 (float): 4th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a5 (float): 5th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a6 (float): 6th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF1_a7 (float): 7th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.

            F2EQF2_low_lim (float): The lower limit of the focus wrt exit plane the equation
                                    accounts for.
            F2EQF2_up_lim (float): The upper limit of the focus wrt exit plane the equation accounts
                                   for.

            for range F2EQF2_low_lim < focus wrt exit plane <= F2EQF2_up_lim
            normalized pressure vs. focal depth wrt exit plane [mm] equation (EQF2 = F2EQF2_a0 +
                                                                              F2EQF2_a1*f +
                                                                              F2EQF2_a2*f^2 +
                                                                              F2EQF2_a3*f^3 +
                                                                              F2EQF2_a4*f^4 +
                                                                              F2EQF2_a5*f^5 +
                                                                              F2EQF2_a6*f^6 +
                                                                              F2EQF2_a7*f^7 +
                                                                              ).
            F2EQF2_a0 (float): 0-order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a1 (float): 1st order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a2 (float): 2nd order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a3 (float): 3rd order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a4 (float): 4th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a5 (float): 5th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a6 (float): 6th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.
            F2EQF2_a7 (float): 7th order coefficient of normalized pressure vs. focal depth wrt exit
                               plane [mm] equation.

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
        self._equip_combos = config['Equipment']['Combinations']

        self._driving_sys = ds.DrivingSystem()
        def_ds_serial = ds.get_ds_serials()[0]
        self.driving_sys = def_ds_serial

        self._wait_for_trigger = False  # Default value for wait_for_trigger
        self._trigger_option = config['General']['Trigger options'].split('\n')[0]
        self._n_triggers = 0

        # set a temporary focus wrt mid bowl and operating frequency to set a default transducer
        self._chosen_power = None

        self._global_power = 0  # SC: global power [W]
        self._press = 0  # IGT: maximum pressure in free water [MPa]
        self._volt = 0  # IGT: voltage [V]
        self._ampl = 0  # IGT: amplitude [%]
        self._eq_factor = 0  # IGT: normalized pressure
        self._focus_wrt_mid_bowl = 40  # [mm]
        self._oper_freq = 0  # [kHz]

        # Degree used to dephase every nth elemen based on chosen degree. (0 = no dephasing).
        self._dephasing_degree = None

        self._transducer = tran.Transducer()
        def_tran_serial = tran.get_tran_serials()[0]
        self.transducer = def_tran_serial

        self._chosen_focus = self.get_focus_options()[0]
        self._focus_wrt_exit_plane = self._focus_wrt_mid_bowl - self._transducer.exit_plane_dist

        # If applicable, retrieve conversion parameters
        self._conv_param = {
            "V2A_a": 0,
            "V2A_b": 0,

            "P2A_a": 0,
            "P2A_b": 0,

            "DF2SF_a": 0,
            "DF2SF_b": 0,

            "F2EQF1_low_lim": 0,
            "F2EQF1_up_lim": 0,
            "F2EQF1_a0": 0,
            "F2EQF1_a1": 0,
            "F2EQF1_a2": 0,
            "F2EQF1_a3": 0,
            "F2EQF1_a4": 0,
            "F2EQF1_a5": 0,
            "F2EQF1_a6": 0,
            "F2EQF1_a7": 0,

            "F2EQF2_low_lim": 0,
            "F2EQF2_up_lim": 0,
            "F2EQF2_a0": 0,
            "F2EQF2_a1": 0,
            "F2EQF2_a2": 0,
            "F2EQF2_a3": 0,
            "F2EQF2_a4": 0,
            "F2EQF2_a5": 0,
            "F2EQF2_a6": 0,
            "F2EQF2_a7": 0,

            }

        self._ds_tran_combo = '~'.join([self._driving_sys.serial, self._transducer.serial])
        if self._ds_tran_combo in self._equip_combos:
            self._update_conv_param()

        # Timing parameters
        self._timing_param = {
            # # Pulse
            'pulse_dur': 0.25,  # [ms]
            'pulse_rep_int': 20,  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            'pulse_ramp_shape': config['General']['Ramp shapes'].split('\n')[0],
            'pulse_ramp_dur': 0,  # [ms]

            # # Pulse train
            'pulse_train_dur': 20,  # [ms]
            'pulse_train_rep_int': 20,  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            # 'pulse_train_ramp_shape': config['General']['Ramp shapes'].split('\n')[0],
            # 'pulse_train_ramp_dur': 0,  # [ms]

            # Pulse train repetition
            'pulse_train_rep_dur': 20,  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            # 'pulse_train_rep_ramp_shape': config['General']['Ramp shapes'].split('\n')[0],
            # 'pulse_train_rep_ramp_dur': 0,  # [ms]
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

        if self._driving_sys.manufact == config['Equipment.Manufacturer.IGT']['Name']:
            if self._ds_tran_combo in self._equip_combos:
                info += f"Maximum pressure in free water [MPa]: {self._press} \n "
                info += f"Voltage [V]: {self._volt} \n "
                info += f"Amplitude [%]: {self._ampl} \n "

                info += ("Voltage [V] vs. amplitude [%] equation (A = a*V + b): A = " +
                         f"{self.V2A_a}*V + {self.V2A_b} \n ")

                info += ("Pressure [Pa] vs. amplitude [%] equation (A = a*P + b): A = " +
                         f"{self.P2A_a}*P + {self.P2A_b} \n ")

                info += ("FWHM center wrt exit plane [mm] vs. set focus [%] equation (SF = " +
                         f"a*FWHMC + b): SF = {self.DF2SF_a}*FWHMC + {self.DF2SF_b} \n ")

                info += ("Normalized pressure [-] vs. focal depth wrt exit plane [mm] equation " +
                         f"between a focus wrt exit plane of {self.F2EQF1_low_lim} and " +
                         f"{self.F2EQF1_up_lim} [mm] (EQ1 = a0 + a1*f + a2*f^2 + a3*f^3 + a4*f^4 " +
                         f"+ a5*f^5): EQ1 = {self.F2EQF1_a0} + {self.F2EQF1_a1}*f + " +
                         f"{self.F2EQF1_a2}*f^2 + {self.F2EQF1_a3}*f^3 + {self.F2EQF1_a4}*f^4 + " +
                         f"{self.F2EQF1_a5}*f^5 + {self.F2EQF1_a6}*f^6 + {self.F2EQF1_a7}*f^7 \n ")

                info += ("Normalized pressure [-] vs. focal depth wrt exit plane [mm] equation " +
                         f"between a focus wrt exit plane of {self.F2EQF2_low_lim} and " +
                         f"{self.F2EQF2_up_lim} [mm] (EQ1 = a0 + a1*f + a2*f^2 + a3*f^3 + a4*f^4 " +
                         f"+ a5*f^5): EQ1 = {self.F2EQF2_a0} + {self.F2EQF2_a1}*f + " +
                         f"{self.F2EQF2_a2}*f^2 + {self.F2EQF2_a3}*f^3 + {self.F2EQF2_a4}*f^4 + " +
                         f"{self.F2EQF2_a5}*f^5 + {self.F2EQF2_a6}*f^6 + {self.F2EQF2_a7}*f^7\n ")

                info += ("Normalized pressure [-] based on chosen focal depth wrt exit plane of " +
                         f"{self._focus_wrt_exit_plane} [mm]: {self._eq_factor} \n ")

            else:
                info += ("Pressure correction with an increasing focal depth not available in the" +
                         " configuration file for this driving system and transducer combination!" +
                         " \n ")

                info += f"Amplitude [%]: {self._ampl} \n "

            info += f"Dephasing degree (0 = no dephasing): {self.dephasing_degree} \n "

        elif self._driving_sys.manufact == config['Equipment.Manufacturer.SC']['Name']:
            info += f"Global power [W]: {self._global_power} \n "

        info += f"Operating frequency [kHz]: {self._oper_freq} \n "
        info += f"Focal depth wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n "
        info += f"Focal depth wrt bowl middle [mm]: {self._focus_wrt_mid_bowl} \n "
        info += ("Normalized pressure based on chosen focal depth wrt exit plane [-]: " +
                 f"{self._eq_factor} \n ")

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
            self._ds_tran_combo = '~'.join([self._driving_sys.serial, self._transducer.serial])

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

        return config['General']['Trigger options'].split('\n')

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
            logger.error(f'{trigger_option} is not an available option.')
            sys.exit()
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
            self.pulse_train_rep_dur = self.pulse_train_dur

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
            self._ds_tran_combo = '~'.join([self._driving_sys.serial, self._transducer.serial])

            if self._ds_tran_combo in self._equip_combos:
                # New equipment selected, update conversion parameters
                self._update_conv_param()
                self._focus_wrt_mid_bowl = self.DF2SF_a * self._focus_wrt_exit_plane + self.DF2SF_b
            else:
                self._focus_wrt_mid_bowl = self._focus_wrt_exit_plane + self._transducer.exit_plane_dist

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

        return config['General']['Power options'].split('\n')

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
            logger.error(f'{chosen_power} is not an available option.')
            sys.exit()
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

        if self._driving_sys.manufact == config['Equipment.Manufacturer.SC']['Name']:
            is_validated = validate_value(global_power, 'Global power [W] (global_power)',
                                          True, True, False, False)
            if is_validated:
                self._global_power = global_power
                self._chosen_power = config['General']['Power option.glob_pow']

        else:
            # Chosen system is not SC.
            if global_power > 0:
                logger.error('Global power parameter is not available for ' +
                             'chosen driving system. Use ampl [%], press ' +
                             '[MPa] or volt [V] instead.')
                sys.exit()

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

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            is_validated = validate_value(press, 'Maximum pressure in free water [MPa] (press)',
                                          True, True, False, False)
            if is_validated:
                max_press = float(config['General']['Maximum pressure allowed in free water [MPa]'])
                if press > max_press:
                    logger.error(f'The set maximum pressure in free water of {press} [MPa] is ' +
                                 f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                                 ' your value.')
                    sys.exit()

                self._press = press

                self._chosen_power = config['General']['Power option.press']

                # Convert required amplitude
                self._calc_ampl()

                # Calculate voltage for logging
                self._calc_volt()

                logger.info(f'New maximum pressure in free water value of {self._press:.2f} [MPa]' +
                            f' results in a voltage of {self._volt:.2f} [V] and an amplitude ' +
                            f'of {self._ampl:.2f} [%].')
        else:
            logger.error('No pressure compensation parameters available in the configuration' +
                         ' file for chosen equipment combination. Enter amplitude [%].')
            sys.exit()

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

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            is_validated = validate_value(volt, 'Voltage [V] (volt)',
                                          True, True, False, False)
            if is_validated:
                self._volt = volt

                self._chosen_power = config['General']['Power option.volt']

                # Convert required to amplitude
                self._calc_ampl_using_volt()

                # Calculate maximum pressure in free water for logging purposes
                self._calc_press()

                logger.info(f'New voltage value of {self._volt:.2f} [V] results in a maximum' +
                            f' pressure in free water of {self._press:.2f} [MPa] and an amplitude' +
                            f' of {self._ampl:.2f} [%].')
        else:
            logger.error('No pressure compensation parameters available in the configuration' +
                         ' file for chosen equipment combination. Enter amplitude [%].')
            sys.exit()

    @property
    def ampl(self):
        """
        Getter method for the amplitude.

        Returns:
            float: The amplitude [%] for IGT.
        """

        return self._ampl

    @ampl.setter
    def ampl(self, ampl):
        """
        Setter method for the amplitude.

        Parameters:
            ampl (float): The amplitude [%] for IGT.
        """

        # set other parameters determine the intensity to None
        self._global_power = 0
        self._ampl = 0

        if self._driving_sys.manufact == config['Equipment.Manufacturer.IGT']['Name']:
            self._chosen_power = config['General']['Power option.ampl']

            is_validated = validate_value(ampl, 'Amplitude [%] (ampl)',
                                          True, True, False, False)
            if is_validated:
                self._ampl = ampl

            if self._ds_tran_combo in self._equip_combos:
                # Convert amplitude to voltage for logging
                self._calc_volt()

                # Convert amplitude to pressure for logging
                self._calc_press()

                logger.info(f'New amplitude value of {self._ampl:.2f} [%] results in a maximum' +
                            f' pressure in free water of {self._press:.2f} [MPa] and a voltage ' +
                            f'of {self._volt:.2f} [V].')

            else:
                # Equipment is not part a combination, so only set amplitude
                logger.info('Chosen transducer - driving system combination ' +
                            'is not apart of configured combinations. ' +
                            'Pressure and voltage cannot be calculated.')
        else:
            # Chosen system is not IGT.
            if ampl > 0:
                logger.error('Amplitude parameter is not available for ' +
                             'chosen driving system. Use global_power [mW]' +
                             ' instead.')
                sys.exit()

    def get_focus_options(self):
        """
        Returns a list of available focus options.

        Returns:
            List[str]: Available focus options.
        """

        return config['General']['Focus options'].split('\n')

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
            logger.error(f'{chosen_focus} is not an available option.')
            sys.exit()
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
        """

        is_validated = validate_value(focus, 'Focus wrt exit plane [mm] (focus_wrt_exit_plane)',
                                      True, True, False, False)

        if is_validated:
            if self._ds_tran_combo not in self._equip_combos:
                # Check if focus is within range if compensation equations are not applicable
                if focus < self._transducer.min_foc or focus > self._transducer.max_foc:
                    logger.error(f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                                 f'focus range of {self._transducer.min_foc} and ' +
                                 f'{self._transducer.max_foc} [mm] of transducer ' +
                                 f'{self._transducer.name}.')
                    sys.exit()

                logger.warning('Compensation equations are not available or applicable. ' +
                               'Calculate focus wrt mid bowl based on exit plane distance of ' +
                               f'{self._transducer.exit_plane_dist} [mm].')
                self._focus_wrt_mid_bowl = focus + self._transducer.exit_plane_dist

            else:
                self._focus_wrt_mid_bowl = self.DF2SF_a * focus + self.DF2SF_b

            self._chosen_focus = config['General']['Focus option.exit']
            self._focus_wrt_exit_plane = focus

            logger.info(f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                        f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            # Update normalized pressure based on new focal depth
            self._calc_eq_factor()

            # Update amplitude accordingly
            self._calc_ampl()

            # Update voltage accordingly
            self._calc_volt()

            logger.info(f"New focus wrt exit plane of {self._focus_wrt_exit_plane:.2f} [mm] " +
                        f" results in an equalization factor of {self._eq_factor:.2f} " +
                        f"recalcultating the maximum pressure in free water as {self._press:.2f} " +
                        f"[MPa], the voltage as {self._volt:.2f} [V], and the amplitude as " +
                        f"{self._ampl:.1f} [%].")

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
        """

        is_validated = validate_value(focus, 'Focus wrt mid bowl [mm] (focus_wrt_mid_bowl)',
                                      True, True, False, False)

        if is_validated:
            if self._ds_tran_combo in self._equip_combos and self.DF2SF_a != 0:
                self._focus_wrt_exit_plane = (focus - self.DF2SF_b) / self.DF2SF_a
            else:
                logger.warning('Compensation equations are not available or applicable, or ' +
                               'a-coefficient of focus equation (DF2SF_a) is zero. Calculate ' +
                               'focus wrt exit plane based on exit plane distance of ' +
                               f'{self._transducer.exit_plane_dist} [mm].')
                self._focus_wrt_exit_plane = focus - self._transducer.exit_plane_dist

                # Check if focus is within range if compensation equations are not applicable
                if self._focus_wrt_exit_plane < self._transducer.min_foc or self._focus_wrt_exit_plane > self._transducer.max_foc:
                    logger.error(f'Focus wrt exit plane of {focus} [mm] is not within the set ' +
                                 f'focus range of {self._transducer.min_foc} and ' +
                                 f'{self._transducer.max_foc} [mm] of transducer ' +
                                 f'{self._transducer.name}.')
                    sys.exit()

            self._chosen_focus = config['General']['Focus option.bowl']
            self._focus_wrt_mid_bowl = focus

            logger.info(f'Focus wrt exit plane [mm]: {self._focus_wrt_exit_plane} \n ' +
                        f'Focus wrt bowl middle [mm]: {self._focus_wrt_mid_bowl}')

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            # Update normalized pressure based on new focal depth
            self._calc_eq_factor()

            # Update amplitude accordingly
            self._calc_ampl()

            # Update voltage accordingly
            self._calc_volt()

            logger.info(f"New focus wrt exit plane of {self._focus_wrt_mid_bowl:.2f} [mm] results" +
                        f" in an equalization factor of {self._eq_factor:.2f} recalcultating the " +
                        f"maximum pressure in free water as {self._press:.2f} [MPa], the voltage " +
                        f"as {self._volt:.2f} [V], and the amplitude as {self._ampl:.1f} [%].")

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
    def V2A_a(self):
        """
        Getter method for the 1st order coefficient of voltage [V] vs. amplitude [%] equation.

        Returns:
            float: The 1st order coefficient of voltage [V] vs. amplitude [%] equation.
        """

        return float(self._conv_param['V2A_a'])

    @property
    def V2A_b(self):
        """
        Getter method for the 0-order coefficient of voltage [V] vs. amplitude [%] equation.

        Returns:
            float: The 0-order coefficient of voltage [V] vs. amplitude [%] equation.
        """

        return float(self._conv_param['V2A_b'])

    @property
    def P2A_a(self):
        """
        Getter method for the 1st order coefficient of pressure [Pa] vs. amplitude [%] equation.

        Returns:
            float: The 1st order coefficient of pressure [Pa] vs. amplitude [%] equation.
        """

        return float(self._conv_param['P2A_a'])

    @property
    def P2A_b(self):
        """
        Getter method for the 0-order coefficient of pressure [Pa] vs. amplitude [%] equation.

        Returns:
            float: The 0-order coefficient of pressure [Pa] vs. amplitude [%] equation.
        """

        return float(self._conv_param['P2A_b'])

    @property
    def DF2SF_a(self):
        """
        Getter method for the 1st order coefficient of FWHM center wrt exit plane [mm] vs. set focus
        [mm] equation.

        Returns:
            float: The 1st order coefficient of FWHM center wrt exit plane [mm] vs. set focus [mm]
            equation.
        """

        return float(self._conv_param['DF2SF_a'])

    @property
    def DF2SF_b(self):
        """
        Getter method for the 0-order coefficient of FWHM center wrt exit plane [mm] vs. set focus
        [mm] equation.

        Returns:
            float: The 0-order coefficient of FWHM center wrt exit plane [mm] vs. set focus [mm]
            equation.
        """

        return float(self._conv_param['DF2SF_b'])

    @property
    def F2EQF1_low_lim(self):
        """
        Getter method for the lower limit of F2EQF1 focal depth wrt exit plane [mm].

        Returns:
            float: The lower limit of F2EQF1 focal depth wrt exit plane [mm].
        """

        return float(self._conv_param['F2EQF1_low_lim'])

    @property
    def F2EQF1_up_lim(self):
        """
        Getter method for the upper limit of F2EQF1 focal depth wrt exit plane [mm].

        Returns:
            float: The upper limit of F2EQF1 focal depth wrt exit plane [mm].
        """

        return float(self._conv_param['F2EQF1_up_lim'])

    @property
    def F2EQF1_a0(self):
        """
        Getter method for the 0-order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 0-order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a0'])

    @property
    def F2EQF1_a1(self):
        """
        Getter method for the 1st order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 1st order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a1'])

    @property
    def F2EQF1_a2(self):
        """
        Getter method for the 2nd order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 2nd order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a2'])

    @property
    def F2EQF1_a3(self):
        """
        Getter method for the 3rd order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 3rd order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a3'])

    @property
    def F2EQF1_a4(self):
        """
        Getter method for the 4th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 4th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a4'])

    @property
    def F2EQF1_a5(self):
        """
        Getter method for the 5th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 5th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a5'])

    @property
    def F2EQF1_a6(self):
        """
        Getter method for the 6th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 6th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a6'])

    @property
    def F2EQF1_a7(self):
        """
        Getter method for the 7th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 7th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF1_a7'])

    @property
    def F2EQF2_low_lim(self):
        """
        Getter method for the lower limit of F2EQF2 focal depth wrt exit plane [mm].

        Returns:
            float: The lower limit of F2EQF2 focal depth wrt exit plane [mm].
        """

        return float(self._conv_param['F2EQF2_low_lim'])

    @property
    def F2EQF2_up_lim(self):
        """
        Getter method for the upper limit of F2EQF2 focal depth wrt exit plane [mm].

        Returns:
            float: The upper limit of F2EQF2 focal depth wrt exit plane [mm].
        """

        return float(self._conv_param['F2EQF2_up_lim'])

    @property
    def F2EQF2_a0(self):
        """
        Getter method for the 0-order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 0-order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a0'])

    @property
    def F2EQF2_a1(self):
        """
        Getter method for the 1st order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 1st order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a1'])

    @property
    def F2EQF2_a2(self):
        """
        Getter method for the 2nd order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 2nd order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a2'])

    @property
    def F2EQF2_a3(self):
        """
        Getter method for the 3rd order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 3rd order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a3'])

    @property
    def F2EQF2_a4(self):
        """
        Getter method for the 4th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 4th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a4'])

    @property
    def F2EQF2_a5(self):
        """
        Getter method for the 5th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 5th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a5'])

    @property
    def F2EQF2_a6(self):
        """
        Getter method for the 6th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 6th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a6'])

    @property
    def F2EQF2_a7(self):
        """
        Getter method for the 7th order coefficient of normalized pressure vs. focal depth wrt exit
        plane [mm] equation.

        Returns:
            float: The 5th order coefficient of normalized pressure vs. focal depth wrt exit plane
            [mm] equation.
        """

        return float(self._conv_param['F2EQF2_a7'])

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

    def get_ramp_shapes(self):
        """
        Returns a list of available ramp shapes for pulse modulation.

        Returns:
            List[str]: Available ramp shapes.
        """

        return config['General']['Ramp shapes'].split('\n')

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
            logger.error(f'{pulse_ramp_shape} is not an available option.')
            sys.exit()
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
            
            if self._driving_sys.manufact == config['Equipment.Manufacturer.SC']['Name']:
                # SC doesn't have a pulse train repetition definition so set to None
                
                self._timing_param['pulse_train_rep_int'] = None
                self._timing_param['pulse_train_rep_dur'] = None
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

    def _update_conv_param(self):
        """
        Update method for the conversion parameters to compensate for decreasing pressure with
        increasing focal depth wrt exit plane.
        """

        self._conv_param = {
            "V2A_a": config['Equipment.Combination.' + self._ds_tran_combo]['V2A a-coeff'],
            "V2A_b": config['Equipment.Combination.' + self._ds_tran_combo]['V2A b-coeff'],

            "P2A_a": config['Equipment.Combination.' + self._ds_tran_combo]['P2A a-coeff'],
            "P2A_b": config['Equipment.Combination.' + self._ds_tran_combo]['P2A b-coeff'],

            "DF2SF_a": config['Equipment.Combination.' + self._ds_tran_combo]['DF2SF a-coeff'],
            "DF2SF_b": config['Equipment.Combination.' + self._ds_tran_combo]['DF2SF b-coeff'],

            "F2EQF1_low_lim": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 foc. low lim.'],
            "F2EQF1_up_lim": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 foc. upper lim.'],
            "F2EQF1_a0": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a0-coeff'],
            "F2EQF1_a1": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a1-coeff'],
            "F2EQF1_a2": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a2-coeff'],
            "F2EQF1_a3": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a3-coeff'],
            "F2EQF1_a4": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a4-coeff'],
            "F2EQF1_a5": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a5-coeff'],
            "F2EQF1_a6": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a6-coeff'],
            "F2EQF1_a7": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF1 a7-coeff'],

            "F2EQF2_low_lim": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 foc. low lim.'],
            "F2EQF2_up_lim": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 foc. upper lim.'],
            "F2EQF2_a0": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a0-coeff'],
            "F2EQF2_a1": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a1-coeff'],
            "F2EQF2_a2": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a2-coeff'],
            "F2EQF2_a3": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a3-coeff'],
            "F2EQF2_a4": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a4-coeff'],
            "F2EQF2_a5": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a5-coeff'],
            "F2EQF2_a6": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a6-coeff'],
            "F2EQF2_a7": config['Equipment.Combination.' + self._ds_tran_combo]['F2EQF2 a7-coeff'],

            }

        self._calc_eq_factor()

        # Convert to amplitude, assumption that the maximum pressure in free water remains the same
        self._calc_ampl()

        self._calc_volt()

        logger.info('New equipment pressure compensation coefficients result in a maximum' +
                    f' pressure in free water of {self._press:.2f} [MPa], a voltage of ' +
                    f'{self._volt:.2f} [V] and an amplitude of {self._ampl:.2f} [%].')

    def _calc_eq_factor(self):
        """
        Calculate equalization factor of the pressure vs. focal depth wrt exit plane [mm] equation
        (EQF = a0 + a1*f + a2*f^2 + a3*f^3 + a4*f^4 + a5*f^5).
        """

        if self._focus_wrt_exit_plane >= self.F2EQF1_low_lim and self._focus_wrt_exit_plane <= self.F2EQF1_up_lim:
            self._eq_factor = (self.F2EQF1_a0 + self.F2EQF1_a1*self._focus_wrt_exit_plane +
                               self.F2EQF1_a2*math.pow(self._focus_wrt_exit_plane, 2) +
                               self.F2EQF1_a3*math.pow(self._focus_wrt_exit_plane, 3) +
                               self.F2EQF1_a4*math.pow(self._focus_wrt_exit_plane, 4) +
                               self.F2EQF1_a5*math.pow(self._focus_wrt_exit_plane, 5) +
                               self.F2EQF1_a6*math.pow(self._focus_wrt_exit_plane, 6) +
                               self.F2EQF1_a7*math.pow(self._focus_wrt_exit_plane, 7))
        elif self._focus_wrt_exit_plane > self.F2EQF2_low_lim and self._focus_wrt_exit_plane <= self.F2EQF2_up_lim:
            self._eq_factor = (self.F2EQF2_a0 + self.F2EQF2_a1*self._focus_wrt_exit_plane +
                               self.F2EQF2_a2*math.pow(self._focus_wrt_exit_plane, 2) +
                               self.F2EQF2_a3*math.pow(self._focus_wrt_exit_plane, 3) +
                               self.F2EQF2_a4*math.pow(self._focus_wrt_exit_plane, 4) +
                               self.F2EQF2_a5*math.pow(self._focus_wrt_exit_plane, 5) +
                               self.F2EQF2_a6*math.pow(self._focus_wrt_exit_plane, 6) +
                               self.F2EQF2_a7*math.pow(self._focus_wrt_exit_plane, 7))
        else:
            logger.error(f'Focus wrt exit plane of {self._focus_wrt_exit_plane} mm is not within ' +
                         f'the limits of {self.F2EQF1_low_lim} and {self.F2EQF2_up_lim} [mm].')
            sys.exit()

    def _calc_volt(self):
        """
        Calculate amplitude [%] vs. voltage [V] equation V = (A - b)/a when amplitude is
        updated.
        """

        # Prevent division by zero
        if self.V2A_a == 0:
            self._volt = 0
        else:
            self._volt = (self._ampl - self.V2A_b) / self.V2A_a

    def _calc_ampl(self):
        """
        Calculate pressure [Pa] vs. amplitude [%] equation (A = a*(P*EQF) + b) when pressure is
        updated.
        """

        press_pa = self._press * 1e6  # convert to Pa
        self._ampl = self.P2A_a * (press_pa * self._eq_factor) + self.P2A_b
        if self._ampl > 100:
            logger.warning(('Calculated amplitude exceeds 100%, so cut off the amplitude at 100% ' +
                            'and recalculate the pressure.'))
            self._ampl = 100
            self._calc_press()
            self._calc_volt()
        elif self._ampl < 0:
            logger.warning(('Calculated amplitude below 0%, so cut off the amplitude at 0% and ' +
                            'recalculate the pressure.'))
            self._ampl = 0
            self._calc_press()
            self._calc_volt()

    def _calc_ampl_using_volt(self):
        """
        Calculate voltage [V] vs. amplitude [%] equation (A = a*V + b) when voltage is
        updated.
        """

        self._ampl = self.V2A_a * self._volt + self.V2A_b

    def _calc_press(self):
        """
        Calculate pressure [Pa] vs. amplitude [%] equation (P = (A - b)/(a*EQF)) when amplitude is
        updated.
        """

        press_pa = (self._ampl - self.P2A_b) / (self.P2A_a * self._eq_factor)
        press_mpa = press_pa * 1e-6  # convert to MPa

        max_press = float(config['General']['Maximum pressure allowed in free water [MPa]'])
        if press_mpa > max_press:
            logger.error(f'The set maximum pressure in free water of {press_mpa} [MPa] is ' +
                         f'crossing the allowed limit of {max_press} [MPa]. Please change' +
                         ' your value.')
            sys.exit()

        self._press = press_mpa  # convert to MPa


def validate_value(value, input_param, check_num, check_pos, check_nonzero, check_bool):
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

    Returns:
        bool: True if all checks pass; otherwise, logs errors and exits.
    """

    val_messages = []

    if check_nonzero and value == 0:
        val_messages.append(f'{input_param} is not allowed to be zero.')
    if check_num and not isinstance(value, (int, float)):
        val_messages.append(f'{input_param} should be a number.')
    if check_pos and value < 0:
        val_messages.append(f'{input_param} is not allowed to be negative.')

    if check_bool and not isinstance(value, bool):
        val_messages.append(f'{input_param} should be a boolean.')

    if val_messages:
        for message in val_messages:
            logger.error(message)
        sys.exit()

    return True
