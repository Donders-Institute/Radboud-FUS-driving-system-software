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
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 0.8),
https://github.com/Donders-Institute/Radboud-FUS-measurement-kit
"""

# Basic packages

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
        the focus are overridden.
        _chosen_power (str): The chosen power parameter like amplitude or global power.
        _global_power (float): [SC] global power [W].
        _press (float): [IGT] maximum pressure in free water [MPa].
        _volt (float): [IGT] voltage [V].
        _ampl (float): [IGT] amplitude [%].
        _focus (float): Focal depth of the sequence [mm].
        _ds_tran_combo (str): combination of driving system and transducer serial numbers.
        _conv_param (dict): Conversion parameters to compensate for decreasing pressure with
        increasing focal depth.
            voltage [V] vs. amplitude [%] equation (A = a*V + b)
            V2A_a (float): 1st order coefficient of voltage [V] vs. amplitude [%] equation.
            V2A_b (float): 0-order coefficient of voltage [V] vs. amplitude [%] equation.
            normalized pressure vs. focal depth [mm] equation (Pnorm = a0 + a1*f + a2*f^2 + a3*f^3 +
                                                               a4*f^4 + a5*f^5).
            a0 (float): 0-order coefficient of normalized pressure vs. focal depth [mm] equation.
            a1 (float): 1st order coefficient of normalized pressure vs. focal depth [mm] equation.
            a2 (float): 2nd order coefficient of normalized pressure vs. focal depth [mm] equation.
            a3 (float): 3rd order coefficient of normalized pressure vs. focal depth [mm] equation.
            a4 (float): 4th order coefficient of normalized pressure vs. focal depth [mm] equation.
            a5 (float): 5th order coefficient of normalized pressure vs. focal depth [mm] equation.

            pressure [MPa] vs. voltage [V] equation (P = a*V + b)
            V2P_a (float): 1st order coefficient of pressure [MPa] vs. voltage [V] equation.
            V2P_b (float): 0-order coefficient of pressure [MPa] vs. voltage [V] equation.
        _norm_press (float): [IGT] normalized pressure based on chosen focal depth [-].
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

        # set a temporary focus and operating frequency to set a default transducer
        self._chosen_power = ''
        self._global_power = -1  # SC: global power [W]
        self._press = -1  # IGT: maximum pressure in free water [MPa]
        self._volt = -1  # IGT: voltage [V]
        self._ampl = -1  # IGT: amplitude [%]
        self._norm_press = 0  # IGT: normalized pressure
        self._focus = 40  # [mm]
        self._oper_freq = 0  # [kHz]

        # Degree used to dephase every nth elemen based on chosen degree. (0 = no dephasing).
        self._dephasing_degree = None

        self._transducer = tran.Transducer()
        def_tran_serial = tran.get_tran_serials()[0]
        self.transducer = def_tran_serial

        # If applicable, retrieve conversion parameters
        self._ds_tran_combo = '~'.join([self._driving_sys.serial, self._transducer.serial])
        if self._ds_tran_combo in self._equip_combos:
            self._update_conv_param()

        # Timing parameters
        self._timing_param = {
            # # Pulse
            'pulse_dur': 0.25,  # [ms]
            'pulse_rep_int': 200,  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            'pulse_ramp_shape': config['General']['Ramp shapes'].split('\n')[0],
            'pulse_ramp_dur': 0,  # [ms]

            # # Pulse train
            'pulse_train_dur': 200,  # [ms]
            'pulse_train_rep_int': 200,  # [ms]

            # Rectangular - no ramping, Linear, Tukey
            # 'pulse_train_ramp_shape': config['General']['Ramp shapes'].split('\n')[0],
            # 'pulse_train_ramp_dur': 0,  # [ms]

            # Pulse train repetition
            'pulse_train_rep_dur': 200,  # [ms]

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
                info += ("Normalized pressure [-] vs. focal depth [mm] equation (Pnorm = a0 + " +
                         f"a1*f + a2*f^2 + a3*f^3 + a4*f^4 + a5*f^5): Pnorm = {self.a0} + " +
                         f"{self.a1}*f + {self.a2}*f^2 + {self.a3}*f^3 + {self.a4}*f^4 + " +
                         f"{self.a5}*f^5 \n ")
                info += (f"Normalized pressure [-] based on chosen focal depth of {self._focus}" +
                         f" [mm]: {self._norm_press} \n ")
                info += ("Pressure [MPa] vs. voltage [V] equation (P = a*V + b): P = " +
                         f"{self.V2P_a}*V + {self.V2P_b} \n ")
            else:
                info += ("Pressure correction with an increasing focal depth not available in the" +
                         " configuration file for this driving system and transducer combination!" +
                         " \n ")
                info += f"Amplitude [%]: {self._ampl} \n "

            info += f"Dephasing degree (0 = no dephasing): {self.dephasing_degree} \n "

        elif self._driving_sys.manufact == config['Equipment.Manufacturer.SC']['Name']:
            info += f"Global power [W]: {self._global_power} \n "

        info += f"Operating frequency [kHz]: {self._oper_freq} \n "
        info += f"Focal depth [mm]: {self._focus} \n "
        info += f"Normalized pressure based on chosen focal depth [-]: {self._norm_press} \n "

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
        self._n_triggers = n_triggers

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
        self._focus = self._transducer.min_foc  # [mm]

        # Check if driving system is initialized
        if hasattr(self, '_driving_sys'):
            # Update equipment combo
            self._ds_tran_combo = '~'.join([self._driving_sys.serial, self._transducer.serial])

            if self._ds_tran_combo in self._equip_combos:
                # New equipment selected, update conversion parameters
                self._update_conv_param()

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

        self._oper_freq = int(oper_freq)

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

        if self._driving_sys.manufact == config['Equipment.Manufacturer.SC']['Name']:
            self._global_power = global_power
            self._chosen_power = config['General']['Power option.glob_pow']

            # set other parameters determine the intensity to None
            self.ampl = -1
        else:
            # Chosen system is not SC, so check if another value is set.
            if global_power == -1 and self._ampl > -1:
                self._global_power = -1

            else:
                logger.warning('Global power parameter is not available for ' +
                               'chosen driving system. Use ampl [%], press ' +
                               '[MPa] or volt [V] instead.')

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

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            self._press = press
            self._chosen_power = config['General']['Power option.press']

            # Calculate required voltage
            self._calc_volt()

            # Convert required voltage to amplitude
            self._calc_ampl()

            logger.info(f'New maximum pressure in free water value of {self._press:.2f} [MPa] ' +
                        f'results in a voltage of {self._volt:.2f} [V] and an amplitude ' +
                        f'of {self._ampl:.2f} [%].')

            # set other parameters determine the intensity to None
            self.global_power = -1
        else:
            logger.warning('No pressure compensation parameters available in the configuration' +
                           ' file for chosen equipment combination. Enter amplitude [%].')

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
        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            self._volt = volt
            self._chosen_power = config['General']['Power option.volt']

            # Calculate maximum pressure in free water for logging purposes
            self._calc_press()

            # Convert required to amplitude
            self._calc_ampl()

            logger.info(f'New voltage value of {self._volt:.2f} [V] results in a maximum' +
                        f' pressure in free water of {self._press:.2f} [MPa] and an amplitude ' +
                        f'of {self._ampl:.2f} [%].')

            # set other parameters determine the intensity to None
            self.global_power = -1

        else:
            logger.warning('No pressure compensation parameters available in the configuration' +
                           ' file for chosen equipment combination. Enter amplitude [%].')

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
        if self._driving_sys.manufact == config['Equipment.Manufacturer.IGT']['Name']:
            self._chosen_power = config['General']['Power option.ampl']
            if self._ds_tran_combo in self._equip_combos:
                self._ampl = ampl

                # Convert amplitude to voltage for logging
                self._volt = (self._ampl - self.V2A_b) / self.V2A_a

                # Convert voltage to pressure for logging
                self._calc_press()

                logger.info(f'New amplitude value of {self._ampl:.2f} [%] results in a maximum' +
                            f' pressure in free water of {self._press:.2f} [MPa] and a voltage ' +
                            f'of {self._volt:.2f} [V].')

                # set other parameters determine the intensity to None
                self.global_power = -1
            else:
                # Equipment is not part a combination, so only set amplitude
                self._ampl = ampl
                logger.info('Chosen transducer - driving system combination ' +
                            'is not apart of configured combinations. ' +
                            'Pressure and voltage cannot be calculated, so ' +
                            ' only amplitude is accepted as input.')
        else:
            # Chosen system is not IGT, so check if another value is set.
            if ampl == -1 and self._global_power > -1:
                self._ampl = -1
                self._volt = -1
                self._press = -1

            else:
                logger.warning('Amplitude parameter is not available for ' +
                               'chosen driving system. Use global_power [mW]' +
                               ' instead.')

    @property
    def focus(self):
        """
        Getter method for the focal depth.

        Returns:
            float: The focal depth [mm].
        """

        return self._focus

    @focus.setter
    def focus(self, focus):
        """
        Setter method for the focal depth.

        Parameters:
            focus (float): Focal depth [mm].
        """

        self._focus = focus

        # Check if pressure compensation is available for chosen equipment
        if self._ds_tran_combo in self._equip_combos:
            # Update normalized pressure based on new focal depth
            self._calc_norm_press()

            # Update voltage accordingly
            self._calc_volt()

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
            the focus are overriden.
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
    def a0(self):
        """
        Getter method for the 0-order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 0-order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a0'])

    @property
    def a1(self):
        """
        Getter method for the 1st order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 1st order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a1'])

    @property
    def a2(self):
        """
        Getter method for the 2nd order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 2nd order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a2'])

    @property
    def a3(self):
        """
        Getter method for the 3rd order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 3rd order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a3'])

    @property
    def a4(self):
        """
        Getter method for the 4th order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 4th order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a4'])

    @property
    def a5(self):
        """
        Getter method for the 5th order coefficient of normalized pressure vs. focal depth [mm]
        equation.

        Returns:
            float: The 5th order coefficient of normalized pressure vs. focal depth [mm] equation.
        """

        return float(self._conv_param['a5'])

    @property
    def V2P_a(self):
        """
        Getter method for the 1st order coefficient of pressure [MPa] vs. voltage [V] equation.

        Returns:
            float: The 1st order coefficient of pressure [MPa] vs. voltage [V] equation.
        """

        return float(self._conv_param['V2P_a'])

    @property
    def V2P_b(self):
        """
        Getter method for the 0-order coefficient of pressure [MPa] vs. voltage [V] equation.

        Returns:
            float: The 0-order coefficient of pressure [MPa] vs. voltage [V] equation.
        """

        return float(self._conv_param['V2P_b'])

    @property
    def norm_press(self):
        """
        Getter method for the normalized pressure based on chosen focal depth [-].

        Returns:
            float: The normalized pressure based on chosen focal depth [-].
        """

        return self._norm_press

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

        self._timing_param['pulse_train_dur'] = pulse_train_dur

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

        # convert pulse train repetition duration in seconds to milliseconds
        self._timing_param['pulse_train_rep_dur'] = pulse_train_rep_dur * 1e3

    def _update_conv_param(self):
        """
        Update method for the conversion parameters to compensate for decreasing pressure with
        increasing focal depth.
        """

        self._conv_param = {
            "V2A_a": config['Equipment.Combination.' + self._ds_tran_combo]['V2A a-coeff'],
            "V2A_b": config['Equipment.Combination.' + self._ds_tran_combo]['V2A b-coeff'],
            "a0": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a0-coeff'],
            "a1": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a1-coeff'],
            "a2": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a2-coeff'],
            "a3": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a3-coeff'],
            "a4": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a4-coeff'],
            "a5": config['Equipment.Combination.' + self._ds_tran_combo]['F2NP a5-coeff'],
            "V2P_a": config['Equipment.Combination.' + self._ds_tran_combo]['V2P a-coeff'],
            "V2P_b": config['Equipment.Combination.' + self._ds_tran_combo]['V2P b-coeff']
            }

        self._calc_norm_press()

        # Assumption that the maximum pressure in free water remains the same
        self._calc_volt()

        # Convert required to amplitude
        self._calc_ampl()

        logger.info('New equipment pressure compensation coefficients result in a maximum' +
                    f' pressure in free water of {self._press:.2f} [MPa], a voltage of ' +
                    f'{self._volt:.2f} [V] and an amplitude of {self._ampl:.2f} [%].')

    def _calc_norm_press(self):
        """
        Calculate normalized pressure vs. focal depth [mm] equation (Pnorm = a0 + a1*f + a2*f^2 +
                                                                     a3*f^3 + a4*f^4 + a5*f^5).
        """

        self._norm_press = (self.a0 + self.a1*self._focus + self.a2*math.pow(self._focus, 2) +
                            self.a3*math.pow(self._focus, 3) + self.a4*math.pow(self._focus, 4) +
                            self.a5*math.pow(self._focus, 5))

    def _calc_volt(self):
        """
        Calculate pressure [MPa] vs. voltage [V] equation V = ((P/Pnorm) - b)/a when pressure is
        updated.
        """

        # Prevent division by zero
        if self._norm_press == 0:
            self._volt = 0
        else:
            self._volt = (((self._press / self._norm_press) - self.V2P_a)
                          / self.V2P_a)

    def _calc_ampl(self):
        """
        Calculate voltage [V] vs. amplitude [%] equation (A = a*V + b) when voltage is
        updated.
        """

        self._ampl = self.V2A_a * self._volt + self.V2A_b

    def _calc_press(self):
        """
        Calculate pressure [MPa] vs. voltage [V] equation (P = (a*V + b)*Pnorm) when voltage is
        updated.
        """

        self._press = ((self.V2P_a * self._volt + self.V2P_b)
                       * self._norm_press)
