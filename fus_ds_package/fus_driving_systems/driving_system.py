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
import sys

# Miscellaneous packages

# Own packages
from fus_driving_systems.config.config import config_info as config


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
        self.is_active = True

    def set_ds_info(self, serial):
        """
        Sets the driving system based on the provided serial number.

        Parameters:
            serial (str): Serial number of the driving system.
        """

        try:
            self.serial = serial
            self.name = config['Equipment.Driving system.' + serial]['Name']
            self.connect_info = config['Equipment.Driving system.' + serial]['Connection info']
            self.manufact = config['Equipment.Driving system.' + serial]['Manufacturer']
            self.available_ch = int(config['Equipment.Driving system.' + serial]
                                          ['Available channels'])
            self.connect_info = config['Equipment.Driving system.' + serial]['Connection info']
            self.tran_comp = (config['Equipment.Driving system.' + serial]
                                    ['Transducer compatibility'].split(', '))
            self.is_active = config['Equipment.Driving system.' + serial]['Active?'] == 'True'

        except KeyError:
            sys.exit(f'No driving system with serial number {serial} found in configuration file.')

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
        tran_comp = '\n '.join(self.tran_comp)
        info += f"Driving system tranducer compatibility: {tran_comp} \n "

        return info


def get_ds_serials():
    """
    Returns a list of serial numbers for available driving systems.

    Returns:
        List[str]: Serial numbers for available driving systems.
    """

    serial_ds = config['Equipment']['Driving systems'].split(', ')

    active_serials = []
    for serial in serial_ds:
        # only extract active driving systems
        if config['Equipment.Driving system.' + serial]['Active?'] == 'True':
            active_serials.append(serial)

    return active_serials


def get_ds_names():
    """
    Returns a list of names of available driving systems.

    Returns:
        List[str]: Names of available driving systems.
    """

    names = []
    for serial in get_ds_serials():
        try:
            ds_name = config['Equipment.Driving system.' + serial]['Name']
        except KeyError:
            sys.exit(f'No driving system with serial number {serial} found in' +
                     ' configuration file.')
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
        try:
            ds = DrivingSystem()
            ds.set_ds_info(serial)
        except KeyError:
            sys.exit(f'No driving system with serial number {serial} found in' +
                     ' configuration file.')
        ds_list.append(ds)

    if len(ds_list) < 1:
        sys.exit('No driving systems found in configuration file.')

    return ds_list
