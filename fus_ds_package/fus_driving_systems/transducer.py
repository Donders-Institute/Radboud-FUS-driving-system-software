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

# Miscellaneous packages
import copy

# Own packages
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.config.logging_config import get_logger
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
        exit_plane_dist (float): Distance between exit plane and first element [mm].
        min_foc (float): Minimum focal depth of the transducer [mm].
        max_foc (float): Maximum focal depth of the transducer [mm].
        steer_info (str):  ONLY USED FOR IGT! Path to the steer information of the transducer.
        can_3d_steer (Boolean): Whether this transducer's own element geometry supports lateral
                                (x/y) steering in addition to depth (z), not just whether a
                                driving system happens to accept a 3D focus option, see
                                TransducerSlot._set_focus_xyz(). Only meaningful for a .ini-based
                                steer_info (transducer_xyz.Transducer); a .xlsx-based lookup
                                table has no x/y concept at all.
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
        # No natural_foc here -- for IGT it comes from the transducer's own .ini steer file
        # (transducer_xyz.Transducer.focalLength), read fresh at connect-time, so it can never
        # drift out of sync with a separately-maintained config copy. See igt_ds.py's
        # _set_phases().
        self.exit_plane_dist = 0  # [mm]
        self.min_foc = float(get_config_value(get_logger(), config, 'Focus',
                                              'Default.minimum', 0))  # [mm]
        self.max_foc = float(get_config_value(get_logger(), config, 'Focus',
                                              'Default.maximum', 1000))  # [mm]
        self.steer_info = None
        self.can_3d_steer = False
        self.is_active = True

    def set_transducer_info(self, serial):
        """
        Sets the transducer based on the provided serial number.

        Called by TransducerSlot.transducer's setter and get_tran_list() -- both can be given a
        serial that isn't actually in the configuration file (e.g. a typo). That is checked
        explicitly below, rather than relying on incidentally hitting one of the individual
        is_sys_exit=True fields further down and having to track down why that one field
        failed.

        Parameters:
            serial (str): Serial number of the transducer.
        """

        section = 'Equipment.Transducer.' + serial
        if section not in config:
            message = (f'No transducer with serial number {serial} found in configuration ' +
                       'file.')
            get_logger().critical(message)
            sys.exit(message)

        self.serial = serial
        self.name = get_config_value(get_logger(), config, section, 'Name',
                                     'Unknown transducer name')
        self.manufact = get_config_value(get_logger(), config, section, 'Manufacturer',
                                         'Unknown transducer manufacturer')
        self.elements = int(get_config_value(
            get_logger(), config, section, 'Elements', 0, True))
        self.fund_freq = int(get_config_value(
            get_logger(), config, section, 'Fund. freq.', 0, True))
        self.exit_plane_dist = float(get_config_value(get_logger(), config, section,
                                                      'Exit plane - first element dist.', 0))
        default_min = float(get_config_value(
            get_logger(), config, 'Focus', 'Default.minimum', 0))
        self.min_foc = float(get_config_value(get_logger(), config, section, 'Min. focus',
                                              default_min))

        default_max = float(get_config_value(
            get_logger(), config, 'Focus', 'Default.maximum', 1000))

        self.max_foc = float(get_config_value(get_logger(), config, section, 'Max. focus',
                                              default_max))

        self.steer_info = get_config_value(get_logger(), config, section, 'Steer information',
                                           None, True)
        self.can_3d_steer = get_config_value(
            get_logger(), config, section, 'Can 3D steer?', 'False') == 'True'
        if self.can_3d_steer and not self.steer_info.endswith('.ini'):
            message = (f'{serial} is configured with can_3d_steer=True, but its steer '
                       f'information ({self.steer_info}) is not a .ini file -- 3D steering is ' +
                       'only possible for the transducer_xyz.Transducer (.ini) steer path.')
            get_logger().critical(message)
            sys.exit(message)
        self.is_active = get_config_value(
            get_logger(), config, section, 'Active?', 'True') == 'True'

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
        info += f"Transducer exit plane - first elem. distance [mm]: {self.exit_plane_dist} \n "
        info += f"Transducer min. focus [mm]: {self.min_foc:.2f} \n "
        info += f"Transducer max. focus [mm]: {self.max_foc:.2f} \n "
        info += ("Transducer steer table (Note: only used i.c.w. IGT driving sys.):" +
                 f" {self.steer_info} \n ")
        info += f"Transducer can 3D steer: {self.can_3d_steer} \n "

        return info

    def clone(self):
        """
        Creates and returns a new instance of the Transducer class with the same attribute
        values.

        The new instance is a deep copy of the current instance, ensuring that changes to the
        cloned object do not affect the original object.

        Returns:
            CharacSequence: A new instance of the Transducer class with copied attribute values.
        """

        new_instance = Transducer()
        new_instance.__dict__ = copy.deepcopy(self.__dict__)  # Copy all attributes
        return new_instance


def get_tran_serials():
    """
    Returns a list of serial numbers for available transducers.

    Returns:
        List[str]: Serial numbers for available transducers.
    """

    serial_trans = get_config_value(get_logger(), config, 'Equipment', 'Transducers', '',
                                    True).split('\n')

    active_serials = []
    for serial in serial_trans:
        # only extract active tranducers
        section = 'Equipment.Transducer.' + serial
        if get_config_value(get_logger(), config, section, 'Active?', 'True') == 'True':
            active_serials.append(serial)

    if len(active_serials) < 1:
        message = 'No active tranducers found in configuration file.'
        get_logger().critical(message)
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
        section = 'Equipment.Transducer.' + serial
        tran_name = get_config_value(get_logger(), config, section, 'Name',
                                     'Unknown transducer name')
        names.append(tran_name)

    return names


def get_tran_list():
    """
    Returns a list of available transducer objects.

    Returns:
        List[Obj]: Objects of available transducers.
    """

    tran_list = []
    for serial in get_tran_serials():
        tran = Transducer()
        tran.set_transducer_info(serial)
        tran_list.append(tran)

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

    return None
