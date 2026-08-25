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


class DrivingSystem:
    """
    Class representing ultrasound driving system information.

    Attributes:
        serial (str): Serial number of the driving system.
        name (str): Name of the driving system.
        manufact (str): Name of the manufacturer.
        available_ch (int): Number of available channels with chosen configuration.
        connect_info (str): Connection information for the driving system, either COM port (SC) or
        config. file (IGT).
        tran_comp (List[str]): List of transducers the driving system is compatible with.
        power_options (List[str]): List of power options compatible with the driving system.
        focus_options (List[str]): List of focus options compatible with the driving system.
        native_power_params (List[str]): The power parameter(s) this driving system's hardware
            accepts directly, without needing a calibration curve to convert them (e.g.
            amplitude for IGT). Usually a single entry, but a driving system whose hardware
            genuinely accepts more than one power representation directly can list several.
        native_focus_params (List[str]): Same idea as native_power_params, for focus.
        max_tran_slots (int): The number of transducers this driving system can drive
            simultaneously (see TUSProtocol.add_slot()). Default 1 -- a driving system that
            doesn't declare a higher value is single-transducer-only.
        max_buffers (int): The number of hardware buffers this driving system can hold a
            protocol in at once (see TUSProtocol.buffer_num) -- each buffer can be pre-loaded
            with its own protocol ahead of time and triggered/executed independently. Default 1 --
            a driving system that doesn't declare a higher value has no real buffer concept at
            all (buffer_num is then only ever 0).
        is_active (Boolean): Indication if the driving system is used with the code.
    """

    def __init__(self):
        """
        Initializes a DrivingSystem object with default values.

        """

        self.serial = None
        self.name = None
        self.manufact = None
        self.available_ch = 0
        self.connect_info = None
        self.tran_comp = None
        self.power_options = None
        self.focus_options = None
        self.native_power_params = None
        self.native_focus_params = None
        self.max_tran_slots = 1
        self.max_buffers = 1
        self.is_active = True

    def set_ds_info(self, serial):
        """
        Sets the driving system based on the provided serial number.

        Called by TUSProtocol.driving_sys's setter and get_ds_list() -- both can be given a
        serial that isn't actually in the configuration file (e.g. a typo). That is checked
        explicitly below, rather than relying on incidentally hitting one of the individual
        is_sys_exit=True fields further down and having to track down why that one field
        failed.

        Parameters:
            serial (str): Serial number of the driving system.
        """

        section = 'Equipment.Driving system.' + serial
        if section not in config:
            message = (f'No driving system with serial number {serial} found in ' +
                       'configuration file.')
            get_logger().critical(message)
            sys.exit(message)

        self.serial = serial
        self.name = get_config_value(get_logger(), config, section, 'Name',
                                     'Unknown driving system name')
        self.manufact = get_config_value(get_logger(), config, section, 'Manufacturer',
                                         'Unknown driving system manufacturer')
        self.available_ch = int(get_config_value(get_logger(), config, section,
                                                 'Available channels', 0))
        self.connect_info = get_config_value(get_logger(), config, section, 'Connection info',
                                             None, True)
        self.tran_comp = get_config_value(
            get_logger(), config, section, 'Transducer compatibility', '').split('\n')
        self.power_options = get_config_value(get_logger(), config, section, 'Power options',
                                              '').split('\n')
        self.focus_options = get_config_value(get_logger(), config, section, 'Focus options',
                                              '').split('\n')
        self.native_power_params = get_config_value(
            get_logger(), config, section, 'Native power parameters', '', True).split('\n')
        self.native_focus_params = get_config_value(
            get_logger(), config, section, 'Native focus parameters', '', True).split('\n')
        self.max_tran_slots = int(get_config_value(
            get_logger(), config, section, 'Max. transducer slots', 1))
        self.max_buffers = int(get_config_value(
            get_logger(), config, section, 'Max. buffers', 1))
        self.is_active = get_config_value(
            get_logger(), config, section, 'Active?', 'True') == 'True'

    def __str__(self):
        """
        Returns a formatted string containing information about the driving system.

        Returns:
            str: Formatted information about the driving system.
        """

        info = ''
        info += f"Driving system serial number: {self.serial} \n "
        info += f"Driving system name: {self.name} \n "
        info += f"Driving system manufacturer: {self.manufact} \n "
        info += f"Driving system available channels: {self.available_ch} \n "
        info += f"Driving system connection info: {self.connect_info} \n "

        tran_comp = ', '.join(self.tran_comp)
        info += f"Driving system tranducer compatibility: {tran_comp} \n "

        power_options = ', '.join(self.power_options)
        info += f"Driving system power options: {power_options} \n "
        focus_options = ', '.join(self.focus_options)
        info += f"Driving system focus options: {focus_options} \n "
        native_power_params = ', '.join(self.native_power_params)
        info += f"Driving system native power parameter(s): {native_power_params} \n "
        native_focus_params = ', '.join(self.native_focus_params)
        info += f"Driving system native focus parameter(s): {native_focus_params} \n "
        info += f"Driving system max. transducer slots: {self.max_tran_slots} \n "
        info += f"Driving system max. buffers: {self.max_buffers} \n "

        return info

    def clone(self):
        """
        Creates and returns a new instance of the DrivingSystem class with the same attribute
        values.

        The new instance is a deep copy of the current instance, ensuring that changes to the
        cloned object do not affect the original object.

        Returns:
            CharacSequence: A new instance of the DrivingSystem class with copied attribute values.
        """

        new_instance = DrivingSystem()
        new_instance.__dict__ = copy.deepcopy(self.__dict__)  # Copy all attributes
        return new_instance


def get_ds_serials():
    """
    Returns a list of serial numbers for available driving systems.

    Returns:
        List[str]: Serial numbers for available driving systems.
    """

    serial_ds = get_config_value(get_logger(), config, 'Equipment', 'Driving systems', '',
                                 True).split('\n')

    active_serials = []
    for serial in serial_ds:
        # only extract active driving systems
        section = 'Equipment.Driving system.' + serial
        if get_config_value(get_logger(), config, section, 'Active?', 'True') == 'True':
            active_serials.append(serial)

    if len(active_serials) < 1:
        message = 'No active driving systems found in configuration file.'
        get_logger().critical(message)
        sys.exit(message)

    return active_serials


def get_ds_names():
    """
    Returns a list of names of available driving systems.

    Returns:
        List[str]: Names of available driving systems.
    """

    names = []
    for serial in get_ds_serials():
        section = 'Equipment.Driving system.' + serial
        ds_name = get_config_value(get_logger(), config, section,
                                   'Name', 'Unknown driving system name')
        names.append(ds_name)

    return names


def get_ds_list():
    """
    Returns a list of available driving system objects.

    Returns:
        List[Obj]: Objects of available driving systems.
    """

    ds_list = []
    for serial in get_ds_serials():
        ds = DrivingSystem()
        ds.set_ds_info(serial)
        ds_list.append(ds)

    return ds_list


def get_serial_from_name(name):
    """
    Returns the serial number matching the given name.

    Args:
        name (str): The name of the device.

    Returns:
        str: The serial number, or None if no match is found.
    """

    for ds in get_ds_list():
        if ds.name == name:
            return ds.serial

    return None
