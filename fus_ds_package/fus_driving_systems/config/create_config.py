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

from fus_driving_systems import utils
import configparser
import os


CONFIG_FOLDER = utils.get_config_folder()  # should be in the same directory as code
CONFIG_FILE = utils.get_config_file()

config = configparser.ConfigParser(interpolation=None)

config['General'] = {}

config['General']['Configuration file folder'] = CONFIG_FOLDER
config['General']['Maximum reconnection attempts'] = str(5)
config['General']['Package name'] = 'fus_driving_systems'
config['General']['Speed of sound water [m/s]'] = str(1500)

# Logging
config['Logging'] = {}
config['Logging']['Logger name'] = 'driving_system'
config['Logging']['Temporary logging path'] = 'C:\\Temp'
config['Logging']['Filename faulthandler'] = 'faulthandler_output.log'

config['Logging']['Timestamp format'] = '%Y-%m-%d_%H-%M-%S'
config['Logging']['Log level console'] = 'WARNING'
config['Logging']['Log level file'] = 'INFO'
config['Logging']['Initial part of log filename'] = 'log_'

# Trigger options
TRIG_NONE = 'None'
TRIG_SEQ = 'TriggerSequence'
TRIG_PTR = 'TriggerOnePulseTrainRepetition'

config['Trigger'] = {}
config['Trigger']['Options'] = '\n'.join([TRIG_NONE, TRIG_SEQ, TRIG_PTR])
config['Trigger']['Default option'] = TRIG_NONE
config['Trigger']['Option.none'] = TRIG_NONE
config['Trigger']['Option.seq'] = TRIG_SEQ
config['Trigger']['Option.ptr'] = TRIG_PTR

config['Trigger']['Default wait_for_trigger'] = 'False'
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

config['Power']['Default.glob_pow'] = str(0)
config['Power']['Default.ampl'] = str(0)
config['Power']['Default.press'] = str(0)
config['Power']['Default.volt'] = str(0)

config['Power']['Default.eq_factor'] = str(0)

MAX_ALLOWED_PRESSURE = 1.4  # MPa
config['Power']['Maximum pressure allowed in free water [MPa]'] = str(MAX_ALLOWED_PRESSURE)

# Focus options
FOC_WRT_EXIT = 'Focus wrt exit plane [mm]'
FOC_WRT_BOWL = 'Focus wrt mid bowl [mm]'

config['Focus'] = {}
config['Focus']['Options'] = '\n'.join([FOC_WRT_EXIT, FOC_WRT_BOWL])
config['Focus']['Default option'] = FOC_WRT_EXIT
config['Focus']['Option.exit'] = FOC_WRT_EXIT
config['Focus']['Option.bowl'] = FOC_WRT_BOWL

config['Focus']['Default.exit'] = str(40)  # [mm]
config['Focus']['Default.bowl'] = str(50)  # [mm]
config['Focus']['Default.minimum'] = str(0)  # [mm]
config['Focus']['Default.maximum'] = str(1000)  # [mm]

# Ramp options
RAMP_RECT = 'Rectangular - no ramping'
RAMP_LIN = 'Linear'
RAMP_TUK = 'Tukey'
RAMP_SHOTA = 'Shota'

config['Ramp'] = {}
config['Ramp']['Options'] = '\n'.join([RAMP_RECT, RAMP_LIN, RAMP_TUK])
config['Ramp']['Default option'] = RAMP_RECT
config['Ramp']['Option.rect'] = RAMP_RECT
config['Ramp']['Option.lin'] = RAMP_LIN
config['Ramp']['Option.tuk'] = RAMP_TUK
config['Ramp']['Option.shota'] = RAMP_SHOTA

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

# TODO: deprecated - hosted under each driving system
config['Equipment.Manufacturer.SC']['Power options'] = '\n'.join([POW_GP])
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
config['Equipment.Manufacturer.IGT']['Config. file folder driving sys.'] = CONFIG_FILE_FOLDER_IGT_DS
config['Equipment.Manufacturer.IGT']['Power options'] = '\n'.join([POW_AMPL, POW_PRESS, POW_VOLT])
config['Equipment.Manufacturer.IGT']['Additional charac. discon. message'] = ''

config['Equipment.Manufacturer.IGT']['Default log filename prefix'] = 'standalone_igt'
config['Equipment.Manufacturer.IGT']['Default log filename suffix'] = '_igt_ds_log'

config['Equipment.Manufacturer.IGT']['Wait time before reponsive [ms]'] = str(100)
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


#######################################################################################
# Imasonic
#######################################################################################

IMASONIC = 'Imasonic'
CONFIG_FILE_FOLDER_IS_TRAN = 'igt\\config\\imasonic_transducers'
config['Equipment.Manufacturer.IS'] = {}
config['Equipment.Manufacturer.IS']['Name'] = IMASONIC
config['Equipment.Manufacturer.IS']['Config. file folder transducers'] = CONFIG_FILE_FOLDER_IS_TRAN

IS_TRANS = ['IS_PCD15287_01001', 'IS_PCD15287_01002', 'IS_PCD15473_01001', 'IS_PCD15473_01002']


#######################################################################################
# Equipment collection
#######################################################################################

config['Equipment.Manufacturer.IS']['Equipment - Transducers'] = '\n'.join(IS_TRANS)

# list of driving system 'serial numbers'
config['Equipment']['Driving systems'] = str('\n'.join(SC_DS + IGT_DS))
config['Equipment']['Default driving system serial'] = SC_DS[0]

DUMMY = 'Dummy'
DUMMIES = [DUMMY]
# list of transducer 'serial numbers'
config['Equipment']['Transducers'] = str('\n'.join(SC_TRANS + IS_TRANS + DUMMIES))
config['Equipment']['Default transducer serial'] = SC_TRANS[0]

COMBO_JOIN_SIGN = '~'
config['Equipment']['Combination sign'] = COMBO_JOIN_SIGN

DS_TRAN_COMBOS = [
    # IGT 128 ch. 2 x 10
    COMBO_JOIN_SIGN.join([IGT_DS[1], IS_TRANS[0]]), COMBO_JOIN_SIGN.join([IGT_DS[1], IS_TRANS[1]]),
    COMBO_JOIN_SIGN.join([IGT_DS[1], IS_TRANS[2]]), COMBO_JOIN_SIGN.join([IGT_DS[1], IS_TRANS[3]]),

    # IGT 128 ch. 1 x 10
    COMBO_JOIN_SIGN.join([IGT_DS[2], IS_TRANS[0]]), COMBO_JOIN_SIGN.join([IGT_DS[2], IS_TRANS[1]]),
    COMBO_JOIN_SIGN.join([IGT_DS[2], IS_TRANS[2]]), COMBO_JOIN_SIGN.join([IGT_DS[2], IS_TRANS[3]]),

    # IGT 32 ch. 2 x 10
    COMBO_JOIN_SIGN.join([IGT_DS[7], IS_TRANS[0]]), COMBO_JOIN_SIGN.join([IGT_DS[7], IS_TRANS[1]]),
    COMBO_JOIN_SIGN.join([IGT_DS[7], IS_TRANS[2]]), COMBO_JOIN_SIGN.join([IGT_DS[7], IS_TRANS[3]]),

    # IGT 32 ch. 1 x 10
    COMBO_JOIN_SIGN.join([IGT_DS[8], IS_TRANS[0]]), COMBO_JOIN_SIGN.join([IGT_DS[8], IS_TRANS[1]]),
    COMBO_JOIN_SIGN.join([IGT_DS[8], IS_TRANS[2]]), COMBO_JOIN_SIGN.join([IGT_DS[8], IS_TRANS[3]])
                                                     ]

config['Equipment']['Combinations'] = '\n'.join(DS_TRAN_COMBOS)
config['Equipment']['inactive_combinations'] = ''

#######################################################################################
# Sonic Concepts - Driving systems
#######################################################################################

config['Equipment.Driving system.' + SC_DS[0]] = {}
config['Equipment.Driving system.' + SC_DS[0]]['Name'] = ('NeuroFUS 1 x 4 ch. or 1 x 2 ch. TPO '
                                                          + 'junior ' + SC_DS[0])
config['Equipment.Driving system.' + SC_DS[0]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Driving system.' + SC_DS[0]]['Available channels'] = str(4)
config['Equipment.Driving system.' + SC_DS[0]]['Connection info'] = 'COM6'
config['Equipment.Driving system.' + SC_DS[0]]['Power options'] = '\n'.join([POW_GP])
config['Equipment.Driving system.' + SC_DS[0]]['Requires conversion equations?'] = str(False)
config['Equipment.Driving system.' + SC_DS[0]]['Transducer compatibility'] = str('\n'.join(
    SC_TRANS + DUMMIES))
config['Equipment.Driving system.' + SC_DS[0]]['Active?'] = str(True)

config['Equipment.Driving system.' + SC_DS[1]] = {}
config['Equipment.Driving system.' + SC_DS[1]]['Name'] = ('NeuroFUS 1 x 4 ch. or 1 x 2 ch. TPO '
                                                          + 'senior ' + SC_DS[1])
config['Equipment.Driving system.' + SC_DS[1]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Driving system.' + SC_DS[1]]['Available channels'] = str(4)
config['Equipment.Driving system.' + SC_DS[1]]['Connection info'] = 'COM5'
config['Equipment.Driving system.' + SC_DS[1]]['Transducer compatibility'] = str('\n'.join(
    SC_TRANS + DUMMIES))
config['Equipment.Driving system.' + SC_DS[1]]['Power options'] = '\n'.join([POW_GP])
config['Equipment.Driving system.' + SC_DS[1]]['Requires conversion equations?'] = str(False)
config['Equipment.Driving system.' + SC_DS[1]]['Active?'] = str(True)


#######################################################################################
# IGT - Driving systems
#######################################################################################

# # 128 ch. # #
IGT_128_ch = {}
IGT_128_ch['v2a_a_coeff'] = 6.1122
IGT_128_ch['v2a_b_coeff'] = -0.4917

config['Equipment.Driving system.' + IGT_DS[0]] = {}
config['Equipment.Driving system.' + IGT_DS[0]]['Name'] = IGT + ' 128 ch. - all channels'
config['Equipment.Driving system.' + IGT_DS[0]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[0]]['Available channels'] = str(128)
config['Equipment.Driving system.' + IGT_DS[0]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_393F.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[0]]['Transducer compatibility'] = str('\n'.join(
    DUMMIES))
config['Equipment.Driving system.' + IGT_DS[0]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[0]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[0]]['Active?'] = str(True)

config['Equipment.Driving system.' + IGT_DS[1]] = {}
config['Equipment.Driving system.' + IGT_DS[1]]['Name'] = IGT + ' 128 ch. - 2 x 10 ch.'
config['Equipment.Driving system.' + IGT_DS[1]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[1]]['Available channels'] = str(20)
config['Equipment.Driving system.' + IGT_DS[1]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_2x10_393F.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[1]]['Transducer compatibility'] = str('\n'.join(
    IS_TRANS + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[1]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[1]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[1]]['Active?'] = str(True)

config['Equipment.Driving system.' + IGT_DS[2]] = {}
config['Equipment.Driving system.' + IGT_DS[2]]['Name'] = IGT + ' 128 ch. - 1 x 10 ch.'
config['Equipment.Driving system.' + IGT_DS[2]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[2]]['Available channels'] = str(10)
config['Equipment.Driving system.' + IGT_DS[2]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_1x10_393F.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[2]]['Transducer compatibility'] = str('\n'.join(
    IS_TRANS + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[2]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[2]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[2]]['Active?'] = str(True)

config['Equipment.Driving system.' + IGT_DS[3]] = {}
config['Equipment.Driving system.' + IGT_DS[3]]['Name'] = IGT + ' 128 ch. - 8 ch.'
config['Equipment.Driving system.' + IGT_DS[3]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[3]]['Available channels'] = str(8)
config['Equipment.Driving system.' + IGT_DS[3]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_8c.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[3]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_4CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[3]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[3]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[3]]['Active?'] = str(False)

config['Equipment.Driving system.' + IGT_DS[4]] = {}
config['Equipment.Driving system.' + IGT_DS[4]]['Name'] = IGT + ' 128 ch. - 4 ch.'
config['Equipment.Driving system.' + IGT_DS[4]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[4]]['Available channels'] = str(4)
config['Equipment.Driving system.' + IGT_DS[4]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_4ch.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[4]]['Transducer compatibility'] = str('\n'.join(
    SC_TRANS + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[4]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[4]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[4]]['Active?'] = str(False)

config['Equipment.Driving system.' + IGT_DS[5]] = {}
config['Equipment.Driving system.' + IGT_DS[5]]['Name'] = IGT + ' 128 ch. - 2 ch.'
config['Equipment.Driving system.' + IGT_DS[5]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[5]]['Available channels'] = str(2)
config['Equipment.Driving system.' + IGT_DS[5]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen128_2ch.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[5]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_2CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[5]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[5]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[5]]['Active?'] = str(False)

# # 32 ch. # #

IGT_32_ch = {}
IGT_32_ch['v2a_a_coeff'] = 6.1393
IGT_32_ch['v2a_b_coeff'] = -0.7172

config['Equipment.Driving system.' + IGT_DS[6]] = {}
config['Equipment.Driving system.' + IGT_DS[6]]['Name'] = IGT + ' 32 ch. - all channels'
config['Equipment.Driving system.' + IGT_DS[6]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[6]]['Available channels'] = str(32)
config['Equipment.Driving system.' + IGT_DS[6]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen32_71D8.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[6]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[6]]['Transducer compatibility'] = str('\n'.join(
    DUMMIES))
config['Equipment.Driving system.' + IGT_DS[6]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[6]]['Active?'] = str(True)

config['Equipment.Driving system.' + IGT_DS[7]] = {}
config['Equipment.Driving system.' + IGT_DS[7]]['Name'] = IGT + ' 32 ch. - 2 x 10 ch.'
config['Equipment.Driving system.' + IGT_DS[7]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[7]]['Available channels'] = str(20)
config['Equipment.Driving system.' + IGT_DS[7]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen32_2x10c_71D8.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[7]]['Transducer compatibility'] = str('\n'.join(
    IS_TRANS + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[7]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[7]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[7]]['Active?'] = str(True)

config['Equipment.Driving system.' + IGT_DS[8]] = {}
config['Equipment.Driving system.' + IGT_DS[8]]['Name'] = IGT + ' 32 ch. - 1 x 10 ch.'
config['Equipment.Driving system.' + IGT_DS[8]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[8]]['Available channels'] = str(10)
config['Equipment.Driving system.' + IGT_DS[8]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen32_10c_71D8.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[8]]['Transducer compatibility'] = str('\n'.join(
    IS_TRANS + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[8]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[8]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[8]]['Active?'] = str(True)


# # 8 ch. # #

IGT_8_ch = {}
IGT_8_ch['v2a_a_coeff'] = 0
IGT_8_ch['v2a_b_coeff'] = 0

config['Equipment.Driving system.' + IGT_DS[9]] = {}
config['Equipment.Driving system.' + IGT_DS[9]]['Name'] = IGT + ' 8 ch. - 2 x 4 ch.'
config['Equipment.Driving system.' + IGT_DS[9]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[9]]['Available channels'] = str(8)
config['Equipment.Driving system.' + IGT_DS[9]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen_8_F720.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[9]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_4CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[9]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[9]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[9]]['Active?'] = str(False)

config['Equipment.Driving system.' + IGT_DS[10]] = {}
config['Equipment.Driving system.' + IGT_DS[10]]['Name'] = IGT + ' 8 ch. - 1 x 4 ch.'
config['Equipment.Driving system.' + IGT_DS[10]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[10]]['Available channels'] = str(4)
config['Equipment.Driving system.' + IGT_DS[10]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen_4_F720.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[10]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_4CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[10]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[10]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[10]]['Active?'] = str(False)

config['Equipment.Driving system.' + IGT_DS[11]] = {}
config['Equipment.Driving system.' + IGT_DS[11]]['Name'] = IGT + ' 8 ch. - 2 x 2 ch.'
config['Equipment.Driving system.' + IGT_DS[11]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[11]]['Available channels'] = str(4)
config['Equipment.Driving system.' + IGT_DS[11]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen_8c4_F720.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[11]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_2CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[11]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[11]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[11]]['Active?'] = str(False)

config['Equipment.Driving system.' + IGT_DS[12]] = {}
config['Equipment.Driving system.' + IGT_DS[12]]['Name'] = IGT + ' 8 ch. - 1 x 2 ch.'
config['Equipment.Driving system.' + IGT_DS[12]]['Manufacturer'] = IGT
config['Equipment.Driving system.' + IGT_DS[12]]['Available channels'] = str(2)
config['Equipment.Driving system.' + IGT_DS[12]]['Connection info'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IGT_DS,
    'gen_Nijmegen_4c2_F720.json'))  # should be in the same directory as code
config['Equipment.Driving system.' + IGT_DS[12]]['Transducer compatibility'] = str('\n'.join(
    SC_TRAN_2CH + DUMMIES))
config['Equipment.Driving system.' + IGT_DS[12]]['Power options'] = '\n'.join([POW_AMPL, POW_PRESS,
                                                                              POW_VOLT])
config['Equipment.Driving system.' + IGT_DS[12]]['Requires conversion equations?'] = str(True)
config['Equipment.Driving system.' + IGT_DS[12]]['Active?'] = str(False)


#######################################################################################
# Sonic Concepts - Tranducers
#######################################################################################

config['Equipment.Transducer.' + SC_TRANS[0]] = {}
config['Equipment.Transducer.' + SC_TRANS[0]]['Name'] = 'NeuroFUS 2 ch. CTX-250-009'
config['Equipment.Transducer.' + SC_TRANS[0]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[0]]['Elements'] = str(2)
config['Equipment.Transducer.' + SC_TRANS[0]]['Fund. freq.'] = str(250)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[0]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[0]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[0]]['Min. focus'] = str(15.9)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[0]]['Max. focus'] = str(46.0)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[0]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-250-009 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[0]]['Active?'] = str(True)

config['Equipment.Transducer.' + SC_TRANS[1]] = {}
config['Equipment.Transducer.' + SC_TRANS[1]]['Name'] = 'NeuroFUS 2 ch. CTX-250-014'
config['Equipment.Transducer.' + SC_TRANS[1]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[1]]['Elements'] = str(2)
config['Equipment.Transducer.' + SC_TRANS[1]]['Fund. freq.'] = str(250)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[1]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[1]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[1]]['Min. focus'] = str(12.6)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[1]]['Max. focus'] = str(44.1)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[1]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-250-014 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[1]]['Active?'] = str(True)


config['Equipment.Transducer.' + SC_TRANS[2]] = {}
config['Equipment.Transducer.' + SC_TRANS[2]]['Name'] = 'NeuroFUS 2 ch. CTX-500-006'
config['Equipment.Transducer.' + SC_TRANS[2]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[2]]['Elements'] = str(2)
config['Equipment.Transducer.' + SC_TRANS[2]]['Fund. freq.'] = str(500)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[2]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[2]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[2]]['Min. focus'] = str(33.2)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[2]]['Max. focus'] = str(79.4)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[2]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-500-006 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[2]]['Active?'] = str(True)

config['Equipment.Transducer.' + SC_TRANS[3]] = {}
config['Equipment.Transducer.' + SC_TRANS[3]]['Name'] = 'NeuroFUS 4 ch. CTX-250-001'
config['Equipment.Transducer.' + SC_TRANS[3]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[3]]['Elements'] = str(4)
config['Equipment.Transducer.' + SC_TRANS[3]]['Fund. freq.'] = str(250)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[3]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[3]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[3]]['Min. focus'] = str(14.2)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[3]]['Max. focus'] = str(60.9)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[3]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-250-001 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[3]]['Active?'] = str(True)

config['Equipment.Transducer.' + SC_TRANS[4]] = {}
config['Equipment.Transducer.' + SC_TRANS[4]]['Name'] = 'NeuroFUS 4 ch. CTX-250-026'
config['Equipment.Transducer.' + SC_TRANS[4]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[4]]['Elements'] = str(4)
config['Equipment.Transducer.' + SC_TRANS[4]]['Fund. freq.'] = str(250)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[4]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[4]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[4]]['Min. focus'] = str(22.2)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[4]]['Max. focus'] = str(61.5)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[4]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-250-026 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[4]]['Active?'] = str(True)

config['Equipment.Transducer.' + SC_TRANS[5]] = {}
config['Equipment.Transducer.' + SC_TRANS[5]]['Name'] = 'NeuroFUS 4 ch. CTX-500-024'
config['Equipment.Transducer.' + SC_TRANS[5]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[5]]['Elements'] = str(4)
config['Equipment.Transducer.' + SC_TRANS[5]]['Fund. freq.'] = str(500)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[5]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[5]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[5]]['Min. focus'] = str(31.7)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[5]]['Max. focus'] = str(77.0)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[5]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-500-024 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[5]]['Active?'] = str(False)

config['Equipment.Transducer.' + SC_TRANS[6]] = {}
config['Equipment.Transducer.' + SC_TRANS[6]]['Name'] = 'NeuroFUS 4 ch. CTX-500-026'
config['Equipment.Transducer.' + SC_TRANS[6]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[6]]['Elements'] = str(4)
config['Equipment.Transducer.' + SC_TRANS[6]]['Fund. freq.'] = str(500)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[6]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[6]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[6]]['Min. focus'] = str(39.6)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[6]]['Max. focus'] = str(79.6)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[6]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_SC_TRAN,
    'CTX-500-026 - TPO-105-010 - Steer Table.xlsx'))  # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[6]]['Active?'] = str(True)

config['Equipment.Transducer.' + SC_TRANS[7]] = {}
config['Equipment.Transducer.' + SC_TRANS[7]]['Name'] = 'NeuroFUS 4 ch. DPX-500-022'
config['Equipment.Transducer.' + SC_TRANS[7]]['Manufacturer'] = SONIC_CONCEPTS
config['Equipment.Transducer.' + SC_TRANS[7]]['Elements'] = str(4)
config['Equipment.Transducer.' + SC_TRANS[7]]['Fund. freq.'] = str(500)  # [kHz]
config['Equipment.Transducer.' + SC_TRANS[7]]['Natural focus'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[7]]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + SC_TRANS[7]]['Min. focus'] = str(54)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[7]]['Max. focus'] = str(122)  # [mm], wrt exit plane
config['Equipment.Transducer.' + SC_TRANS[7]]['Steer information'] = '' # should be in the same directory as code
config['Equipment.Transducer.' + SC_TRANS[7]]['Active?'] = str(True)

#######################################################################################
# Imasonic - Tranducers
#######################################################################################

IS_15287_1001 = {}
IS_15287_1001['p2a_a_coeff'] = 0.000082054668313
IS_15287_1001['p2a_b_coeff'] = -0.033911682289495
IS_15287_1001['df2sf_a_coeff'] = 1.018224584320300
IS_15287_1001['df2sf_b_coeff'] = 9.639417185685110
IS_15287_1001['f2eqf1_foc_low_lim'] = 7.19
IS_15287_1001['f2eqf1_foc_upper_lim'] = 18.74
IS_15287_1001['f2eqf1_a0_coeff'] = -4.15658138190493
IS_15287_1001['f2eqf1_a1_coeff'] = 2.0850949129438
IS_15287_1001['f2eqf1_a2_coeff'] = -0.298158433937165
IS_15287_1001['f2eqf1_a3_coeff'] = 0.0192639743467205
IS_15287_1001['f2eqf1_a4_coeff'] = -0.000583222233476554
IS_15287_1001['f2eqf1_a5_coeff'] = 6.72077922560719e-06
IS_15287_1001['f2eqf1_a6_coeff'] = 0
IS_15287_1001['f2eqf1_a7_coeff'] = 0
IS_15287_1001['f2eqf2_foc_low_lim'] = 18.74
IS_15287_1001['f2eqf2_foc_upper_lim'] = 96.01
IS_15287_1001['f2eqf2_a0_coeff'] = 0.461307101083033
IS_15287_1001['f2eqf2_a1_coeff'] = 0.00624309239733177
IS_15287_1001['f2eqf2_a2_coeff'] = 4.47711157280263e-05
IS_15287_1001['f2eqf2_a3_coeff'] = -1.92923194701268e-07
IS_15287_1001['f2eqf2_a4_coeff'] = 0
IS_15287_1001['f2eqf2_a5_coeff'] = 0
IS_15287_1001['f2eqf2_a6_coeff'] = 0
IS_15287_1001['f2eqf2_a7_coeff'] = 0

config['Equipment.Transducer.' + IS_TRANS[0]] = {}
config['Equipment.Transducer.' + IS_TRANS[0]]['Name'] = (IMASONIC +
                                                         ' 10 ch. PCD15287_01001 ROC 75 mm')
config['Equipment.Transducer.' + IS_TRANS[0]]['Manufacturer'] = IMASONIC
config['Equipment.Transducer.' + IS_TRANS[0]]['Elements'] = str(10)
config['Equipment.Transducer.' + IS_TRANS[0]]['Fund. freq.'] = str(300)  # [kHz]
config['Equipment.Transducer.' + IS_TRANS[0]]['Natural focus'] = str(75)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[0]]['Exit plane - first element dist.'] = str(9.7)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[0]]['Min. focus'] = str(IS_15287_1001['f2eqf1_foc_low_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[0]]['Max. focus'] = str(IS_15287_1001['f2eqf2_foc_upper_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[0]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IS_TRAN,
    'transducer_15287_10_300kHz.ini'))  # should be in the same directory as code
config['Equipment.Transducer.' + IS_TRANS[0]]['Active?'] = str(True)

IS_15287_1002 = {}
IS_15287_1002['p2a_a_coeff'] = 0.000082382997297
IS_15287_1002['p2a_b_coeff'] = -0.074808010677911
IS_15287_1002['df2sf_a_coeff'] = 1.008225863268538
IS_15287_1002['df2sf_b_coeff'] = 8.851388328773629
IS_15287_1002['f2eqf1_foc_low_lim'] = 7.05
IS_15287_1002['f2eqf1_foc_upper_lim'] = 19.65
IS_15287_1002['f2eqf1_a0_coeff'] = 30.6830498533291
IS_15287_1002['f2eqf1_a1_coeff'] = -18.0451551494184
IS_15287_1002['f2eqf1_a2_coeff'] = 4.54917445340624
IS_15287_1002['f2eqf1_a3_coeff'] = -0.613218695316875
IS_15287_1002['f2eqf1_a4_coeff'] = 0.0478107944123514
IS_15287_1002['f2eqf1_a5_coeff'] = -0.00216778531206177
IS_15287_1002['f2eqf1_a6_coeff'] = 5.31961813315904e-05
IS_15287_1002['f2eqf1_a7_coeff'] = -5.4723963282926e-07
IS_15287_1002['f2eqf2_foc_low_lim'] = 19.65
IS_15287_1002['f2eqf2_foc_upper_lim'] = 93.92
IS_15287_1002['f2eqf2_a0_coeff'] = 0.898964661744547
IS_15287_1002['f2eqf2_a1_coeff'] = -0.038286218314933
IS_15287_1002['f2eqf2_a2_coeff'] = 0.00165181603456986
IS_15287_1002['f2eqf2_a3_coeff'] = -2.72985702783128e-05
IS_15287_1002['f2eqf2_a4_coeff'] = 2.16917491436039e-07
IS_15287_1002['f2eqf2_a5_coeff'] = -6.66061534849006e-10
IS_15287_1002['f2eqf2_a6_coeff'] = 0
IS_15287_1002['f2eqf2_a7_coeff'] = 0

config['Equipment.Transducer.' + IS_TRANS[1]] = {}
config['Equipment.Transducer.' + IS_TRANS[1]]['Name'] = (IMASONIC +
                                                         ' 10 ch. PCD15287_01002 ROC 75 mm')
config['Equipment.Transducer.' + IS_TRANS[1]]['Manufacturer'] = IMASONIC
config['Equipment.Transducer.' + IS_TRANS[1]]['Elements'] = str(10)
config['Equipment.Transducer.' + IS_TRANS[1]]['Fund. freq.'] = str(300)  # [kHz]
config['Equipment.Transducer.' + IS_TRANS[1]]['Natural focus'] = str(75)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[1]]['Exit plane - first element dist.'] = str(9.7)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[1]]['Min. focus'] = str(IS_15287_1002['f2eqf1_foc_low_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[1]]['Max. focus'] = str(IS_15287_1002['f2eqf2_foc_upper_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[1]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IS_TRAN,
    'transducer_15287_10_300kHz.ini'))  # should be in the same directory as code
config['Equipment.Transducer.' + IS_TRANS[1]]['Active?'] = str(True)

IS_15473_1001 = {}
IS_15473_1001['p2a_a_coeff'] = 0.000108856063340
IS_15473_1001['p2a_b_coeff'] = -0.040608603214349
IS_15473_1001['df2sf_a_coeff'] = 1.001417337686330
IS_15473_1001['df2sf_b_coeff'] = 6.501919735352103
IS_15473_1001['f2eqf1_foc_low_lim'] = 11.41
IS_15473_1001['f2eqf1_foc_upper_lim'] = 23.91
IS_15473_1001['f2eqf1_a0_coeff'] = 155.456141425652
IS_15473_1001['f2eqf1_a1_coeff'] = -62.4159468007929
IS_15473_1001['f2eqf1_a2_coeff'] = 10.572862781395
IS_15473_1001['f2eqf1_a3_coeff'] = -0.974118502758613
IS_15473_1001['f2eqf1_a4_coeff'] = 0.0527778625069939
IS_15473_1001['f2eqf1_a5_coeff'] = -0.00168495870404901
IS_15473_1001['f2eqf1_a6_coeff'] = 2.94099609801237e-05
IS_15473_1001['f2eqf1_a7_coeff'] = -2.1689610110201e-07
IS_15473_1001['f2eqf2_foc_low_lim'] = 23.91
IS_15473_1001['f2eqf2_foc_upper_lim'] = 92.51
IS_15473_1001['f2eqf2_a0_coeff'] = 0.708228661808233
IS_15473_1001['f2eqf2_a1_coeff'] = -0.0251942648277707
IS_15473_1001['f2eqf2_a2_coeff'] = 0.000994917874925799
IS_15473_1001['f2eqf2_a3_coeff'] = -1.46061580177157e-05
IS_15473_1001['f2eqf2_a4_coeff'] = 1.0470213175301e-07
IS_15473_1001['f2eqf2_a5_coeff'] = -2.94628257086522e-10
IS_15473_1001['f2eqf2_a6_coeff'] = 0
IS_15473_1001['f2eqf2_a7_coeff'] = 0

config['Equipment.Transducer.' + IS_TRANS[2]] = {}
config['Equipment.Transducer.' + IS_TRANS[2]]['Name'] = (IMASONIC +
                                                         ' 10 ch. PCD15473_01001 ROC 100 mm')
config['Equipment.Transducer.' + IS_TRANS[2]]['Manufacturer'] = IMASONIC
config['Equipment.Transducer.' + IS_TRANS[2]]['Elements'] = str(10)
config['Equipment.Transducer.' + IS_TRANS[2]]['Fund. freq.'] = str(300)  # [kHz]
config['Equipment.Transducer.' + IS_TRANS[2]]['Natural focus'] = str(100)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[2]]['Exit plane - first element dist.'] = str(7.3)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[2]]['Min. focus'] = str(IS_15473_1001['f2eqf1_foc_low_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[2]]['Max. focus'] = str(IS_15473_1001['f2eqf2_foc_upper_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[2]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IS_TRAN,
    'transducer_15473_10_300kHz.ini'))  # should be in the same directory as code
config['Equipment.Transducer.' + IS_TRANS[2]]['Active?'] = str(True)

IS_15473_1002 = {}
IS_15473_1002['p2a_a_coeff'] = 0.000109652030606
IS_15473_1002['p2a_b_coeff'] = -0.049100892347670
IS_15473_1002['df2sf_a_coeff'] = 0.985997294283070
IS_15473_1002['df2sf_b_coeff'] = 6.839965574252088
IS_15473_1002['f2eqf1_foc_low_lim'] = 11.81
IS_15473_1002['f2eqf1_foc_upper_lim'] = 23.19
IS_15473_1002['f2eqf1_a0_coeff'] = 215.873867616457
IS_15473_1002['f2eqf1_a1_coeff'] = -86.1814700183455
IS_15473_1002['f2eqf1_a2_coeff'] = 14.5225303056864
IS_15473_1002['f2eqf1_a3_coeff'] = -1.33371123213391
IS_15473_1002['f2eqf1_a4_coeff'] = 0.0721670489572786
IS_15473_1002['f2eqf1_a5_coeff'] = -0.00230487726262542
IS_15473_1002['f2eqf1_a6_coeff'] = 4.03049687566001e-05
IS_15473_1002['f2eqf1_a7_coeff'] = -2.9817886302987e-07
IS_15473_1002['f2eqf2_foc_low_lim'] = 23.19
IS_15473_1002['f2eqf2_foc_upper_lim'] = 94.63
IS_15473_1002['f2eqf2_a0_coeff'] = 0.74295672516508
IS_15473_1002['f2eqf2_a1_coeff'] = -0.0239057128267281
IS_15473_1002['f2eqf2_a2_coeff'] = 0.000765054513772272
IS_15473_1002['f2eqf2_a3_coeff'] = -8.34872753646803e-06
IS_15473_1002['f2eqf2_a4_coeff'] = 3.93567876712398e-08
IS_15473_1002['f2eqf2_a5_coeff'] = -5.44529271912347e-11
IS_15473_1002['f2eqf2_a6_coeff'] = 0
IS_15473_1002['f2eqf2_a7_coeff'] = 0

config['Equipment.Transducer.' + IS_TRANS[3]] = {}
config['Equipment.Transducer.' + IS_TRANS[3]]['Name'] = (IMASONIC +
                                                         ' 10 ch. PCD15473_01002 ROC 100 mm')
config['Equipment.Transducer.' + IS_TRANS[3]]['Manufacturer'] = IMASONIC
config['Equipment.Transducer.' + IS_TRANS[3]]['Elements'] = str(10)
config['Equipment.Transducer.' + IS_TRANS[3]]['Fund. freq.'] = str(300)  # [kHz]
config['Equipment.Transducer.' + IS_TRANS[3]]['Natural focus'] = str(100)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[3]]['Exit plane - first element dist.'] = str(7.3)  # [mm]
config['Equipment.Transducer.' + IS_TRANS[3]]['Min. focus'] = str(IS_15473_1002['f2eqf1_foc_low_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[3]]['Max. focus'] = str(IS_15473_1002['f2eqf2_foc_upper_lim'])  # [mm], wrt exit plane
config['Equipment.Transducer.' + IS_TRANS[3]]['Steer information'] = str(os.path.join(
    CONFIG_FILE_FOLDER_IS_TRAN,
    'transducer_15473_10_300kHz.ini'))  # should be in the same directory as code
config['Equipment.Transducer.' + IS_TRANS[3]]['Active?'] = str(True)

#######################################################################################
# Dummy tranducer
#######################################################################################

config['Equipment.Transducer.' + DUMMY] = {}
config['Equipment.Transducer.' + DUMMY]['Name'] = 'Dummy load'
config['Equipment.Transducer.' + DUMMY]['Manufacturer'] = ''
config['Equipment.Transducer.' + DUMMY]['Elements'] = str(0)
config['Equipment.Transducer.' + DUMMY]['Fund. freq.'] = str(0)  # [kHz]
config['Equipment.Transducer.' + DUMMY]['Natural focus'] = str(0)  # [mm]
config['Equipment.Transducer.' + DUMMY]['Exit plane - first element dist.'] = str(0)  # [mm] only for Imasonic
config['Equipment.Transducer.' + DUMMY]['Min. focus'] = str(0)  # [mm]
config['Equipment.Transducer.' + DUMMY]['Max. focus'] = str(1000)  # [mm]
config['Equipment.Transducer.' + DUMMY]['Steer information'] = ''
config['Equipment.Transducer.' + DUMMY]['Active?'] = str(False)

#######################################################################################
# Driving system - transducer combinations
#######################################################################################

# IGT-128-ch_comb_2x10-ch~IS_PCD15287_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['Driving system serial'] = (DS_TRAN_COMBOS[0]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['Transducer serial'] = (DS_TRAN_COMBOS[0]
                                                                             .split(COMBO_JOIN_SIGN)[1])

config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['P2A a-coeff'] = str(IS_15287_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['P2A b-coeff'] = str(IS_15287_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['DF2SF a-coeff'] = str(IS_15287_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['DF2SF b-coeff'] = str(IS_15287_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 foc. low lim.'] = str(IS_15287_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1001['f2eqf1_foc_upper_lim']) # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a0-coeff'] = str(IS_15287_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a1-coeff'] = str(IS_15287_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a2-coeff'] = str(IS_15287_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a3-coeff'] = str(IS_15287_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a4-coeff'] = str(IS_15287_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a5-coeff'] = str(IS_15287_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a6-coeff'] = str(IS_15287_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF1 a7-coeff'] = str(IS_15287_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 foc. low lim.'] = str(IS_15287_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a0-coeff'] = str(IS_15287_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a1-coeff'] = str(IS_15287_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a2-coeff'] = str(IS_15287_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a3-coeff'] = str(IS_15287_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a4-coeff'] = str(IS_15287_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a5-coeff'] = str(IS_15287_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a6-coeff'] = str(IS_15287_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[0]]['F2EQF2 a7-coeff'] = str(IS_15287_1001['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_2x10-ch~IS_PCD15287_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['Driving system serial'] = (DS_TRAN_COMBOS[1]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['Transducer serial'] = (DS_TRAN_COMBOS[1]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['P2A a-coeff'] = str(IS_15287_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['P2A b-coeff'] = str(IS_15287_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['DF2SF a-coeff'] = str(IS_15287_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['DF2SF b-coeff'] = str(IS_15287_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 foc. low lim.'] = str(IS_15287_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a0-coeff'] = str(IS_15287_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a1-coeff'] = str(IS_15287_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a2-coeff'] = str(IS_15287_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a3-coeff'] = str(IS_15287_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a4-coeff'] = str(IS_15287_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a5-coeff'] = str(IS_15287_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a6-coeff'] = str(IS_15287_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF1 a7-coeff'] = str(IS_15287_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 foc. low lim.'] = str(IS_15287_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a0-coeff'] = str(IS_15287_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a1-coeff'] = str(IS_15287_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a2-coeff'] = str(IS_15287_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a3-coeff'] = str(IS_15287_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a4-coeff'] = str(IS_15287_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a5-coeff'] = str(IS_15287_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a6-coeff'] = str(IS_15287_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[1]]['F2EQF2 a7-coeff'] = str(IS_15287_1002['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_2x10-ch~IS_PCD15473_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['Driving system serial'] = (DS_TRAN_COMBOS[2]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['Transducer serial'] = (DS_TRAN_COMBOS[2]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['P2A a-coeff'] = str(IS_15473_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['P2A b-coeff'] = str(IS_15473_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['DF2SF a-coeff'] = str(IS_15473_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['DF2SF b-coeff'] = str(IS_15473_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 foc. low lim.'] = str(IS_15473_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a0-coeff'] = str(IS_15473_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a1-coeff'] = str(IS_15473_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a2-coeff'] = str(IS_15473_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a3-coeff'] = str(IS_15473_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a4-coeff'] = str(IS_15473_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a5-coeff'] = str(IS_15473_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a6-coeff'] = str(IS_15473_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF1 a7-coeff'] = str(IS_15473_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 foc. low lim.'] = str(IS_15473_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a0-coeff'] = str(IS_15473_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a1-coeff'] = str(IS_15473_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a2-coeff'] = str(IS_15473_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a3-coeff'] = str(IS_15473_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a4-coeff'] = str(IS_15473_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a5-coeff'] = str(IS_15473_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a6-coeff'] = str(IS_15473_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[2]]['F2EQF2 a7-coeff'] = str(IS_15473_1001['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_2x10-ch~IS_PCD15473_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['Driving system serial'] = (DS_TRAN_COMBOS[3]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['Transducer serial'] = (DS_TRAN_COMBOS[3]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['P2A a-coeff'] = str(IS_15473_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['P2A b-coeff'] = str(IS_15473_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['DF2SF a-coeff'] = str(IS_15473_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['DF2SF b-coeff'] = str(IS_15473_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 foc. low lim.'] = str(IS_15473_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a0-coeff'] = str(IS_15473_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a1-coeff'] = str(IS_15473_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a2-coeff'] = str(IS_15473_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a3-coeff'] = str(IS_15473_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a4-coeff'] = str(IS_15473_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a5-coeff'] = str(IS_15473_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a6-coeff'] = str(IS_15473_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF1 a7-coeff'] = str(IS_15473_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 foc. low lim.'] = str(IS_15473_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a0-coeff'] = str(IS_15473_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a1-coeff'] = str(IS_15473_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a2-coeff'] = str(IS_15473_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a3-coeff'] = str(IS_15473_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a4-coeff'] = str(IS_15473_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a5-coeff'] = str(IS_15473_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a6-coeff'] = str(IS_15473_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[3]]['F2EQF2 a7-coeff'] = str(IS_15473_1002['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_1x10-ch~IS_PCD15287_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['Driving system serial'] = (DS_TRAN_COMBOS[4]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['Transducer serial'] = (DS_TRAN_COMBOS[4]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['P2A a-coeff'] = str(IS_15287_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['P2A b-coeff'] = str(IS_15287_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['DF2SF a-coeff'] = str(IS_15287_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['DF2SF b-coeff'] = str(IS_15287_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 foc. low lim.'] = str(IS_15287_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a0-coeff'] = str(IS_15287_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a1-coeff'] = str(IS_15287_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a2-coeff'] = str(IS_15287_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a3-coeff'] = str(IS_15287_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a4-coeff'] = str(IS_15287_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a5-coeff'] = str(IS_15287_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a6-coeff'] = str(IS_15287_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF1 a7-coeff'] = str(IS_15287_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 foc. low lim.'] = str(IS_15287_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a0-coeff'] = str(IS_15287_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a1-coeff'] = str(IS_15287_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a2-coeff'] = str(IS_15287_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a3-coeff'] = str(IS_15287_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a4-coeff'] = str(IS_15287_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a5-coeff'] = str(IS_15287_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a6-coeff'] = str(IS_15287_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[4]]['F2EQF2 a7-coeff'] = str(IS_15287_1001['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_1x10-ch~IS_PCD15287_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['Driving system serial'] = (DS_TRAN_COMBOS[5]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['Transducer serial'] = (DS_TRAN_COMBOS[5]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['P2A a-coeff'] = str(IS_15287_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['P2A b-coeff'] = str(IS_15287_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['DF2SF a-coeff'] = str(IS_15287_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['DF2SF b-coeff'] = str(IS_15287_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 foc. low lim.'] = str(IS_15287_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a0-coeff'] = str(IS_15287_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a1-coeff'] = str(IS_15287_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a2-coeff'] = str(IS_15287_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a3-coeff'] = str(IS_15287_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a4-coeff'] = str(IS_15287_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a5-coeff'] = str(IS_15287_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a6-coeff'] = str(IS_15287_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF1 a7-coeff'] = str(IS_15287_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 foc. low lim.'] = str(IS_15287_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a0-coeff'] = str(IS_15287_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a1-coeff'] = str(IS_15287_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a2-coeff'] = str(IS_15287_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a3-coeff'] = str(IS_15287_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a4-coeff'] = str(IS_15287_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a5-coeff'] = str(IS_15287_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a6-coeff'] = str(IS_15287_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[5]]['F2EQF2 a7-coeff'] = str(IS_15287_1002['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_1x10-ch~IS_PCD15473_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['Driving system serial'] = (DS_TRAN_COMBOS[6]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['Transducer serial'] = (DS_TRAN_COMBOS[6]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['P2A a-coeff'] = str(IS_15473_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['P2A b-coeff'] = str(IS_15473_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['DF2SF a-coeff'] = str(IS_15473_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['DF2SF b-coeff'] = str(IS_15473_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 foc. low lim.'] = str(IS_15473_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a0-coeff'] = str(IS_15473_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a1-coeff'] = str(IS_15473_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a2-coeff'] = str(IS_15473_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a3-coeff'] = str(IS_15473_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a4-coeff'] = str(IS_15473_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a5-coeff'] = str(IS_15473_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a6-coeff'] = str(IS_15473_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF1 a7-coeff'] = str(IS_15473_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 foc. low lim.'] = str(IS_15473_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a0-coeff'] = str(IS_15473_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a1-coeff'] = str(IS_15473_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a2-coeff'] = str(IS_15473_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a3-coeff'] = str(IS_15473_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a4-coeff'] = str(IS_15473_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a5-coeff'] = str(IS_15473_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a6-coeff'] = str(IS_15473_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[6]]['F2EQF2 a7-coeff'] = str(IS_15473_1001['f2eqf2_a7_coeff'])

# IGT-128-ch_comb_1x10-ch~IS_PCD15473_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['Driving system serial'] = (DS_TRAN_COMBOS[7]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['Transducer serial'] = (DS_TRAN_COMBOS[7]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['V2A a-coeff'] = str(IGT_128_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['V2A b-coeff'] = str(IGT_128_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['P2A a-coeff'] = str(IS_15473_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['P2A b-coeff'] = str(IS_15473_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['DF2SF a-coeff'] = str(IS_15473_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['DF2SF b-coeff'] = str(IS_15473_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 foc. low lim.'] = str(IS_15473_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a0-coeff'] = str(IS_15473_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a1-coeff'] = str(IS_15473_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a2-coeff'] = str(IS_15473_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a3-coeff'] = str(IS_15473_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a4-coeff'] = str(IS_15473_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a5-coeff'] = str(IS_15473_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a6-coeff'] = str(IS_15473_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF1 a7-coeff'] = str(IS_15473_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 foc. low lim.'] = str(IS_15473_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a0-coeff'] = str(IS_15473_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a1-coeff'] = str(IS_15473_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a2-coeff'] = str(IS_15473_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a3-coeff'] = str(IS_15473_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a4-coeff'] = str(IS_15473_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a5-coeff'] = str(IS_15473_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a6-coeff'] = str(IS_15473_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[7]]['F2EQF2 a7-coeff'] = str(IS_15473_1002['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_2x10-ch~IS_PCD15287_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['Driving system serial'] = (DS_TRAN_COMBOS[8]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['Transducer serial'] = (DS_TRAN_COMBOS[8]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['P2A a-coeff'] = str(IS_15287_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['P2A b-coeff'] = str(IS_15287_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['DF2SF a-coeff'] = str(IS_15287_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['DF2SF b-coeff'] = str(IS_15287_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 foc. low lim.'] = str(IS_15287_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a0-coeff'] = str(IS_15287_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a1-coeff'] = str(IS_15287_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a2-coeff'] = str(IS_15287_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a3-coeff'] = str(IS_15287_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a4-coeff'] = str(IS_15287_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a5-coeff'] = str(IS_15287_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a6-coeff'] = str(IS_15287_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF1 a7-coeff'] = str(IS_15287_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 foc. low lim.'] = str(IS_15287_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a0-coeff'] = str(IS_15287_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a1-coeff'] = str(IS_15287_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a2-coeff'] = str(IS_15287_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a3-coeff'] = str(IS_15287_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a4-coeff'] = str(IS_15287_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a5-coeff'] = str(IS_15287_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a6-coeff'] = str(IS_15287_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[8]]['F2EQF2 a7-coeff'] = str(IS_15287_1001['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_2x10-ch~IS_PCD15287_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['Driving system serial'] = (DS_TRAN_COMBOS[9]
                                                                                 .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['Transducer serial'] = (DS_TRAN_COMBOS[9]
                                                                             .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['P2A a-coeff'] = str(IS_15287_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['P2A b-coeff'] = str(IS_15287_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['DF2SF a-coeff'] = str(IS_15287_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['DF2SF b-coeff'] = str(IS_15287_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 foc. low lim.'] = str(IS_15287_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a0-coeff'] = str(IS_15287_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a1-coeff'] = str(IS_15287_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a2-coeff'] = str(IS_15287_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a3-coeff'] = str(IS_15287_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a4-coeff'] = str(IS_15287_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a5-coeff'] = str(IS_15287_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a6-coeff'] = str(IS_15287_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF1 a7-coeff'] = str(IS_15287_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 foc. low lim.'] = str(IS_15287_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a0-coeff'] = str(IS_15287_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a1-coeff'] = str(IS_15287_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a2-coeff'] = str(IS_15287_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a3-coeff'] = str(IS_15287_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a4-coeff'] = str(IS_15287_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a5-coeff'] = str(IS_15287_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a6-coeff'] = str(IS_15287_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[9]]['F2EQF2 a7-coeff'] = str(IS_15287_1002['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_2x10-ch~IS_PCD15473_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['Driving system serial'] = (DS_TRAN_COMBOS[10]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['Transducer serial'] = (DS_TRAN_COMBOS[10]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['P2A a-coeff'] = str(IS_15473_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['P2A b-coeff'] = str(IS_15473_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['DF2SF a-coeff'] = str(IS_15473_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['DF2SF b-coeff'] = str(IS_15473_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 foc. low lim.'] = str(IS_15473_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a0-coeff'] = str(IS_15473_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a1-coeff'] = str(IS_15473_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a2-coeff'] = str(IS_15473_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a3-coeff'] = str(IS_15473_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a4-coeff'] = str(IS_15473_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a5-coeff'] = str(IS_15473_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a6-coeff'] = str(IS_15473_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF1 a7-coeff'] = str(IS_15473_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 foc. low lim.'] = str(IS_15473_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a0-coeff'] = str(IS_15473_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a1-coeff'] = str(IS_15473_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a2-coeff'] = str(IS_15473_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a3-coeff'] = str(IS_15473_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a4-coeff'] = str(IS_15473_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a5-coeff'] = str(IS_15473_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a6-coeff'] = str(IS_15473_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[10]]['F2EQF2 a7-coeff'] = str(IS_15473_1001['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_2x10-ch~IS_PCD15473_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['Driving system serial'] = (DS_TRAN_COMBOS[11]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['Transducer serial'] = (DS_TRAN_COMBOS[11]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['P2A a-coeff'] = str(IS_15473_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['P2A b-coeff'] = str(IS_15473_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['DF2SF a-coeff'] = str(IS_15473_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['DF2SF b-coeff'] = str(IS_15473_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 foc. low lim.'] = str(IS_15473_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a0-coeff'] = str(IS_15473_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a1-coeff'] = str(IS_15473_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a2-coeff'] = str(IS_15473_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a3-coeff'] = str(IS_15473_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a4-coeff'] = str(IS_15473_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a5-coeff'] = str(IS_15473_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a6-coeff'] = str(IS_15473_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF1 a7-coeff'] = str(IS_15473_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 foc. low lim.'] = str(IS_15473_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a0-coeff'] = str(IS_15473_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a1-coeff'] = str(IS_15473_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a2-coeff'] = str(IS_15473_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a3-coeff'] = str(IS_15473_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a4-coeff'] = str(IS_15473_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a5-coeff'] = str(IS_15473_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a6-coeff'] = str(IS_15473_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[11]]['F2EQF2 a7-coeff'] = str(IS_15473_1002['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_1x10-ch~IS_PCD15287_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['Driving system serial'] = (DS_TRAN_COMBOS[12]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['Transducer serial'] = (DS_TRAN_COMBOS[12]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['P2A a-coeff'] = str(IS_15287_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['P2A b-coeff'] = str(IS_15287_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['DF2SF a-coeff'] = str(IS_15287_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['DF2SF b-coeff'] = str(IS_15287_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 foc. low lim.'] = str(IS_15287_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a0-coeff'] = str(IS_15287_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a1-coeff'] = str(IS_15287_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a2-coeff'] = str(IS_15287_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a3-coeff'] = str(IS_15287_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a4-coeff'] = str(IS_15287_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a5-coeff'] = str(IS_15287_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a6-coeff'] = str(IS_15287_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF1 a7-coeff'] = str(IS_15287_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 foc. low lim.'] = str(IS_15287_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a0-coeff'] = str(IS_15287_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a1-coeff'] = str(IS_15287_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a2-coeff'] = str(IS_15287_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a3-coeff'] = str(IS_15287_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a4-coeff'] = str(IS_15287_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a5-coeff'] = str(IS_15287_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a6-coeff'] = str(IS_15287_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[12]]['F2EQF2 a7-coeff'] = str(IS_15287_1001['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_1x10-ch~IS_PCD15287_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['Driving system serial'] = (DS_TRAN_COMBOS[13]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['Transducer serial'] = (DS_TRAN_COMBOS[13]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['P2A a-coeff'] = str(IS_15287_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['P2A b-coeff'] = str(IS_15287_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['DF2SF a-coeff'] = str(IS_15287_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['DF2SF b-coeff'] = str(IS_15287_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 foc. low lim.'] = str(IS_15287_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 foc. upper lim.'] = str(IS_15287_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a0-coeff'] = str(IS_15287_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a1-coeff'] = str(IS_15287_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a2-coeff'] = str(IS_15287_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a3-coeff'] = str(IS_15287_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a4-coeff'] = str(IS_15287_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a5-coeff'] = str(IS_15287_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a6-coeff'] = str(IS_15287_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF1 a7-coeff'] = str(IS_15287_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 foc. low lim.'] = str(IS_15287_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 foc. upper lim.'] = str(IS_15287_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a0-coeff'] = str(IS_15287_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a1-coeff'] = str(IS_15287_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a2-coeff'] = str(IS_15287_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a3-coeff'] = str(IS_15287_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a4-coeff'] = str(IS_15287_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a5-coeff'] = str(IS_15287_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a6-coeff'] = str(IS_15287_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[13]]['F2EQF2 a7-coeff'] = str(IS_15287_1002['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_1x10-ch~IS_PCD15473_01001
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['Driving system serial'] = (DS_TRAN_COMBOS[14]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['Transducer serial'] = (DS_TRAN_COMBOS[14]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['P2A a-coeff'] = str(IS_15473_1001['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['P2A b-coeff'] = str(IS_15473_1001['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['DF2SF a-coeff'] = str(IS_15473_1001['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['DF2SF b-coeff'] = str(IS_15473_1001['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 foc. low lim.'] = str(IS_15473_1001['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1001['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a0-coeff'] = str(IS_15473_1001['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a1-coeff'] = str(IS_15473_1001['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a2-coeff'] = str(IS_15473_1001['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a3-coeff'] = str(IS_15473_1001['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a4-coeff'] = str(IS_15473_1001['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a5-coeff'] = str(IS_15473_1001['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a6-coeff'] = str(IS_15473_1001['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF1 a7-coeff'] = str(IS_15473_1001['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 foc. low lim.'] = str(IS_15473_1001['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1001['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a0-coeff'] = str(IS_15473_1001['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a1-coeff'] = str(IS_15473_1001['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a2-coeff'] = str(IS_15473_1001['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a3-coeff'] = str(IS_15473_1001['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a4-coeff'] = str(IS_15473_1001['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a5-coeff'] = str(IS_15473_1001['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a6-coeff'] = str(IS_15473_1001['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[14]]['F2EQF2 a7-coeff'] = str(IS_15473_1001['f2eqf2_a7_coeff'])

# IGT-32-ch_comb_1x10-ch~IS_PCD15473_01002
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]] = {}
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['Driving system serial'] = (DS_TRAN_COMBOS[15]
                                                                                  .split(COMBO_JOIN_SIGN)[0])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['Transducer serial'] = (DS_TRAN_COMBOS[15]
                                                                              .split(COMBO_JOIN_SIGN)[1])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['V2A a-coeff'] = str(IGT_32_ch['v2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['V2A b-coeff'] = str(IGT_32_ch['v2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['P2A a-coeff'] = str(IS_15473_1002['p2a_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['P2A b-coeff'] = str(IS_15473_1002['p2a_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['DF2SF a-coeff'] = str(IS_15473_1002['df2sf_a_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['DF2SF b-coeff'] = str(IS_15473_1002['df2sf_b_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 foc. low lim.'] = str(IS_15473_1002['f2eqf1_foc_low_lim'])  # >=
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 foc. upper lim.'] = str(IS_15473_1002['f2eqf1_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a0-coeff'] = str(IS_15473_1002['f2eqf1_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a1-coeff'] = str(IS_15473_1002['f2eqf1_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a2-coeff'] = str(IS_15473_1002['f2eqf1_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a3-coeff'] = str(IS_15473_1002['f2eqf1_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a4-coeff'] = str(IS_15473_1002['f2eqf1_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a5-coeff'] = str(IS_15473_1002['f2eqf1_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a6-coeff'] = str(IS_15473_1002['f2eqf1_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF1 a7-coeff'] = str(IS_15473_1002['f2eqf1_a7_coeff'])

config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 foc. low lim.'] = str(IS_15473_1002['f2eqf2_foc_low_lim'])  # >
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 foc. upper lim.'] = str(IS_15473_1002['f2eqf2_foc_upper_lim'])  # <=
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a0-coeff'] = str(IS_15473_1002['f2eqf2_a0_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a1-coeff'] = str(IS_15473_1002['f2eqf2_a1_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a2-coeff'] = str(IS_15473_1002['f2eqf2_a2_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a3-coeff'] = str(IS_15473_1002['f2eqf2_a3_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a4-coeff'] = str(IS_15473_1002['f2eqf2_a4_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a5-coeff'] = str(IS_15473_1002['f2eqf2_a5_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a6-coeff'] = str(IS_15473_1002['f2eqf2_a6_coeff'])
config['Equipment.Combination.' + DS_TRAN_COMBOS[15]]['F2EQF2 a7-coeff'] = str(IS_15473_1002['f2eqf2_a7_coeff'])

with open(CONFIG_FILE, 'w') as configfile:
    config.write(configfile)
