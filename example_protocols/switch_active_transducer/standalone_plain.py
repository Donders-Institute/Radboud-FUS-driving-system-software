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

# IGT example: two physically connected transducers, only one of which is actually active at a
# time -- switched mid-experiment by reconfiguring the SAME protocol's slots via
# slot.configure(). Slot 1 starts active (real press) and slot 2 off (press=0); later, 
# slot.configure() swaps that around on both slots at once, and the protocol is re-sent so the
# driving system actually picks up the change before executing again.
#
# There is no interleaving API involved here at all -- send_protocol()/execute_protocol() are
# each called twice, once before and once after the switch. See
# ../alternating_single_pulse_train/ instead if you actually want both transducers to alternate
# pulse-by-pulse within one shared execution.
#
# See standalone_yaml.py in this same folder for the YAML-driven equivalent of the initial
# configuration -- the runtime slot.configure() switch below still happens in Python either way,
# since it's an imperative, mid-script action a static declarative file can't express.
#
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C:\\Temp"
filename = "standalone_plain"
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

# Connecting doesn't require a protocol to exist yet. In practice, you typically connect once
# when your experiment starts, then build/adapt protocols iteratively as it progresses -- so
# look up the driving system's connection info directly via DrivingSystem, rather than through
# a TUSProtocol.

from fus_driving_systems import driving_system, transducer
from fus_driving_systems import tus_protocol
from fus_driving_systems.igt import igt_ds

# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('IGT-32-ch_comb_2x10-ch')

igt_driving_sys = igt_ds.IGT(log_dir)

# connect() is a no-op (besides logging) if already connected, so calling it again later in
# your experiment (e.g. before re-sending the reconfigured protocol below) won't tear down and
# recreate the connection unnecessarily.
igt_driving_sys.connect(ds_info.connect_info, log_dir, filename)

# you can check if the system is still connected by using the following:
# print(igt_driving_sys.is_connected())

##############################################################################
# protocol -- transducer 1 active, transducer 2 off
##############################################################################

# to check available options for this driving system (no need to add a slot first):
# print(protocol.get_focus_options()) / print(protocol.get_power_options())
FOCUS_OPTION = 'Focus wrt exit plane [mm]'
POWER_OPTION = 'Max. pressure in free water [MPa]'

# Both transducers below are physically connected for the whole session -- defined once here so
# the transducer_1/transducer_2 mapping used in the switch further down can't drift apart from
# the one used here.
# to check available transducers: print(transducer.get_tran_serials())
# choose transducers from that list as input
TRANSDUCER_1 = 'IS_PCD15287_01001'
TRANSDUCER_2 = 'IS_PCD15287_01002'
ACTIVE_PRESS = 0.5  # [MPa], maximum pressure in free water for whichever transducer is active
INACTIVE_PRESS = 0  # [MPa], off -- physically connected, but not firing

protocol = tus_protocol.TUSProtocol('IGT-32-ch_comb_2x10-ch')
slot1 = protocol.add_slot(
    TRANSDUCER_1,
    FOCUS_OPTION, 40,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
    POWER_OPTION, ACTIVE_PRESS,
    oper_freq=300,  # [kHz], operating frequency
)
slot2 = protocol.add_slot(
    TRANSDUCER_2,
    FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
    POWER_OPTION, INACTIVE_PRESS,
    oper_freq=300,  # [kHz], operating frequency
)

# configure_timing() only requires pulse_dur -- every other parameter here could be left out and
# would fall back to a sensible default (see its own docstring). They're all given explicitly
# below instead, each set to a genuinely different value (not just mirroring the level below
# it), to show the full timing hierarchy in one place: one pulse, repeated into a pulse train,
# itself repeated some number of times.
protocol.configure_timing(
    pulse_dur=45,  # [ms], pulse duration
    pulse_ramp_shape='Rectangular - no ramping',
    pulse_rep_int=100,  # [ms], pulse repetition interval -- one pulse every 100 ms
    pulse_train_dur=500,  # [ms], pulse train duration -- 5 pulses per train (500 / 100)
    # [ms], pulse train repetition interval -- a new train starts every 1000 ms (500 ms train,
    # then a 500 ms gap before the next one starts)
    pulse_train_rep_int=1000,
    # [s], pulse train repetition duration -- keeps repeating for 5 s in total, i.e. 5
    # repetitions of the whole train (5000 ms / 1000 ms)
    pulse_train_rep_dur=5,

    # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. Use
    # 'None' (this template's default) to not use a trigger at all; 'TriggerOnePulseTrain' to
    # fire one pulse train per trigger received (you must also give n_triggers below); or
    # 'TriggerWholeProtocol' to fire the entire, already fully-timed protocol at once with a
    # single trigger. To check available trigger options: print(protocol.get_trigger_options())
    trigger_option='None',
    # trigger_option='TriggerOnePulseTrain',
    # trigger_option='TriggerWholeProtocol'
)

# It is important to place your experimental code into a try-finally block, so if your code is
# stopped abruptly, the driving system will be disconnected. Otherwise, there is a chance that
# it keeps on firing ultrasound protocols.
try:
    igt_driving_sys.send_protocol(protocol)

    # If wait_for_trigger is true, only the protocol is sent and will be executed by the
    # external trigger. If false (this template's default), the protocol is sent and can be
    # executed directly using execute_protocol(). See
    # ../single_transducer/igt/standalone_wait_for_trigger.py/standalone_wait_for_trigger_poll.py
    # for the full wait_for_trigger_result()/has_execution_error() explanation this pattern
    # relies on.
    if protocol.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocol)
        igt_driving_sys.wait_for_trigger_result(protocol.buffer_num, timeout_s=5.0)
    else:
        igt_driving_sys.execute_protocol(protocol)

    ##########################################################################
    # ... later in your experiment: switch which transducer is active ...
    ##########################################################################

    # slot.configure() changes an already-added slot's focus/power in place -- no new protocol,
    # no new slots, just the same two transducers with their power values swapped. Focus stays
    # the same here (still the current slot value), only power changes.
    slot1.configure(FOCUS_OPTION, slot1.focus_wrt_exit_plane, POWER_OPTION, INACTIVE_PRESS)
    slot2.configure(FOCUS_OPTION, slot2.focus_wrt_exit_plane, POWER_OPTION, ACTIVE_PRESS)

    # The driving system already has the OLD configuration loaded -- send_protocol() must be
    # called again so it picks up what slot.configure() just changed above.
    igt_driving_sys.send_protocol(protocol)
    if protocol.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocol)
        igt_driving_sys.wait_for_trigger_result(protocol.buffer_num, timeout_s=5.0)
    else:
        igt_driving_sys.execute_protocol(protocol)

finally:
    # By the time we reach here, the protocol has actually finished executing either way:
    # execute_protocol()/wait_for_trigger_result() only return once it's done. So it's always
    # safe to disconnect here -- if your code stops abruptly before this point instead (like a
    # kernel death/crash), make sure to disconnect the driving system yourself, otherwise it may
    # keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
