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

# Own packages
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import logger
from fus_driving_systems.utils import get_config_value


class Transducer:
    """
    Class representing an ultrasound transducer.

    Attributes:
        serial (str): Serial number of the transducer.
        name (str): Name of the transducer.
        manufact (str): Name of the manufacturer.
        elements (int): Number of elements.
        fund_freq (int): Fundamental frequency of the transducer [kHz].
        natural_foc (float): Natural focal depth of the transducer [mm].
        exit_plane_dist (float): Distance between exit plane and first element [mm].
        min_foc (float): Minimum focal depth of the transducer [mm].
        max_foc (float): Maximum focal depth of the transducer [mm].
        steer_info (str):  ONLY USED FOR IGT! Path to the steer information of the transducer.
        is_active (Boolean): Indication if the transducer is used with the code.
    """

    def __init__(self):
        """
        Initializes a Transducer object with default values.
        """

        self.serial = None
        self.name = None
        self.manufact = None
        self.elements = 0
        self.fund_freq = 0  # [kHz]
        self.natural_foc = 0  # [mm]
        self.exit_plane_dist = 0  # [mm]
        self.min_foc = float(get_config_value(logger, config, 'Focus', 'Default.minimum', 0))  # [mm]
        self.max_foc = float(get_config_value(logger, config, 'Focus', 'Default.maximum', 1000))  # [mm]
        self.steer_info = None
        self.is_active = True

    def set_transducer_info(self, serial):
        """
        Sets the transducer based on the provided serial number.

        Parameters:
            serial (str): Serial number of the transducer.
        """

        try:
            self.serial = serial
            section = 'Equipment.Transducer.' + serial
            self.name = get_config_value(logger, config, section, 'Name', 'Unknown transducer name')
            self.manufact = get_config_value(logger, config, section, 'Manufacturer',
                                             'Unknown transducer manufacturer')
            self.elements = int(get_config_value(logger, config, section, 'Elements', 0, True))
            self.fund_freq = int(get_config_value(logger, config, section, 'Fund. freq.', 0, True))
            self.natural_foc = float(get_config_value(logger, config, section, 'Natural focus', 0))
            self.exit_plane_dist = float(get_config_value(logger, config, section,
                                                          'Exit plane - first element dist.', 0))
            default_min = float(get_config_value(logger, config, 'Focus', 'Default.minimum', 0))
            self.min_foc = float(get_config_value(logger, config, section, 'Min. focus',
                                                  default_min))

            default_max = float(get_config_value(logger, config, 'Focus', 'Default.maximum', 1000))

            self.max_foc = float(get_config_value(logger, config, section, 'Max. focus',
                                                  default_max))

            self.steer_info = get_config_value(logger, config, section, 'Steer information',
                                               None, True)
            self.is_active = get_config_value(logger, config, section, 'Active?', 'True') == 'True'

        except KeyError:
            message = f'No transducer with serial number {serial} found in configuration file.'
            logger.critical(message)
            sys.exit(message)

    def __str__(self):
        """
        Returns a formatted string containing information about the transducer.

        Returns:
            str: Formatted information about the transducer.
        """

        info = ''
        info += f"Transducer serial number: {self.serial} \n "
        info += f"Transducer name: {self.name} \n "
        info += f"Transducer manufacturer: {self.manufact} \n "
        info += f"Transducer elements: {self.elements} \n "
        info += f"Transducer fundamental frequency [kHz]: {self.fund_freq} \n "
        info += f"Transducer natural focus [mm]: {self.natural_foc} \n "
        info += f"Transducer exit plane - first elem. distance [mm]: {self.exit_plane_dist} \n "
        info += f"Transducer min. focus [mm]: {self.min_foc} \n "
        info += f"Transducer max. focus [mm]: {self.max_foc} \n "
        info += ("Transducer steer table (Note: only used i.c.w. IGT driving sys.):" +
                 f" {self.steer_info} \n ")

        return info


def get_tran_serials():
    """
    Returns a list of serial numbers for available transducers.

    Returns:
        List[str]: Serial numbers for available transducers.
    """

    serial_trans = get_config_value(logger, config, 'Equipment', 'Transducers', '',
                                    True).split('\n')

    active_serials = []
    for serial in serial_trans:
        # only extract active tranducers
        section = 'Equipment.Transducer.' + serial
        if get_config_value(logger, config, section, 'Active?', 'True') == 'True':
            active_serials.append(serial)

    if len(active_serials) < 1:
        message = 'No active tranducers found in configuration file.'
        logger.critical(message)
        sys.exit(message)

    return active_serials


def get_tran_names():
    """
    Returns a list of names of available transducers.

    Returns:
        List[str]: Names of available transducers.
    """

    names = []
    for serial in get_tran_serials():
        try:
            section = 'Equipment.Transducer.' + serial
            tran_name = get_config_value(logger, config, section, 'Name', 'Unknown transducer name')
        except KeyError:
            message = (f'No transducer with serial number {serial} found in' +
                       ' configuration file.')
            logger.critical(message)
            sys.exit(message)

        names.append(tran_name)

    if len(names) < 1:
        message = 'No transducers found in configuration file.'
        logger.critical(message)
        sys.exit(message)

    return names


def get_tran_list():
    """
    Returns a list of available transducer objects.

    Returns:
        List[Obj]: Objects of available transducers.
    """

    tran_list = []
    for serial in get_tran_serials():
        try:
            tran = Transducer()
            tran.set_transducer_info(serial)
        except KeyError:
            message = (f'No transducer with serial number {serial} found in' +
                       ' configuration file.')
            logger.critical(message)
            sys.exit(message)

        tran_list.append(tran)

    if len(tran_list) < 1:
        message = 'No transducers found in configuration file.'
        logger.critical(message)
        sys.exit(message)

    return tran_list


def get_serial_from_name(name):
    """
    Returns the serial number matching the given name.

    Args:
        name (str): The name of the device.

    Returns:
        str: The serial number, or None if no match is found.
    """

    for tran in get_tran_list():
        if tran.name == name:

            return tran.serial
