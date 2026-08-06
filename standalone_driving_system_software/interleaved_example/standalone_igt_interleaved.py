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

log_dir = "C:\\Temp"
filename = "standalone_igt"
logger = initialize_logger(log_dir, filename)

# This creates a timestamped session folder inside log_dir for this FDS log, and also enables
# crash detection (faulthandler) for the whole session -- both land in that same folder.
# igt_ds.IGT()/connect() below automatically discover and reuse it for the native IGT log too,
# so every log file from one session ends up together -- convenient for sharing a whole session
# at once (e.g. with IGT for a bug report, GitHub issue #126).

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

##############################################################################
# connect with the driving system
##############################################################################

# Connecting doesn't require a sequence to exist yet. In practice, you typically connect once
# when your experiment starts, then build/adapt sequences iteratively as it progresses -- so
# look up the driving system's connection info directly via DrivingSystem, rather than through
# a Sequence.

from fus_driving_systems import driving_system
from fus_driving_systems.igt import igt_ds

# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('IGT-32-ch_comb_2x10-ch')

igt_driving_sys = igt_ds.IGT(log_dir)

# connect() is a no-op (besides logging) if already connected, so calling it again later in
# your experiment (e.g. before sending a new sequence) won't tear down and recreate the
# connection unnecessarily.
igt_driving_sys.connect(ds_info.connect_info, log_dir, filename)

# you can check if the system is still connected by using the following:
# print(igt_driving_sys.is_connected())

##############################################################################
# first sequence collection
##############################################################################

from sequences import sequence_1_10_ch

seq1, seq2 = sequence_1_10_ch.create_sequence_collection(logger)

##############################################################################
# second sequence collection
##############################################################################

from sequences import sequence_17_26_ch

seq3, seq4 = sequence_17_26_ch.create_sequence_collection(logger)

total_duration_ms = 80000  # [ms]

##############################################################################
# send and execute the sequence
##############################################################################

# sending your first sequence, and executing it when appropriate, can be done when initializing
# your experiment. When appropriate, execute your sequence by implementing 'execute_sequence()'
# into your code or by using the external trigger.

# when you want to change your sequence in the middle of your experimental code, create a new
# sequence as above (the driving system is already connected, see above) and send the new
# sequence: 'send_sequence()'. When appropriate, execute your sequence by implementing
# 'execute_sequence()' into your code or by using the external trigger.

try:
    igt_driving_sys.send_sequence(seq1, seq2, seq3, seq4, total_duration_ms)

    #igt_driving_sys.execute_sequence(seq1, seq2, seq3, seq4, total_duration_ms)

    # or even better wait for trigger
    igt_driving_sys.wait_for_trigger(seq1, seq2, seq3, seq4, total_duration_ms)

    # wait_for_trigger() above only arms the sequence to fire on the external trigger and
    # returns immediately -- it does NOT wait for, or check, the actual execution result. The
    # driving system only reports success/failure once the triggered execution is actually
    # finished, which can happen at an unpredictable moment later (whenever your external
    # trigger fires).
    #
    # Call wait_for_trigger_result() once you expect the trigger to have fired (or with a
    # generous timeout covering your full protocol) to block until completion and exit if the
    # driving system reports the execution failed. total_duration_ms above is reused here since
    # it already describes how long this triggered protocol is expected to take.
    #
    # Note: an execution error is always logged immediately when it happens (regardless of when
    # you call this), but your code will only actively react to it (via sys.exit()) once
    # wait_for_trigger_result() is called -- calling it late means reacting late, even though
    # the failure itself was already recorded at the real time it occurred.
    #
    # If you have other work to do while waiting for the external trigger (e.g. waiting on
    # other equipment), use the non-blocking has_execution_error() instead, in your own polling
    # loop, for real-time reaction instead of only finding out at the end:
    #
    # while <your own condition, e.g. still waiting on the scanner>:
    #     if igt_driving_sys.has_execution_error() is not None:
    #         ...  # react immediately (log, stop other equipment, sys.exit(), ...)
    #     <do other work / short sleep>
    #
    # Note: has_execution_error() only tells you whether an error has occurred so far -- not
    # whether the sequence has finished. Your own loop condition (e.g. "still waiting on the
    # scanner") isn't necessarily tied to the sequence's actual completion, so disconnecting
    # right after such a loop can cut off a still-running sequence. If you use this pattern
    # instead of wait_for_trigger_result(), make sure you have your own way of confirming the
    # sequence actually finished (e.g. also call wait_for_trigger_result() once you expect it
    # to have) before disconnecting.
    igt_driving_sys.wait_for_trigger_result(timeout_s=total_duration_ms / 1000.0)

finally:
    # By the time we reach here, the sequence has actually finished executing either way:
    # execute_sequence() only returns once it's done, and wait_for_trigger_result() above
    # blocks until the triggered execution completes (or its timeout expires). So it's always
    # safe to disconnect here -- if your code stops abruptly before this point instead (like
    # a kernel death/crash), make sure to disconnect the driving system yourself, otherwise it
    # may keep firing ultrasound sequences.
    #
    # If you replaced wait_for_trigger_result() above with your own has_execution_error()
    # polling loop, this is only safe once you've confirmed the sequence actually finished --
    # see the note above.
    igt_driving_sys.disconnect()
