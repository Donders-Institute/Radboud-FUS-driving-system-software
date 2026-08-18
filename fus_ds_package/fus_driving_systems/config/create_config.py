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

import configparser
import importlib.resources
import os
import re

from fus_driving_systems import utils


def _combo_files_exist(*rel_paths):
    """
    True only if every given calibration file actually exists on disk. Paths are resolved
    relative to the fus_driving_systems package, matching how calc_utils.py's
    extract_and_define_pp() resolves the very same config values at runtime.

    Parameters:
        rel_paths (str): Config-relative paths to calibration JSON files (e.g. the value of an
        'Equipment.Combination.*' section's 'EqualizationCurveFit json file' key).

    Returns:
        bool: True if every path exists, False if any is missing.
    """

    package_root = importlib.resources.files('fus_driving_systems')
    return all(os.path.isfile(str(package_root.joinpath(rel_path))) for rel_path in rel_paths)


def _add_driving_system(serial, name, manufacturer, available_channels, connection_info,
                        transducer_compatibility, power_options, native_power_parameters,
                        focus_options, native_focus_parameters, max_transducer_slots=1,
                        max_buffers=1, active=True):
    """
    Builds one '[Equipment.Driving system.<serial>]' section from keyword arguments -- replaces
    what used to be 10-13 individually hand-typed 'config[section][key] = value' lines per
    driving system (the actual source of create_config.py's repetition/typo problem: sharing
    string constants like IGT_DS[i] never eliminated the per-device block itself).

    Parameters:
        serial (str): Driving system serial -- used as-is for the section name.
        name (str): Descriptive name.
        manufacturer (str): Must match one of the Equipment.Manufacturer.* names.
        available_channels (int): Number of channels this driving system provides.
        connection_info (str): COM port, IP address, or path to a config file.
        transducer_compatibility (list(str)): Compatible transducer serials.
        power_options (list(str)): Power options this driving system supports at all.
        native_power_parameters (str): Which power option(s) this hardware accepts directly.
        focus_options (list(str)): Focus options this driving system supports at all.
        native_focus_parameters (str): Which focus option(s) this hardware accepts directly.
        max_transducer_slots (int): How many transducers this driving system can drive at once.
        max_buffers (int): How many hardware buffers this driving system can hold a protocol in.
        active (bool): Whether this driving system is active and available for use.
    """

    section = 'Equipment.Driving system.' + serial
    config[section] = {}
    config[section]['Name'] = name
    config[section]['Manufacturer'] = manufacturer
    config[section]['Available channels'] = str(available_channels)
    config[section]['Connection info'] = connection_info
    config[section]['Transducer compatibility'] = '\n'.join(transducer_compatibility)
    config[section]['Power options'] = '\n'.join(power_options)
    config[section]['Native power parameters'] = native_power_parameters
    config[section]['Focus options'] = '\n'.join(focus_options)
    config[section]['Native focus parameters'] = native_focus_parameters
    config[section]['Max. transducer slots'] = str(max_transducer_slots)
    config[section]['Max. buffers'] = str(max_buffers)
    config[section]['Active?'] = str(active)


def _add_transducer(serial, name, manufacturer, elements, fund_freq, min_focus, max_focus,
                    natural_focus=0, exit_plane_dist=0, steer_information='', active=True):
    """
    Builds one '[Equipment.Transducer.<serial>]' section from keyword arguments.

    Parameters:
        serial (str): Transducer serial -- used as-is for the section name.
        name (str): Descriptive name.
        manufacturer (str): Must match one of the Equipment.Manufacturer.* names.
        elements (int): Number of elements.
        fund_freq (float): Fundamental frequency [kHz].
        min_focus (float): Minimum allowed focus wrt exit plane [mm].
        max_focus (float): Maximum allowed focus wrt exit plane [mm].
        natural_focus (float): Radius of curvature [mm] -- only meaningful for Imasonic.
        exit_plane_dist (float): Distance between radiating surface and exit plane [mm] -- only
            meaningful for Imasonic.
        steer_information (str): Path to steering information file, if applicable.
        active (bool): Whether this transducer is active and available for use.
    """

    section = 'Equipment.Transducer.' + serial
    config[section] = {}
    config[section]['Name'] = name
    config[section]['Manufacturer'] = manufacturer
    config[section]['Elements'] = str(elements)
    config[section]['Fund. freq.'] = str(fund_freq)
    config[section]['Natural focus'] = str(natural_focus)
    config[section]['Exit plane - first element dist.'] = str(exit_plane_dist)
    config[section]['Min. focus'] = str(min_focus)
    config[section]['Max. focus'] = str(max_focus)
    config[section]['Steer information'] = steer_information
    config[section]['Active?'] = str(active)


def _add_combination(ds_serial, tran_serial, eq_curve_filename, focus_curve_filename,
                     power_curve_filename, volt_curve_filename):
    """
    Builds one '[Equipment.Combination.<ds_serial>~<tran_serial>]' section -- the calibration
    curves needed to convert a non-native power/focus parameter for this specific
    driving-system/transducer pair. 'Active?' is derived automatically from whether all four
    referenced calibration files actually exist on disk (see _combo_files_exist()).

    Parameters:
        ds_serial (str): Driving system serial.
        tran_serial (str): Transducer serial.
        eq_curve_filename (str): Bare filename of the equalization curve-fit JSON file.
        focus_curve_filename (str): Bare filename of the focus curve-fit JSON file.
        power_curve_filename (str): Bare filename of the power curve-fit JSON file.
        volt_curve_filename (str): Bare filename of the voltage curve-fit JSON file.
    """

    section = 'Equipment.Combination.' + ds_serial + COMBO_JOIN_SIGN + tran_serial
    config[section] = {}
    config[section]['Driving system serial'] = ds_serial
    config[section]['Transducer serial'] = tran_serial
    config[section]['EqualizationCurveFit json file'] = str(
        os.path.join(CONFIG_FILE_FOLDER_CONVERSION_DATA, eq_curve_filename))
    config[section]['FocusCurveFit json file'] = str(
        os.path.join(CONFIG_FILE_FOLDER_CONVERSION_DATA, focus_curve_filename))
    config[section]['PowerCurveFit json file'] = str(
        os.path.join(CONFIG_FILE_FOLDER_CONVERSION_DATA, power_curve_filename))
    config[section]['VoltageCurveFit json file'] = str(
        os.path.join(CONFIG_FILE_FOLDER_CONVERSION_DATA, volt_curve_filename))
    config[section]['Active?'] = str(_combo_files_exist(
        config[section]['EqualizationCurveFit json file'],
        config[section]['FocusCurveFit json file'],
        config[section]['PowerCurveFit json file'],
        config[section]['VoltageCurveFit json file']))


CONFIG_FOLDER = utils.get_config_folder()  # should be in the same directory as code
CONFIG_FILE = utils.get_config_file()

config = configparser.ConfigParser(interpolation=None)

config['General'] = {}

config['General']['Configuration file folder'] = CONFIG_FOLDER
config['General']['Delay before reconnecting [s]'] = str(2)
config['General']['Maximum reconnection attempts'] = str(5)
config['General']['Package name'] = 'fus_driving_systems'
config['General']['Speed of sound water [m/s]'] = str(1500)

# Logging
config['Logging'] = {}
config['Logging']['Logger name'] = 'driving_system'
config['Logging']['Temporary logging path'] = 'C:\\Temp'
config['Logging']['Filename faulthandler'] = 'faulthandler_output.log'
config['Logging']['Filename session pointer'] = '.last_session_log_dir'
config['Logging']['Filename kernel death counter'] = 'kernel_death_count.txt'

config['Logging']['Timestamp format'] = '%Y-%m-%d_%H-%M-%S'
config['Logging']['Log level console'] = 'INFO'
config['Logging']['Log level file'] = 'DEBUG'
config['Logging']['Initial part of log filename'] = 'log_'
config['Logging']['Max log file size [MB]'] = str(10)

# Trigger options
TRIG_NONE = 'None'
# One pulse train fires per external trigger received -- n_triggers says how many to expect.
TRIG_PULSE_TRAIN = 'TriggerOnePulseTrain'
# One trigger fires the entire, already fully-timed protocol at once (equivalent to executing it
# directly, just gated behind that one trigger).
TRIG_WHOLE_PROTOCOL = 'TriggerWholeProtocol'

config['Trigger'] = {}
config['Trigger']['Options'] = '\n'.join([TRIG_NONE, TRIG_PULSE_TRAIN, TRIG_WHOLE_PROTOCOL])
config['Trigger']['Default option'] = TRIG_NONE
config['Trigger']['Option.none'] = TRIG_NONE
config['Trigger']['Option.pulse_train'] = TRIG_PULSE_TRAIN
config['Trigger']['Option.whole_protocol'] = TRIG_WHOLE_PROTOCOL

config['Trigger']['Default n_triggers'] = str(0)

# Power options
POW_GP = 'Global power [mW]'
POW_AMPL = 'Amplitude [%]'
POW_PRESS = 'Max. pressure in free water [MPa]'
POW_VOLT = 'Voltage [V]'

config['Power'] = {}
config['Power']['Options'] = '\n'.join([POW_GP, POW_AMPL, POW_PRESS, POW_VOLT])
config['Power']['Option.glob_pow'] = POW_GP
config['Power']['Option.ampl'] = POW_AMPL
config['Power']['Option.press'] = POW_PRESS
config['Power']['Option.volt'] = POW_VOLT
# Which power options require TUSProtocol(engineering_mode=True) to set directly -- an
# institutional safety policy, not a hardware property, so it's configurable rather than
# hardcoded: a different institution using this package can list a different set here, or none.
config['Power']['Engineering-only options'] = '\n'.join([POW_AMPL, POW_VOLT])

# No Default.* keys here (global_power/press/volt/ampl/eq_factor/eq_press/input_press/
# calc_ampl) -- TransducerSlot.__init__ hardcodes those to None directly, since every one of
# them is always overwritten before it can ever be read (see the comment there).

MAX_ALLOWED_PRESSURE = 1.4  # MPa
MAX_PRESSURE_KEY = 'Maximum pressure allowed in free water [MPa]'
config['Power'][MAX_PRESSURE_KEY] = str(MAX_ALLOWED_PRESSURE)

# Focus options
FOC_WRT_EXIT = 'Focus wrt exit plane [mm]'
FOC_WRT_BOWL = 'Focus wrt mid bowl [mm]'

config['Focus'] = {}
config['Focus']['Options'] = '\n'.join([FOC_WRT_EXIT, FOC_WRT_BOWL])
config['Focus']['Default option'] = FOC_WRT_EXIT
config['Focus']['Option.exit'] = FOC_WRT_EXIT
config['Focus']['Option.bowl'] = FOC_WRT_BOWL
# See the identical rationale on config['Power']['Engineering-only options'] above.
config['Focus']['Engineering-only options'] = FOC_WRT_BOWL

# No Default.exit/Default.bowl keys here -- TransducerSlot.__init__ hardcodes
# _focus_wrt_exit_plane/_focus_wrt_mid_bowl to None directly. Default.bowl used to be read there,
# but the transducer setter always overwrites it right after construction, before it can ever be
# read (see the comment there); Default.exit was never actually read by anything at all.
config['Focus']['Default.minimum'] = str(15)  # [mm]
config['Focus']['Default.maximum'] = str(1000)  # [mm]

# Ramp options
RAMP_RECT = 'Rectangular - no ramping'
RAMP_LIN = 'Linear'
RAMP_TUK = 'Tukey'

config['Ramp'] = {}
config['Ramp']['Options'] = '\n'.join([RAMP_RECT, RAMP_LIN, RAMP_TUK])
config['Ramp']['Default option'] = RAMP_RECT
config['Ramp']['Option.rect'] = RAMP_RECT
config['Ramp']['Option.lin'] = RAMP_LIN
config['Ramp']['Option.tuk'] = RAMP_TUK

# Timing parameters
config['Timing'] = {}
config['Timing']['Pulse_dur_ms'] = str(0.25)  # [ms]
PULSE_REP_INT = 20
config['Timing']['Pulse_rep_int_ms'] = str(PULSE_REP_INT)  # [ms]
config['Timing']['Pulse_train_dur_ms'] = str(PULSE_REP_INT)  # [ms]
config['Timing']['Pulse_train_rep_int_ms'] = str(PULSE_REP_INT)  # [ms]
config['Timing']['Pulse_train_rep_dur'] = str(PULSE_REP_INT)  # [ms]

config['Timing']['Pulse_ramp_dur_ms'] = str(0)  # [ms]

# Equipment
config['Equipment'] = {}

#######################################################################################
# Sonic Concepts
#######################################################################################

SONIC_CONCEPTS = 'Sonic Concepts'
CONFIG_FILE_FOLDER_SC_TRAN = 'igt\\config\\sonic_concepts_transducers'
config['Equipment.Manufacturer.SC'] = {}
config['Equipment.Manufacturer.SC']['Name'] = SONIC_CONCEPTS
config['Equipment.Manufacturer.SC']['Config. file folder transducers'] = CONFIG_FILE_FOLDER_SC_TRAN

config['Equipment.Manufacturer.SC']['Additional charac. discon. message'] = ('\n - the correct ' +
                                                                             'TRANSDUCER is ' +
                                                                             'selected on the ' +
                                                                             'driving system.')
config['Equipment.Manufacturer.SC']['Check tran message'] = ('Ensure the correct TRANSDUCER is ' +
                                                             'selected on the driving system.')

SC_DS = ['203-035', '105-010']

config['Equipment.Manufacturer.SC']['Equipment - Driving systems'] = '\n'.join(SC_DS)

SC_TRAN_2CH = ['CTX-250-009', 'CTX-250-014', 'CTX-500-006']
SC_TRAN_4CH = ['CTX-250-001', 'CTX-250-026', 'CTX-500-024', 'CTX-500-026', 'DPX-500-022']

SC_TRANS = SC_TRAN_2CH + SC_TRAN_4CH

config['Equipment.Manufacturer.SC']['Equipment - Transducers'] = '\n'.join(SC_TRANS)


#######################################################################################
# IGT
#######################################################################################

IGT = 'IGT'
CONFIG_FILE_FOLDER_IGT_DS = 'igt\\config'
config['Equipment.Manufacturer.IGT'] = {}
config['Equipment.Manufacturer.IGT']['Name'] = IGT
config['Equipment.Manufacturer.IGT']['Config. file folder driving sys.'] = (
    CONFIG_FILE_FOLDER_IGT_DS)
config['Equipment.Manufacturer.IGT']['Additional charac. discon. message'] = ''

config['Equipment.Manufacturer.IGT']['Default log filename prefix'] = 'standalone_igt'
config['Equipment.Manufacturer.IGT']['Default log filename suffix'] = '_igt_ds_log'

config['Equipment.Manufacturer.IGT']['Wait time before responsive [ms]'] = str(100)
config['Equipment.Manufacturer.IGT']['Min. pulse duration [ms]'] = str(0.001)
config['Equipment.Manufacturer.IGT']['Min. pulse rep. interval [ms]'] = str(0.170)
config['Equipment.Manufacturer.IGT']['Min. time in between ramping up and down [ms]'] = str(0.070)
config['Equipment.Manufacturer.IGT']['Max. pulses in pulse train'] = str(64)

config['Equipment.Manufacturer.IGT']['Pulse dur. flag level MeasureChannels [ms]'] = str(4.570)
config['Equipment.Manufacturer.IGT']['Pulse dur. flag level MeasureBoards [ms]'] = str(0.035)
config['Equipment.Manufacturer.IGT']['Pulse dur. flag level MeasureTimings [ms]'] = str(0.001)

config['Equipment.Manufacturer.IGT']['Min. temporal ramping resolution [ms]'] = str(0.005)
config['Equipment.Manufacturer.IGT']['Max. amount of ramping steps'] = str(1023)

IGT_DS = ['IGT-128-ch', 'IGT-128-ch_comb_2x10-ch', 'IGT-128-ch_comb_1x10-ch',
          'IGT-128-ch_comb_1x8-ch', 'IGT-128-ch_comb_1x4-ch', 'IGT-128-ch_comb_1x2-ch',
          'IGT-32-ch', 'IGT-32-ch_comb_2x10-ch', 'IGT-32-ch_comb_1x10-ch',
          'IGT-8-ch_comb_2x4-ch', 'IGT-8-ch_comb_1x4-ch', 'IGT-8-ch_comb_2x2-ch',
          'IGT-8-ch_comb_1x2-ch']

config['Equipment.Manufacturer.IGT']['Equipment - Driving systems'] = '\n'.join(IGT_DS)

CONFIG_FILE_FOLDER_CONVERSION_DATA = 'igt\\config\\conversion_data'
config['Equipment.Manufacturer.IGT']['Config. file folder conversion data'] = (
    CONFIG_FILE_FOLDER_CONVERSION_DATA)

#######################################################################################
# Imasonic
#######################################################################################

IMASONIC = 'Imasonic'
CONFIG_FILE_FOLDER_IS_TRAN = 'igt\\config\\imasonic_transducers'
config['Equipment.Manufacturer.IS'] = {}
config['Equipment.Manufacturer.IS']['Name'] = IMASONIC
config['Equipment.Manufacturer.IS']['Config. file folder transducers'] = CONFIG_FILE_FOLDER_IS_TRAN

IS_TRANS = ['IS_PCD15287_01001', 'IS_PCD15287_01002', 'IS_PCD15473_01001',
            'IS_PCD15473_01002', 'IS_PCD15473_01003', 'IS_PCD15473_01001_OPM',
            'IS_PCD15473_01003_OPM']

#######################################################################################
# CITRUS
#######################################################################################

CITRUS = 'CITRUS'
config['Equipment.Manufacturer.CITRUS'] = {}
config['Equipment.Manufacturer.CITRUS']['Name'] = CITRUS

config['Equipment.Manufacturer.CITRUS']['Additional charac. discon. message'] = ''

CITRUS_DS = ['CITRUS_V2']

config['Equipment.Manufacturer.CITRUS']['Equipment - Driving systems'] = '\n'.join(CITRUS_DS)

CITRUS_TRANS = ['CITRUS_V2_465kHz_256_#5', 'CITRUS_V2_465kHz_128_#6', 'CITRUS_V2_465kHz_128_#7']

config['Equipment.Manufacturer.CITRUS']['Equipment - Transducers'] = '\n'.join(CITRUS_TRANS)

#######################################################################################
# Equipment collection
#######################################################################################

config['Equipment.Manufacturer.IS']['Equipment - Transducers'] = '\n'.join(IS_TRANS)

# list of driving system 'serial numbers'
config['Equipment']['Driving systems'] = str('\n'.join(SC_DS + IGT_DS + CITRUS_DS))
config['Equipment']['Default driving system serial'] = SC_DS[0]

DUMMY = 'Dummy'
DUMMIES = [DUMMY]
# list of transducer 'serial numbers'
config['Equipment']['Transducers'] = str('\n'.join(SC_TRANS + IS_TRANS + CITRUS_TRANS + DUMMIES))
config['Equipment']['Default transducer serial'] = SC_TRANS[0]

COMBO_JOIN_SIGN = '~'
config['Equipment']['Combination sign'] = COMBO_JOIN_SIGN

#######################################################################################
# Sonic Concepts - Driving systems
#######################################################################################

_add_driving_system(
    SC_DS[0],
    name='NeuroFUS 1 x 4 ch. or 1 x 2 ch. TPO junior ' + SC_DS[0],
    manufacturer=SONIC_CONCEPTS,
    available_channels=4,
    connection_info='COM6',
    # No Dummy here: unlike IGT, this driving system's transducer selection happens physically
    # on the hardware itself (not managed by this software), so there is nothing for a
    # software-only "Dummy load" choice to correspond to.
    transducer_compatibility=SC_TRANS,
    power_options=[POW_GP],
    native_power_parameters=POW_GP,
    focus_options=[FOC_WRT_EXIT],
    native_focus_parameters=FOC_WRT_EXIT,
    max_transducer_slots=1,
    max_buffers=1,
    active=True,
)

_add_driving_system(
    SC_DS[1],
    name='NeuroFUS 1 x 4 ch. or 1 x 2 ch. TPO senior ' + SC_DS[1],
    manufacturer=SONIC_CONCEPTS,
    available_channels=4,
    connection_info='COM5',
    # No Dummy here: unlike IGT, this driving system's transducer selection happens physically
    # on the hardware itself (not managed by this software), so there is nothing for a
    # software-only "Dummy load" choice to correspond to.
    transducer_compatibility=SC_TRANS,
    power_options=[POW_GP],
    native_power_parameters=POW_GP,
    focus_options=[FOC_WRT_EXIT],
    native_focus_parameters=FOC_WRT_EXIT,
    max_transducer_slots=1,
    max_buffers=1,
    active=True,
)


#######################################################################################
# IGT - Driving systems
#######################################################################################

# # 128 ch. # #
_add_driving_system(
    IGT_DS[0],
    name=IGT + ' 128 ch. - all channels',
    manufacturer=IGT,
    available_channels=128,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_393F.json')),
    transducer_compatibility=DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=False,
)

# 2 x 10 ch.: this driving system config drives two 10-element transducers at once.
_add_driving_system(
    IGT_DS[1],
    name=IGT + ' 128 ch. - 2 x 10 ch.',
    manufacturer=IGT,
    available_channels=20,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_2x10_393F.json')),
    transducer_compatibility=IS_TRANS + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[2],
    name=IGT + ' 128 ch. - 1 x 10 ch.',
    manufacturer=IGT,
    available_channels=10,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_1x10_393F.json')),
    transducer_compatibility=IS_TRANS + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[3],
    name=IGT + ' 128 ch. - 8 ch.',
    manufacturer=IGT,
    available_channels=8,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_8c.json')),
    transducer_compatibility=SC_TRAN_4CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[4],
    name=IGT + ' 128 ch. - 4 ch.',
    manufacturer=IGT,
    available_channels=4,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_4ch.json')),
    transducer_compatibility=SC_TRANS + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[5],
    name=IGT + ' 128 ch. - 2 ch.',
    manufacturer=IGT,
    available_channels=2,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen128_2ch.json')),
    transducer_compatibility=SC_TRAN_2CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

# # 32 ch. # #
_add_driving_system(
    IGT_DS[6],
    name=IGT + ' 32 ch. - all channels',
    manufacturer=IGT,
    available_channels=32,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen32_71D8_10W.json')),
    transducer_compatibility=DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=True,
)

# 2 x 10 ch.: this driving system config drives two 10-element transducers at once.
_add_driving_system(
    IGT_DS[7],
    name=IGT + ' 32 ch. - 2 x 10 ch.',
    manufacturer=IGT,
    available_channels=20,
    connection_info=str(os.path.join(
        CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen32_2x10c_71D8_10W.json')),
    transducer_compatibility=IS_TRANS + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=True,
)

_add_driving_system(
    IGT_DS[8],
    name=IGT + ' 32 ch. - 1 x 10 ch.',
    manufacturer=IGT,
    available_channels=10,
    connection_info=str(os.path.join(
        CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen32_10c_71D8_10W.json')),
    transducer_compatibility=IS_TRANS + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=True,
)

# # 8 ch. # #
# 2 x 4 ch.: this driving system config drives two 4-element transducers at once.
_add_driving_system(
    IGT_DS[9],
    name=IGT + ' 8 ch. - 2 x 4 ch.',
    manufacturer=IGT,
    available_channels=8,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen_8_F720.json')),
    transducer_compatibility=SC_TRAN_4CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[10],
    name=IGT + ' 8 ch. - 1 x 4 ch.',
    manufacturer=IGT,
    available_channels=4,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen_4_F720.json')),
    transducer_compatibility=SC_TRAN_4CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

# 2 x 2 ch.: this driving system config drives two 2-element transducers at once.
_add_driving_system(
    IGT_DS[11],
    name=IGT + ' 8 ch. - 2 x 2 ch.',
    manufacturer=IGT,
    available_channels=4,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen_8c4_F720.json')),
    transducer_compatibility=SC_TRAN_2CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=2,
    max_buffers=2,
    active=False,
)

_add_driving_system(
    IGT_DS[12],
    name=IGT + ' 8 ch. - 1 x 2 ch.',
    manufacturer=IGT,
    available_channels=2,
    connection_info=str(os.path.join(CONFIG_FILE_FOLDER_IGT_DS, 'gen_Nijmegen_4c2_F720.json')),
    transducer_compatibility=SC_TRAN_2CH + DUMMIES,
    power_options=[POW_AMPL, POW_PRESS, POW_VOLT],
    native_power_parameters=POW_AMPL,
    focus_options=[FOC_WRT_EXIT, FOC_WRT_BOWL],
    native_focus_parameters=FOC_WRT_BOWL,
    max_transducer_slots=1,
    max_buffers=2,
    active=False,
)

#######################################################################################
# CITRUS - Driving systems
#######################################################################################

_add_driving_system(
    CITRUS_DS[0],
    name=CITRUS + ' 256 ch.',
    manufacturer=CITRUS,
    available_channels=256,
    connection_info='COM1',
    # No Dummy here either -- same reason as Sonic Concepts: transducer selection isn't
    # software-managed for this driving system.
    transducer_compatibility=CITRUS_TRANS,
    power_options=[POW_VOLT],
    native_power_parameters=POW_VOLT,
    focus_options=[FOC_WRT_EXIT],
    native_focus_parameters=FOC_WRT_EXIT,
    max_transducer_slots=2,
    max_buffers=1,
    active=True,
)

#######################################################################################
# Sonic Concepts - Tranducers
#######################################################################################

_add_transducer(
    SC_TRANS[0], name='NeuroFUS 2 ch. CTX-250-009', manufacturer=SONIC_CONCEPTS,
    elements=2, fund_freq=250, min_focus=15.9, max_focus=46.0, exit_plane_dist=6.0,
    active=True,
)

_add_transducer(
    SC_TRANS[1], name='NeuroFUS 2 ch. CTX-250-014', manufacturer=SONIC_CONCEPTS,
    elements=2, fund_freq=250, min_focus=12.6, max_focus=44.1, exit_plane_dist=6.0,
    active=True,
)

_add_transducer(
    SC_TRANS[2], name='NeuroFUS 2 ch. CTX-500-006', manufacturer=SONIC_CONCEPTS,
    elements=2, fund_freq=500, min_focus=33.2, max_focus=79.4, exit_plane_dist=6.0,
    active=True,
)

_add_transducer(
    SC_TRANS[3], name='NeuroFUS 4 ch. CTX-250-001', manufacturer=SONIC_CONCEPTS,
    elements=4, fund_freq=250, min_focus=13.7, max_focus=61.5, exit_plane_dist=10.56,
    active=True,
)

_add_transducer(
    SC_TRANS[4], name='NeuroFUS 4 ch. CTX-250-026', manufacturer=SONIC_CONCEPTS,
    elements=4, fund_freq=250, min_focus=21.9, max_focus=61.5, exit_plane_dist=10.56,
    active=True,
)

_add_transducer(
    SC_TRANS[5], name='NeuroFUS 4 ch. CTX-500-024', manufacturer=SONIC_CONCEPTS,
    elements=4, fund_freq=500, min_focus=31.7, max_focus=77.0, exit_plane_dist=10.56,
    active=False,
)

_add_transducer(
    SC_TRANS[6], name='NeuroFUS 4 ch. CTX-500-026', manufacturer=SONIC_CONCEPTS,
    elements=4, fund_freq=500, min_focus=39.6, max_focus=79.6, exit_plane_dist=10.56,
    active=True,
)

_add_transducer(
    SC_TRANS[7], name='NeuroFUS 4 ch. DPX-500-022', manufacturer=SONIC_CONCEPTS,
    elements=4, fund_freq=500, min_focus=54, max_focus=122, active=False,
)

#######################################################################################
# Imasonic - Tranducers
#######################################################################################

_add_transducer(
    IS_TRANS[0], name=IMASONIC + ' 10 ch. PCD15287_01001 ROC 75 mm', manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=75, exit_plane_dist=9.7,
    min_focus=5.0, max_focus=91.7,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15287_10_300kHz.ini')),
    active=True,
)

_add_transducer(
    IS_TRANS[1], name=IMASONIC + ' 10 ch. PCD15287_01002 ROC 75 mm', manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=75, exit_plane_dist=9.7,
    min_focus=6.1, max_focus=93.2,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15287_10_300kHz.ini')),
    active=True,
)

_add_transducer(
    IS_TRANS[2], name=IMASONIC + ' 10 ch. PCD15473_01001 ROC 100 mm', manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=100, exit_plane_dist=7.3,
    min_focus=6.7, max_focus=92.6,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15473_10_300kHz.ini')),
    active=True,
)

_add_transducer(
    IS_TRANS[3], name=IMASONIC + ' 10 ch. PCD15473_01002 ROC 100 mm BROKEN',
    manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=100, exit_plane_dist=7.3,
    min_focus=5.32, max_focus=92.17,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15473_10_300kHz.ini')),
    active=False,
)

_add_transducer(
    IS_TRANS[4], name=IMASONIC + ' 10 ch. PCD15473_01003 ROC 100 mm', manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=100, exit_plane_dist=7.3,
    min_focus=7.2, max_focus=93.6,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15473_10_300kHz.ini')),
    active=True,
)

#######################################################################################
# OPM setup R100 Imasonic tranducers
#######################################################################################

_add_transducer(
    IS_TRANS[5], name=IMASONIC + ' 10 ch. PCD15473_01001 ROC 100 mm - OPM setup',
    manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=100, exit_plane_dist=7.3,
    min_focus=7.8, max_focus=92.0,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15473_10_300kHz_inverted_OPM.ini')),
    active=True,
)

_add_transducer(
    IS_TRANS[6], name=IMASONIC + ' 10 ch. PCD15473_01003 ROC 100 mm - OPM setup',
    manufacturer=IMASONIC,
    elements=10, fund_freq=300, natural_focus=100, exit_plane_dist=7.3,
    min_focus=6.7, max_focus=93.2,
    steer_information=str(os.path.join(
        CONFIG_FILE_FOLDER_IS_TRAN, 'transducer_15473_10_300kHz_inverted_OPM.ini')),
    active=True,
)

#######################################################################################
# Dummy tranducer
#######################################################################################

# For characterizing a driving system's own electrical output (e.g. into resistors) with no
# real transducer connected. Only usable with a driving system's native power/focus parameters
# -- there is no Equipment.Combination.* calibration for Dummy with any driving system, and none
# is meaningful: a dummy load has no real acoustic behavior to calibrate against, so setting a
# non-native option (e.g. a target pressure) would exit with a "no active calibration" error.
_add_transducer(
    DUMMY, name='Dummy load', manufacturer='', elements=0, fund_freq=0,
    min_focus=0, max_focus=1000, active=True,
)

#######################################################################################
# CITRUS - Tranducers
#######################################################################################

_add_transducer(
    CITRUS_TRANS[0], name='CITRUS_V2_465kHz_256_#5', manufacturer=CITRUS,
    elements=256, fund_freq=465, min_focus=0, max_focus=200, active=True,
)

_add_transducer(
    CITRUS_TRANS[1], name='CITRUS_V2_465kHz_128_#6', manufacturer=CITRUS,
    elements=128, fund_freq=465, min_focus=0, max_focus=200, active=True,
)

_add_transducer(
    CITRUS_TRANS[2], name='CITRUS_V2_465kHz_128_#7', manufacturer=CITRUS,
    elements=128, fund_freq=465, min_focus=0, max_focus=200, active=True,
)

#######################################################################################
# Driving system - transducer combinations
#######################################################################################

# No calibration data exists yet for these 128-ch combinations -- kept as ready-to-uncomment
# templates (matching _combo_files_exist()'s automatic Active?, they'd generate Active? = False
# until the calibration JSON files referenced below actually exist on disk).

# _add_combination(
#     IGT_DS[1], IS_TRANS[0],
#     'IS_PCD15287_01001_equalizationCurveFitExport.json',
#     'IS_PCD15287_01001_focusCurveFitExport.json',
#     'IS_PCD15287_01001_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[1], IS_TRANS[1],
#     'IS_PCD15287_01002_equalizationCurveFitExport.json',
#     'IS_PCD15287_01002_focusCurveFitExport.json',
#     'IS_PCD15287_01002_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[1], IS_TRANS[2],
#     'IS_PCD15473_01001_equalizationCurveFitExport.json',
#     'IS_PCD15473_01001_focusCurveFitExport.json',
#     'IS_PCD15473_01001_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[1], IS_TRANS[3],
#     'IS_PCD15473_01002_equalizationCurveFitExport.json',
#     'IS_PCD15473_01002_focusCurveFitExport.json',
#     'IS_PCD15473_01002_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[1], IS_TRANS[4],
#     'IS_PCD15473_01003_equalizationCurveFitExport.json',
#     'IS_PCD15473_01003_focusCurveFitExport.json',
#     'IS_PCD15473_01003_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[2], IS_TRANS[0],
#     'IS_PCD15287_01001_equalizationCurveFitExport.json',
#     'IS_PCD15287_01001_focusCurveFitExport.json',
#     'IS_PCD15287_01001_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[2], IS_TRANS[1],
#     'IS_PCD15287_01002_equalizationCurveFitExport.json',
#     'IS_PCD15287_01002_focusCurveFitExport.json',
#     'IS_PCD15287_01002_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[2], IS_TRANS[2],
#     'IS_PCD15473_01001_equalizationCurveFitExport.json',
#     'IS_PCD15473_01001_focusCurveFitExport.json',
#     'IS_PCD15473_01001_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[2], IS_TRANS[3],
#     'IS_PCD15473_01002_equalizationCurveFitExport.json',
#     'IS_PCD15473_01002_focusCurveFitExport.json',
#     'IS_PCD15473_01002_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# _add_combination(
#     IGT_DS[2], IS_TRANS[4],
#     'IS_PCD15473_01003_equalizationCurveFitExport.json',
#     'IS_PCD15473_01003_focusCurveFitExport.json',
#     'IS_PCD15473_01003_powerCurveFitExport.json',
#     'voltageCurveFit_IGT_128_ch.json')

# IGT-32-ch_comb_2x10-ch combinations
_add_combination(
    IGT_DS[7], IS_TRANS[0],
    'IS_PCD15287_01001_equalizationCurveFitExport.json',
    'IS_PCD15287_01001_focusCurveFitExport.json',
    'IS_PCD15287_01001_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[1],
    'IS_PCD15287_01002_equalizationCurveFitExport.json',
    'IS_PCD15287_01002_focusCurveFitExport.json',
    'IS_PCD15287_01002_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[2],
    'IS_PCD15473_01001_equalizationCurveFitExport.json',
    'IS_PCD15473_01001_focusCurveFitExport.json',
    'IS_PCD15473_01001_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[3],
    'IS_PCD15473_01002_equalizationCurveFitExport.json',
    'IS_PCD15473_01002_focusCurveFitExport.json',
    'IS_PCD15473_01002_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[4],
    'IS_PCD15473_01003_equalizationCurveFitExport.json',
    'IS_PCD15473_01003_focusCurveFitExport.json',
    'IS_PCD15473_01003_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[5],
    'IS_PCD15473_01001_OPM_equalizationCurveFitExport.json',
    'IS_PCD15473_01001_OPM_focusCurveFitExport.json',
    'IS_PCD15473_01001_OPM_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[7], IS_TRANS[6],
    'IS_PCD15473_01003_OPM_equalizationCurveFitExport.json',
    'IS_PCD15473_01003_OPM_focusCurveFitExport.json',
    'IS_PCD15473_01003_OPM_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')

# IGT-32-ch_comb_1x10-ch combinations
_add_combination(
    IGT_DS[8], IS_TRANS[0],
    'IS_PCD15287_01001_equalizationCurveFitExport.json',
    'IS_PCD15287_01001_focusCurveFitExport.json',
    'IS_PCD15287_01001_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[1],
    'IS_PCD15287_01002_equalizationCurveFitExport.json',
    'IS_PCD15287_01002_focusCurveFitExport.json',
    'IS_PCD15287_01002_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[2],
    'IS_PCD15473_01001_equalizationCurveFitExport.json',
    'IS_PCD15473_01001_focusCurveFitExport.json',
    'IS_PCD15473_01001_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[3],
    'IS_PCD15473_01002_equalizationCurveFitExport.json',
    'IS_PCD15473_01002_focusCurveFitExport.json',
    'IS_PCD15473_01002_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[4],
    'IS_PCD15473_01003_equalizationCurveFitExport.json',
    'IS_PCD15473_01003_focusCurveFitExport.json',
    'IS_PCD15473_01003_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[5],
    'IS_PCD15473_01001_OPM_equalizationCurveFitExport.json',
    'IS_PCD15473_01001_OPM_focusCurveFitExport.json',
    'IS_PCD15473_01001_OPM_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')
_add_combination(
    IGT_DS[8], IS_TRANS[6],
    'IS_PCD15473_01003_OPM_equalizationCurveFitExport.json',
    'IS_PCD15473_01003_OPM_focusCurveFitExport.json',
    'IS_PCD15473_01003_OPM_powerCurveFitExport.json',
    'voltageCurveFit_IGT_32_ch.json')

with open(CONFIG_FILE, 'w') as configfile:
    config.write(configfile)

# Insert a comment directly above the max-pressure key in the generated file itself: hand-editing
# this file is fine, but a plain '= value' line gives no hint that the edit is silently lost the
# next time this script regenerates the file, or a new package release ships a fresh one.
with open(CONFIG_FILE, encoding='utf-8') as configfile:
    generated_contents = configfile.read()

MAX_PRESSURE_LINE = f'{MAX_PRESSURE_KEY.lower()} = {MAX_ALLOWED_PRESSURE}'
MAX_PRESSURE_WARNING = (
    '; SAFETY LIMIT: only raise this after confirming your hardware and setup can safely\n'
    "; exceed it. Hand-editing this value is fine, but it will be silently overwritten if\n"
    '; this file is ever regenerated via create_config.py, or replaced by installing a new\n'
    '; package release -- keep a copy of your override if you rely on it long-term.\n'
)
generated_contents = generated_contents.replace(
    MAX_PRESSURE_LINE, MAX_PRESSURE_WARNING + MAX_PRESSURE_LINE)

# Same idea for min. focus/max. focus, but these two keys appear once per transducer (each with
# its own value) rather than once globally, so a plain string .replace() can't target every
# occurrence -- use a regex instead. One comment above min. focus already covers max. focus too,
# since the two are always written directly adjacent to each other.
MIN_FOCUS_NOTE = (
    '; Only used as-is when no calibration is active for this transducer/driving-system pair --\n'
    "; once one is, both are silently overwritten (not merely defaulted) by the equalization\n"
    '; curve\'s own breaks (see TransducerSlot._update_conv_param() / README.md).\n'
)
generated_contents = re.sub(
    r'^min\. focus = .*$',
    lambda match: MIN_FOCUS_NOTE + match.group(0),
    generated_contents, flags=re.MULTILINE)

with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
    configfile.write(generated_contents)
