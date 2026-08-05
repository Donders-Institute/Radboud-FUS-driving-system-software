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

# IGT example
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_igt"
logger = initialize_logger(log_dir, filename)

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

##############################################################################
# create a sequence for an IGT driving system
# a sequence can be created in advance and a new sequence can be defined
# later on in the code
##############################################################################

import sys

from fus_driving_systems import driving_system, sequence, transducer
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.utils import get_config_value

seq1 = sequence.Sequence()

# Number of sequence starting at zero. Currently only used to differentiate and send multiple
# sequences to the IGT system. Only 0 and 1 are possible. Don't change this value if you only
# using one sequence definition.
seq1.seq_num = 0

# equipment
# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
seq1.driving_sys = 'IGT-32-ch_comb_2x10-ch'
use_two_transducers = True  # is true if you are using two transducers simulateneously or interleaved

# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
seq1.transducer = 'IS_PCD15287_01001'

# set general parameters
seq1.oper_freq = 300  # [kHz], operating frequency

# NOTE: Due to compensation equations, the focus has to be set first when using amplitude or
# voltage as power input.
seq1.focus_wrt_exit_plane = 80  # [mm], focal depth w.r.t. the exit plane and FWHM middle
# seq1.focus_wrt_mid_bowl = 69.1  # [mm], focal depth w.r.t. the radiating surface and FWHM middle

# Degree used to dephase every nth elemen based on chosen degree. None = no dephasing
# One value (>0) is the degree of dephasing, for example [90] with 4 elements: 1 elem: 0 dephasing,
# 2 elem: 90 dephasing, 3 elem: 180 dephasing, 4 elem: 270 dephasing.
# When the amount of values match the amount of elements, it will override the calculated phases
# based on the set focus.
seq1.dephasing_degree = None  # [degrees]: None, [120] or [0, 135, 239, 90]

# Set maximum pressure in free water [MPa]. NOTE: DIFFERENT THAN SC
seq1.press = 0.3  # [MPa], maximum pressure in free water

seq2 = None  # seq2 is None of a second transducer isn't used
if use_two_transducers:
    seq2 = sequence.Sequence()

    seq2.driving_sys = seq1.driving_sys.serial

    # to check available transducers: print(transducer.get_tran_serials())
    # choose one transducer from that list as input
    seq2.transducer = 'IS_PCD15287_01002'

    # Check if available channels is equal to the number of elements of the transducers combined
    n_comb_elem = seq1.transducer.elements + seq2.transducer.elements
    if seq1.driving_sys.available_ch != n_comb_elem:
        logger.error(f'Number of available channels ({seq1.driving_sys.available_ch}) is not ' +
                     f'equal to the number of elements of the transducers combined ({n_comb_elem}' +
                     f'). Equipment configuration {seq1.driving_sys.name} - ' +
                     f'{seq1.transducer.name} & {seq2.transducer.name} does ' +
                     'not seem to be compatible or use_two_transducers is incorrectly True.')
        sys.exit()

    # set general parameters
    seq2.oper_freq = 300  # [kHz], operating frequency

    # NOTE: Due to compensation equations, the focus has to be set first when using amplitude or
    # voltage as power input.
    seq2.focus_wrt_exit_plane = 80  # [mm], focal depth w.r.t. the exit plane and FWHM middle
    # seq2.focus_wrt_mid_bowl = 69.1  # [mm], focal depth w.r.t. the radiating surface and FWHM middle

    # Degree used to dephase every nth element based on chosen degree. None = no dephasing
    # One value (>0) is the degree of dephasing, for example [90] with 4 elements: 1 elem: 0
    # dephasing. 2 elem: 90 dephasing, 3 elem: 180 dephasing, 4 elem: 270 dephasing.
    # When the amount of values match the amount of elements, it will override the calculated phases
    # based on the set focus.
    seq2.dephasing_degree = None  # [degrees]: None, [120] or [0, 135, 239, 90]

    # Set maximum pressure in free water [MPa]. NOTE: DIFFERENT THAN SC
    seq2.press = 0.3  # [MPa], maximum pressure in free water

# Check if available channels is equal to the number of elements of the transducer
elif seq1.driving_sys.available_ch != seq1.transducer.elements:
    logger.error(f'Number of available channels ({seq1.driving_sys.available_ch}) is not equal to' +
                 f' the number of elements of the transducer ({seq1.transducer.elements}). ' +
                 f'Equipment configuration {seq1.driving_sys.name} - {seq1.transducer.name} does ' +
                 'not seem to be compatible or use_two_transducers is incorrectly False.')
    sys.exit()

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.socsci.ru.nl/fusinitiative/tuscalculator/

# ## pulse ## #
seq1.pulse_dur = 10  # [ms], pulse duration
seq1.pulse_rep_int = 200  # [ms], pulse repetition interval

# pulse ramping
# to check available ramp shapes: print(seq1.get_ramp_shapes())
# choose one ramp shape from that list as input
seq1.pulse_ramp_shape = 'Rectangular - no ramping'

# ramping up and ramping down duration are equal and are equal to ramp duration
seq1.pulse_ramp_dur = 0  # [ms], ramp duration, with at least 70 us between ramping up and down

# ## pulse train ## #
# if you only want one pulse train, keep the values equal to the pulse repetition interval
seq1.pulse_train_dur = 200  # [ms], pulse train duration

# set wait_for_trigger to true if you want to use trigger
seq1.wait_for_trigger = False

# When you only want to trigger a pulse train repetition once: 'TriggerOnePulseTrainRepetition'
# Multiple times triggering a pulse train repetition isn't supported.
# to check available trigger options: print(seq1.get_trigger_options())
seq1.trigger_option = 'TriggerSequence'
if seq1.wait_for_trigger and seq1.trigger_option == get_config_value(logger, config, 'Trigger',
                                                                     'option.seq',
                                                                     'TriggerSequence'):
    seq1.n_triggers = 4  # number of timings above defined sequence will be triggered

else:
    seq1.pulse_train_rep_int = 200  # [ms], pulse train repetition interval, NOTE: DIFFERENT THAN SC

    # ## pulse train repetition ## #
    # if you only want one pulse train, keep the value equal to the pulse repetition interval
    # if you only want one pulse train repetition block, keep the value equal to the pulse train
    # repetition interval
    seq1.pulse_train_rep_dur = 2  # [s], pulse train repetition duration, NOTE: DIFFERENT THAN SC

# to get a summary of your entered sequence: print(seq1)

##############################################################################
# connect with driving system and execute sequence
##############################################################################

# creating an IGT driving system instance, connecting to it and sending your first sequence can be
# done when initializing your experiment. When appropriate, execute your sequence by implementing
# 'execute_sequence()' into your code or by using the external trigger.

# when you want to change your sequence in the middle of your experimental code, create a new
# sequence as above and send the new sequence: 'send_sequence()'. When appropriate, execute your
# sequence by implementing 'execute_sequence()' into your code or by using the external trigger.

##############################################################################
# connect with the driving system
##############################################################################

from fus_driving_systems.igt import igt_ds

igt_driving_sys = igt_ds.IGT(log_dir)

try:
    igt_driving_sys.connect(seq1.driving_sys.connect_info, log_dir, filename)

    # you can check if the system is still connected by using the following:
    # print(igt_ds.is_connected())

    igt_driving_sys.send_sequence(seq1, seq2)

    # If wait_for_trigger is true, only the sequence is sent and will be executed by the external
    # trigger
    if seq1.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(seq1, seq2)

        # wait_for_trigger() above only arms the sequence to fire on the external trigger and
        # returns immediately -- it does NOT wait for, or check, the actual execution result.
        # The driving system only reports success/failure once the triggered execution is
        # actually finished, which can happen at an unpredictable moment later (whenever your
        # external trigger fires).
        #
        # Call wait_for_trigger_result() once you expect the trigger to have fired (or with a
        # generous timeout covering your full protocol) to block until completion and exit if
        # the driving system reports the execution failed. Adjust the timeout below to match
        # how long your triggered sequence is expected to take.
        #
        # Note: an execution error is always logged immediately when it happens (regardless of
        # when you call this), but your code will only actively react to it (via sys.exit())
        # once wait_for_trigger_result() is called -- calling it late means reacting late, even
        # though the failure itself was already recorded at the real time it occurred.
        #
        # If you have other work to do while waiting for the external trigger (e.g. waiting on
        # other equipment), use the non-blocking has_execution_error() instead, in your own
        # polling loop, for real-time reaction instead of only finding out at the end:
        #
        # while <your own condition, e.g. still waiting on the scanner>:
        #     if igt_driving_sys.has_execution_error() is not None:
        #         ...  # react immediately (log, stop other equipment, sys.exit(), ...)
        #     <do other work / short sleep>
        igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)

    # If wait_for_trigger is false, the sequence is sent and can be executed directly using the
    # execute_sequence() function
    else:
        igt_driving_sys.execute_sequence(seq1, seq2)

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected
    # automatically. In the case your code is stopped abruptly, the driving system will be
    # disconnected. Otherwise, there is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not seq1.wait_for_trigger:
        igt_driving_sys.disconnect()
