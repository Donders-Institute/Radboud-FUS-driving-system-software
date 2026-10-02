# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it, see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

from setuptools import setup, find_packages

setup(name='fus_ds_gui',
      version='0.1.0',
      description='Radboud FUS Driving System GUI: a PySide6 GUI for building, loading, and '
                  'running fus_driving_systems protocols',
      url='https://github.com/Donders-Institute/Radboud-FUS-driving-system-software',
      author='Margely Cornelissen',
      author_email='margely.cornelissen@ru.nl',
      packages=find_packages(),
      package_data={'fus_ds_gui': ['resources/*.png']},
      install_requires=['PySide6'],
      zip_safe=False)
