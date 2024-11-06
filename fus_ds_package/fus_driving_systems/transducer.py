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
        self.min_foc = 0  # [mm]
        self.max_foc = 200  # [mm]
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
            self.name = config['Equipment.Transducer.' + serial]['Name']
            self.manufact = config['Equipment.Transducer.' + serial]['Manufacturer']
            self.elements = int(config['Equipment.Transducer.' + serial]['Elements'])
            self.fund_freq = int(config['Equipment.Transducer.' + serial]['Fund. freq.'])
            self.natural_foc = float(config['Equipment.Transducer.' + serial]['Natural focus'])
            self.exit_plane_dist = float(config['Equipment.Transducer.' + serial]
                                         ['Exit plane - first element dist.'])
            self.min_foc = float(config['Equipment.Transducer.' + serial]['Min. focus'])
            self.max_foc = float(config['Equipment.Transducer.' + serial]['Max. focus'])
            self.steer_info = config['Equipment.Transducer.' + serial]['Steer information']
            self.is_active = config['Equipment.Transducer.' + serial]['Active?'] == 'True'

        except KeyError:
            sys.exit(f'No transducer with serial number {serial} found in configuration file.')

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

    serial_trans = config['Equipment']['Transducers'].split('\n')

    active_serials = []
    for serial in serial_trans:
        # only extract active tranducers
        if config['Equipment.Transducer.' + serial]['Active?'] == 'True':
            active_serials.append(serial)

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
            tran_name = config['Equipment.Transducer.' + serial]['Name']
        except KeyError:
            sys.exit(f'No transducer with serial number {serial} found in' +
                     ' configuration file.')
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
        try:
            tran = Transducer()
            tran.set_transducer_info(serial)
        except KeyError:
            sys.exit(f'No transducer with serial number {serial} found in' +
                     ' configuration file.')
        tran_list.append(tran)

    if len(tran_list) < 1:
        sys.exit('No transducers found in configuration file.')

    return tran_list
