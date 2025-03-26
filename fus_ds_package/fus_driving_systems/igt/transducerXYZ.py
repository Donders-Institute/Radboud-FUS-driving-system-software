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

# -------------------------------------------------------------------------------
# Name:        transducerXYZ
# Purpose:
#
# Author:      Frederic Salabartan
#
# Created:
# Copyright:   (c) Image Guided Therapy

# -------------------------------------------------------------------------------

# Access the logger
from fus_driving_systems.config.logging_config import logger
import sys
import math
try:  # for Python 2/3 compatibility
    from StringIO import StringIO
except ImportError:
    from io import StringIO
try:  # for Python 2/3 compatibility
    import ConfigParser as cfg
except ImportError:
    import configparser as cfg


SOUND_SPEED_WATER = 1500.0  # sound speed in water, m.s-1
TWO_PI = 2.0 * math.pi      # 2 pi, rad


class Transducer(object):
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
        # self.focalLength = 0
        self.elements = []

    def load(self, filename):
        # config = cfg.ConfigParser()
        # this easy version can not be used because of the checksum trick
        # that raises a ConfigParser.MissingSectionHeaderError
        # if config.read (filename) == []:
        #    return False
        # return self._loadConfig (config)
        text = ""
        outside = True
        try:
            with open(filename, "r") as f:
                for line in f:
                    if line.strip() == "":
                        continue
                    if outside:
                        if line.strip()[0] == "[":
                            text += line
                            outside = False
                        continue
                    text += line
            return self.loadFromString(text)
        except IOError as e:
            print("Error: "+str(e))
            return False

    def loadFromString(self, definition):
        config = cfg.ConfigParser()
        stringio = StringIO(definition)
        if config.readfp(stringio) == []:
            print("Error: empty content")
            return False
        return self._loadConfig(config)

    def _loadConfig(self, config):
        size = 0
        # self.name = ""
        try:
            # self.name = config.get ("transducer", "name")
            # self.focalLength = config.getfloat ("transducer", "focalLength") / 1000.0
            size = config.getint("elements", "size")
        except:
            print("Error: missing 'elements.size' parameter")
            return False
        if size == 0:
            print("Error: size is 0")
            return False

        self.elements = []
        for i in range(1, 1+size):
            try:
                elem = config.get("elements", "%d" % i).strip()
                coords = elem.split("|")
                # read coordinates in mm (convert them in m)
                item = (float(coords[0])/1000.0, float(coords[1])/1000.0, float(coords[2])/1000.0)
                self.elements.append(item)
            except Exception as ex:
                print("Error: "+str(ex))
                return False

        return True

    def channelCount(self):
        """Returns the number of channels / elements."""
        return len(self.elements)

    def computePhases(self, pulse, point_mm, set_focus_mm, dephasing_degree):
        """
        Computes the phases necessary to aim at the specified point, and writes them directly in the
        given pulse.
            :param pulse: the pulse to modify, its frequencies must be set before, its phases are
            modified (and resized)
            :param point_mm: a 3-tuple (x,y,z) = cartesian coordinates (in mm) of the target, in the
            transducer space
            :set_focus_mm (float): The chosen focal depth [mm] without respect to natural focus.
            :dephasing_degree (list(float)): The degree used to dephase n elements in one cycle.
            None = no dephasing. If the list is equal to the number of elements, the phases based on
            the focus are overridden.
        """

        freqCount = pulse.frequencyCount()
        if freqCount == 0 or pulse.frequency(0) == 0:
            print("Error: the frequencies must be defined in the pulse before calling" +
                  "computePhases().")
            return False
        if freqCount == 1:
            wavelen = SOUND_SPEED_WATER / pulse.frequency(0)
        elif freqCount != self.channelCount():
            print("Error: bad number of frequencies (%d in pulse, %d elements in transducer)"
                  % (freqCount, self.channelCount()))
            return False

        phases = [0.0] * self.channelCount()
        x = point_mm[0] / 1000.0
        y = point_mm[1] / 1000.0
        z = point_mm[2] / 1000.0

        for i in range(self.channelCount()):
            elem = self.elements[i]
            if freqCount > 1:
                wavelen = SOUND_SPEED_WATER / pulse.frequency(i)
            dist = math.sqrt(math.pow(elem[0]-x, 2) + math.pow(elem[1]-y, 2) +
                             math.pow(elem[2]-z, 2))
            rem = math.modf(dist / wavelen)[0]  # take fractional part
            phases[i] = rem * 360.0

        if dephasing_degree is not None:
            if len(dephasing_degree) > 1:
                logger.error('Too few or too many entries given at dephasing_degree.' +
                             ' Only the first one is now used for dephasing purposes.')
                sys.exit()

            dephasing_degree = dephasing_degree[0]

            # determine n elements to dephase in one cycle
            nth_elem = round(360/dephasing_degree)
            dephasing_elem = 0
            for i in range(len(phases)):
                # Add chosen degrees to dephase signal
                phases[i] = phases[i] + dephasing_degree*dephasing_elem

                dephasing_elem = dephasing_elem + 1
                if dephasing_elem == nth_elem:
                    dephasing_elem = 0

        phases_str = ', '.join([format(x, '.2f') for x in phases])
        natural_foc = set_focus_mm + point_mm[2]
        logger.info(f'Computed phases for focus wrt mid bowl of {set_focus_mm} and aim w.r.t. ' +
                    f'natural focus of {natural_foc}: {phases_str}')

        return phases
