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

            return False

    def load_from_string(self, definition):
        if not definition.strip():
            message = 'Error: empty content'
            get_logger().critical(message)
            sys.exit(message)

        config = cfg.ConfigParser()
        stringio = StringIO(definition)
        config.read_file(stringio)
        return self._load_config(config)

    def _load_config(self, config):
        # Required, not merely defaulted to 0 -- a missing/invalid focalLength would silently
        # feed a wrong value into compute_phases()'s aim_wrt_natural_focus arithmetic, producing
        # a plausible-looking but incorrect target focus rather than a loud failure. No
        # /1000.0 here (unlike the element coordinates below) -- focalLength stays in mm.
        try:
            self.focalLength = config.getfloat("transducer", "focalLength")
        except (cfg.Error, ValueError):
            message = "Error: missing or invalid 'transducer.focalLength' parameter"
            get_logger().critical(message)
            sys.exit(message)

            return False

        size = 0
        # self.name = ""
        try:
            # self.name = config.get ("transducer", "name")
            size = config.getint("elements", "size")
        except (cfg.Error, ValueError):
            message = "Error: missing 'elements.size' parameter"
            get_logger().critical(message)
            sys.exit(message)

            return False
        if size == 0:
            message = "Error: size is 0"
            get_logger().critical(message)
            sys.exit(message)

            return False

        self.elements = []
        for i in range(1, 1+size):
            try:
                elem = config.get("elements", f"{i}").strip()
                coords = elem.split("|")
                # read coordinates in mm (convert them in m)
                item = (float(coords[0])/1000.0, float(coords[1])/1000.0, float(coords[2])/1000.0)
                self.elements.append(item)
            except Exception as ex:
                message = f"Error: {ex}"
                get_logger().critical(message)
                sys.exit(message)

                return False

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

            return False
        if freq_count == 1:
            wavelen = SOUND_SPEED_WATER / pulse.frequency(0)
        elif freq_count != self.channel_count():
            message = (f"Error: bad number of frequencies ({freq_count} in pulse, " +
                       f"{self.channel_count()} elements in transducer)")
            get_logger().critical(message)
            sys.exit(message)

            return False

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
            if len(dephasing_degree) > 1:
                message = (f'Number of dephasing entries ({len(dephasing_degree)}) does not ' +
                           'correspond to number of transducer elements ' +
                           f'({self.channel_count()}). Only enter one dephasing value or ' +
                           'n-values equal to the number of transducer elements.')
                get_logger().critical(message)
                sys.exit(message)

            dephasing_degree = dephasing_degree[0]

            # determine n elements to dephase in one cycle
            nth_elem = round(360/dephasing_degree)
            dephasing_elem = 0
            for i, phase in enumerate(phases):
                # Add chosen degrees to dephase signal
                phases[i] = phase + dephasing_degree*dephasing_elem

                dephasing_elem = dephasing_elem + 1
                if dephasing_elem == nth_elem:
                    dephasing_elem = 0

        phases_str = ', '.join([format(x, '.2f') for x in phases])
        natural_foc = set_focus_mm + point_mm[2]
        get_logger().debug(
            f'Computed phases for focus wrt mid bowl of {set_focus_mm} and aim w.r.t. ' +
            f'natural focus of {natural_foc}: {phases_str}')

        return phases
