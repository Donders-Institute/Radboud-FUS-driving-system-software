# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

from setuptools import setup, find_packages

setup(name='fus_driving_systems',
      version='2.2.3',
      description='Abstract structure to communicate with different FUS driving systems',
      url='https://github.com/Donders-Institute/Radboud-FUS-driving-system-software',
      author='Margely Cornelissen',
      author_email='margely.cornelissen@ru.nl',
      packages=find_packages(),
      package_data={'fus_driving_systems': ['config/*', 'igt/config/imasonic_transducers/*',
                                            'igt/config/sonic_concepts_transducers/*',
                                            'igt/config/conversion_data/*',
                                            'igt/config/*.json', 'igt/*.pyd']},
      py_modules=['driving_system', 'transducer', 'control_driving_system', 'tus_protocol',
                  'utils'],
      zip_safe=False)
