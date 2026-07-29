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
      py_modules=['driving_system', 'transducer', 'control_driving_system', 'sequence', 'utils'],
      zip_safe=False)
