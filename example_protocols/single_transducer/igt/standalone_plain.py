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

# IGT example: a single transducer, built directly in Python (full manual control -- no YAML).
# See standalone_direct_execute.py/standalone_wait_for_trigger.py/
# standalone_wait_for_trigger_poll.py in this same folder for the simpler, YAML-driven
# equivalents of the two execution patterns shown together below.
#
# Only one transducer connected? Use this script as-is. Two transducers firing together as part
# of the same protocol? See ../../two_transducers_simultaneous/ instead.
#
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_plain"
logger = initialize_logger(log_dir, filename)

# This creates a timestamped session folder inside log_dir (e.g. "2026-08-05_18-00-00_
# FDS_logs") for this FDS log, and also enables crash detection (faulthandler) for the whole
# session -- both land in that same folder. igt_ds.IGT()/connect() below automatically
# discover and reuse it for the native IGT log too, so every log file from one session ends up
# together -- convenient for sharing a whole session at once (e.g. with IGT for a bug report,
# GitHub issue #126).

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

##############################################################################
# connect with the driving system
##############################################################################

# Connecting doesn't require a protocol to exist yet. In practice, you typically connect once
# when your experiment starts, then build/adapt protocols iteratively as it progresses -- so
# look up the driving system's connection info directly via DrivingSystem, rather than through
# a TUSProtocol.

from fus_driving_systems import driving_system
from fus_driving_systems.igt import igt_ds

# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('IGT-32-ch_comb_2x10-ch')

igt_driving_sys = igt_ds.IGT(log_dir)

# connect() is a no-op (besides logging) if already connected, so calling it again later in
# your experiment (e.g. before sending a new protocol) won't tear down and recreate the
# connection unnecessarily.
igt_driving_sys.connect(ds_info.connect_info, log_dir, filename)

# you can check if the system is still connected by using the following:
# print(igt_driving_sys.is_connected())

##############################################################################
# create a protocol for an IGT driving system
# a protocol can be created in advance and a new protocol can be defined
# later on in the code
##############################################################################

from fus_driving_systems import tus_protocol, transducer

# equipment: same driving system already used to connect() above
protocol = tus_protocol.TUSProtocol(ds_info.serial)

# Each add_slot() call fully configures one transducer -- serial, focus, and power all at once
# (no partial/half-configured slot, and no separate available-channels check needed: that's
# enforced automatically once the driving system's expected number of slots have been added).
# NOTE: get_focus_options()/get_power_options() only tell you which option NAMES are valid --
# there is no equivalent lookup for valid VALUES. Pick sensible numbers yourself (add_slot()
# validates them once given, e.g. focus against the transducer's own min/max range).
# to check available options for this driving system (no need to add a slot first):
# print(protocol.get_focus_options()) / print(protocol.get_power_options())
# 'Focus wrt mid bowl [mm]'/'Voltage [V]'/'Amplitude [%]' are also valid options for IGT, but
# are configured as engineering-only by default.
FOCUS_OPTION = 'Focus wrt exit plane [mm]'
POWER_OPTION = 'Max. pressure in free water [MPa]'  # or 'Global power [mW]'

# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
slot1 = protocol.add_slot(
    'IS_PCD15287_01001',
    FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
    POWER_OPTION, 0.3,  # [MPa], maximum pressure in free water
    oper_freq=300,  # [kHz], operating frequency

    # Degree used to dephase every nth elemen based on chosen degree. None = no dephasing
    # One value (>0) is the degree of dephasing, for example [90] with 4 elements: 1 elem: 0
    # dephasing, 2 elem: 90 dephasing, 3 elem: 180 dephasing, 4 elem: 270 dephasing.
    # When the amount of values match the amount of elements, it will override the calculated
    # phases based on the set focus.
    dephasing_degree=None,  # [degrees]: None, [120] or [0, 135, 239, 90]
)

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.itrusst.com/tus-calculator

# configure_timing() sets every pulse/pulse-train/trigger parameter together, in one call --
# each individual setter (pulse_dur, pulse_rep_int, ...) cascades its own value forward to every
# level above it, so calling them one by one in the wrong order can silently overwrite an
# earlier one (e.g. setting pulse_train_dur before pulse_dur). Passing everything to
# configure_timing() at once avoids relying on any particular calling order.
protocol.configure_timing(
    # ## pulse ## #
    pulse_dur=10,  # [ms], pulse duration

    # pulse ramping
    # to check available ramp shapes: print(protocol.get_ramp_shapes())
    # choose one ramp shape from that list as input
    pulse_ramp_shape='Rectangular - no ramping',
    # ramping up and ramping down duration are equal and are equal to ramp duration
    pulse_ramp_dur=0,  # [ms], ramp duration, with at least 70 us between ramping up and down

    # ## pulse train ## #
    # Each field below is deliberately a genuinely different value from the one before it (not
    # just mirroring the level below), to show the full timing hierarchy in one place: one
    # pulse, repeated into a pulse train, itself repeated some number of times.
    pulse_rep_int=50,  # [ms], pulse repetition interval -- one pulse every 50 ms

    # if you only want one pulse train, you don't need to set this at all -- it defaults to
    # pulse_rep_int. Set explicitly here for clarity.
    pulse_train_dur=200,  # [ms], pulse train duration -- 4 pulses per train (200 / 50)

    # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. Use
    # 'None' (this template's default) to not use a trigger at all; 'TriggerOnePulseTrain' to
    # fire one pulse train per trigger received (you must also give n_triggers below -- how many
    # triggers to expect); 'TriggerWholeProtocol' to fire the entire, already fully-timed
    # protocol at once with a single trigger (equivalent to executing it directly, just gated
    # behind that one trigger). To check available trigger options:
    # print(protocol.get_trigger_options())
    trigger_option='None',
    # trigger_option='TriggerOnePulseTrain',
    # trigger_option='TriggerWholeProtocol'

    # Required when (and only settable when) trigger_option='TriggerOnePulseTrain' above --
    # pulse_train_rep_int/pulse_train_rep_dur don't apply in that mode at all (they apply to
    # every other trigger_option instead, may be given together or just one of the two).
    # n_triggers=4,  # number of triggers expected -- one pulse train fires per trigger

    # ## pulse train repetition ## #
    # if you only want one pulse train repetition, you don't need to set either of these at all --
    # pulse_train_rep_int defaults to pulse_train_dur, and pulse_train_rep_dur then defaults to
    # that (i.e. "repeat exactly once"). Set explicitly here for clarity.
    # a new train starts every 400 ms (200 ms train, then a 200 ms gap before the next)
    pulse_train_rep_int=400,  # [ms], pulse train repetition interval
    # keeps repeating for 2 s in total, i.e. 5 repetitions of the whole train (2000 / 400)
    pulse_train_rep_dur=2,  # [s], pulse train repetition duration
)

# to get a summary of your entered protocol: print(protocol)

##############################################################################
# send and execute the protocol
##############################################################################

# sending your first protocol, and executing it when appropriate, can be done when initializing
# your experiment. When appropriate, execute your protocol by implementing 'execute_protocol()'
# into your code or by using the external trigger.

# when you want to change your protocol in the middle of your experimental code, create a new
# protocol as above (the driving system is already connected, see above) and send the new
# protocol: 'send_protocol()'. When appropriate, execute your protocol by implementing
# 'execute_protocol()' into your code or by using the external trigger.

try:
    igt_driving_sys.send_protocol(protocol)

    # If wait_for_trigger is true, only the protocol is sent and will be executed by the external
    # trigger
    if protocol.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocol)

        # wait_for_trigger() above only arms the protocol to fire on the external trigger and
        # returns immediately -- it does NOT wait for, or check, the actual execution result.
        # The driving system only reports success/failure once the triggered execution is
        # actually finished, which can happen at an unpredictable moment later (whenever your
        # external trigger fires).
        #
        # Call wait_for_trigger_result() once you expect the trigger to have fired (or with a
        # generous timeout covering your full protocol) to block until completion and exit if
        # the driving system reports the execution failed. Adjust the timeout below to match
        # how long your triggered protocol is expected to take. See
        # standalone_wait_for_trigger.py in this same folder for this pattern on its own.
        #
        # Note: an execution error is always logged immediately when it happens (regardless of
        # when you call this), but your code will only actively react to it (via sys.exit())
        # once wait_for_trigger_result() is called -- calling it late means reacting late, even
        # though the failure itself was already recorded at the real time it occurred.
        #
        # If you have other work to do while waiting for the external trigger (e.g. waiting on
        # other equipment), use the non-blocking has_execution_error() instead, in your own
        # polling loop, for real-time reaction instead of only finding out at the end -- see
        # standalone_wait_for_trigger_poll.py in this same folder for this pattern on its own.
        igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)

    # If wait_for_trigger is false, the protocol is sent and can be executed directly using the
    # execute_protocol() function -- see standalone_direct_execute.py in this same folder for
    # this pattern on its own.
    else:
        igt_driving_sys.execute_protocol(protocol)

finally:
    # By the time we reach here, the protocol has actually finished executing either way:
    # execute_protocol() only returns once it's done, and wait_for_trigger_result() above
    # blocks until the triggered execution completes (or its timeout expires). So it's always
    # safe to disconnect here -- if your code stops abruptly before this point instead (like
    # a kernel death/crash), make sure to disconnect the driving system yourself, otherwise it
    # may keep firing ultrasound protocols.
    #
    # If you replaced wait_for_trigger_result() above with your own has_execution_error()
    # polling loop, this is only safe once you've confirmed the protocol actually finished --
    # see the note above.
    igt_driving_sys.disconnect()
