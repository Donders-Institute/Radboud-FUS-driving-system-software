# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University and Image Guided Therapy

SPDX-License-Identifier: MIT
See the LICENSE file for full license text, and THIRD_PARTY_NOTICES.md for which files in this
package originate from Image Guided Therapy. This file was originally written by Image
Guided Therapy and has since been modified by Radboud University.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# -------------------------------------------------------------------------------
# Name:        transducer_xyz
# Purpose:
#
# Author:      Frederic Salabartan
#
# Created:
# Copyright:   (c) Image Guided Therapy

# -------------------------------------------------------------------------------

import sys
import math

# Access the logger
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.utils import get_config_value
from fus_driving_systems.config.logging_config import get_logger

try:  # for Python 2/3 compatibility
    from StringIO import StringIO
except ImportError:
    from io import StringIO
try:  # for Python 2/3 compatibility
    import ConfigParser as cfg
except ImportError:
    import configparser as cfg


SOUND_SPEED_WATER = float(get_config_value(get_logger(), config, 'General',
                                           'Speed of sound water [m/s]',
                                           1500.0))  # sound speed in water, m.s-1
TWO_PI = 2.0 * math.pi      # 2 pi, rad


def apply_cyclic_dephasing(phases, dephasing_degree):
    """
    Applies a cyclic dephasing step to a list of phases -- shared by Transducer.compute_phases()
    (below) and IGT._set_phases()'s .xlsx branch (igt_ds.py), which used to each carry their own,
    independent copy of this exact loop (flagged by pylint's duplicate-code check). The two
    copies had quietly drifted apart on invalid input: this version's sys.exit() on more than one
    entry is the one that was already correct -- more than one dephasing value that doesn't match
    the element count exactly (that case is handled by the caller directly, as a full phase
    override, before ever reaching here) is invalid input, not something to silently paper over
    by using the first value and warning.

    Parameters:
        phases (list(float)): Phases [degrees] to dephase, one per element.
        dephasing_degree (list(float)): Must contain exactly one entry -- the degree step used
            to dephase n elements in one cycle.

    Returns:
        list(float): A new list with the dephasing step applied.
    """

    if len(dephasing_degree) > 1:
        message = (f'Number of dephasing entries ({len(dephasing_degree)}) does not ' +
                   f'correspond to number of transducer elements ({len(phases)}). Only enter ' +
                   'one dephasing value or n-values equal to the number of transducer elements.')
        get_logger().critical(message)
        sys.exit(message)

    dephasing_degree = dephasing_degree[0]
    dephased = list(phases)

    # determine n elements to dephase in one cycle
    nth_elem = round(360 / dephasing_degree)
    dephasing_elem = 0
    for i, phase in enumerate(dephased):
        # Add chosen degrees to dephase signal
        dephased[i] = phase + dephasing_degree * dephasing_elem

        dephasing_elem = dephasing_elem + 1
        if dephasing_elem == nth_elem:
            dephasing_elem = 0

    return dephased


class Transducer:
    """
    A representation of the device used to shoot.
    It must be initialized from a definition file that contains basically the positions
    of its elements.
    Its working space is:
    - origin (0,0,0) at the natural focal point (all phases = 0)
    - Z axis toward the transducer
    """

    def __init__(self):
        # self.name = ""
        # Kept in mm (unlike self.elements' coordinates below, which are stored in meters) --
        # this crosses the class's own public boundary the same way point_mm/set_focus_mm do,
        # so callers (igt_ds.py) can use it directly alongside those, in the same unit.
        self.focalLength = 0
        self.elements = []

    def load(self, filename):
        # config = cfg.ConfigParser()
        # this easy version can not be used because of the checksum trick
        # that raises a ConfigParser.MissingSectionHeaderError
        # if config.read (filename) == []:
        #    return False
        # return self._load_config (config)
        text = ""
        outside = True
        try:
            with open(filename, "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip() == "":
                        continue
                    if outside:
                        if line.strip()[0] == "[":
                            text += line
                            outside = False
                        continue
                    text += line
            return self.load_from_string(text)
        except IOError as e:
            message = f'Error: {e}'
            get_logger().critical(message)
            sys.exit(message)

    def load_from_string(self, definition):
        if not definition.strip():
            message = 'Error: empty content'
            get_logger().critical(message)
            sys.exit(message)

        # Named parser, not config -- that name is already taken at module level by the shared
        # config_info object (see SOUND_SPEED_WATER above), which this ConfigParser instance
        # (for the transducer's own .ini steer file, an unrelated file) has nothing to do with.
        parser = cfg.ConfigParser()
        stringio = StringIO(definition)
        parser.read_file(stringio)
        return self._load_config(parser)

    def _load_config(self, parser):
        # Required, not merely defaulted to 0 -- a missing/invalid focalLength would silently
        # feed a wrong value into compute_phases()'s aim_wrt_natural_focus arithmetic, producing
        # a plausible-looking but incorrect target focus rather than a loud failure. No
        # /1000.0 here (unlike the element coordinates below) -- focalLength stays in mm.
        try:
            self.focalLength = parser.getfloat("transducer", "focalLength")
        except (cfg.Error, ValueError):
            message = "Error: missing or invalid 'transducer.focalLength' parameter"
            get_logger().critical(message)
            sys.exit(message)

        size = 0
        # self.name = ""
        try:
            # self.name = parser.get ("transducer", "name")
            size = parser.getint("elements", "size")
        except (cfg.Error, ValueError):
            message = "Error: missing 'elements.size' parameter"
            get_logger().critical(message)
            sys.exit(message)
        if size == 0:
            message = "Error: size is 0"
            get_logger().critical(message)
            sys.exit(message)

        self.elements = []
        for i in range(1, 1+size):
            try:
                elem = parser.get("elements", f"{i}").strip()
                coords = elem.split("|")
                # read coordinates in mm (convert them in m)
                item = (float(coords[0])/1000.0, float(coords[1])/1000.0, float(coords[2])/1000.0)
                self.elements.append(item)
            except Exception as ex:
                message = f"Error: {ex}"
                get_logger().critical(message)
                sys.exit(message)

        return True

    def channel_count(self):
        """Returns the number of channels / elements."""
        return len(self.elements)

    def compute_phases(self, pulse, point_mm, set_focus_mm, dephasing_degree):
        """
        Computes the phases necessary to aim at the specified point, and writes them directly in
        the given pulse.
            :param pulse: the pulse to modify, its frequencies must be set before, its phases are
            modified (and resized)
            :param point_mm: a 3-tuple (x,y,z) = cartesian coordinates (in mm) of the target, in
            the transducer space
            :set_focus_mm (float): The chosen focal depth [mm] without respect to natural focus.
            :dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases
            based on the focus are overridden.
        """

        freq_count = pulse.frequencyCount()
        if freq_count == 0 or pulse.frequency(0) == 0:
            message = ("Error: the frequencies must be defined in the pulse before calling" +
                       "compute_phases().")
            get_logger().critical(message)
            sys.exit(message)
        if freq_count == 1:
            wavelen = SOUND_SPEED_WATER / pulse.frequency(0)
        elif freq_count != self.channel_count():
            message = (f"Error: bad number of frequencies ({freq_count} in pulse, " +
                       f"{self.channel_count()} elements in transducer)")
            get_logger().critical(message)
            sys.exit(message)

        phases = [0.0] * self.channel_count()
        x = point_mm[0] / 1000.0
        y = point_mm[1] / 1000.0
        z = point_mm[2] / 1000.0

        for i in range(self.channel_count()):
            elem = self.elements[i]
            if freq_count > 1:
                wavelen = SOUND_SPEED_WATER / pulse.frequency(i)
            dist = math.sqrt(math.pow(elem[0]-x, 2) + math.pow(elem[1]-y, 2) +
                             math.pow(elem[2]-z, 2))
            rem = math.modf(dist / wavelen)[0]  # take fractional part
            phases[i] = rem * 360.0

        if dephasing_degree is not None:
            phases = apply_cyclic_dephasing(phases, dephasing_degree)

        phases_str = ', '.join([format(x, '.2f') for x in phases])
        natural_foc = set_focus_mm + point_mm[2]
        get_logger().debug(
            f'Computed phases for focus wrt mid bowl of {set_focus_mm:.2f} and aim w.r.t. ' +
            f'natural focus of {natural_foc:.2f}: {phases_str}')

        return phases
