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
import os

# Miscellaneous packages
import configparser
from importlib import resources as impresources

# Own packages
from fus_driving_systems import config
from fus_driving_systems.utils import get_config_file


# Initialize ConfigParser
config_info = configparser.ConfigParser(interpolation=None)


def read_config(file_path):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Configuration file '{abs_path}' not found.")
    config_info.read(abs_path)


def read_additional_config(file_path):
    additional_config = configparser.ConfigParser(interpolation=None)
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Configuration file '{abs_path}' not found.")
    additional_config.read(abs_path)
    config_info.update(additional_config)


def sync_config(new_config):
    """
    Merges an externally provided (e.g. host application's) config into our shared config_info,
    in place.

    Mutates the existing ConfigParser object in place instead of rebinding this module's
    'config_info' name to a different object: every module that already did
    'from fus_driving_systems.config.config import config_info as config' at its own import
    time holds a reference to that same object, so an in-place merge reaches them regardless of
    import order -- a plain rebind here would not (they would keep pointing at the old object).
    Uses the same ConfigParser.update() merge already used by read_additional_config() (a
    section present in new_config replaces that whole section here; sections absent from
    new_config are left untouched).

    Parameters:
        new_config (configparser.ConfigParser): The externally provided config to merge in.
    """

    config_info.update(new_config)


# Automatically read the main configuration file when the module is imported
inp_file = (impresources.files(config) / get_config_file())
read_config(inp_file)
