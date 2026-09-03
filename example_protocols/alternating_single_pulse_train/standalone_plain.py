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

# IGT example: two protocols interleaved as one alternating group -- transducer A fires its
# pulse, then transducer B fires its pulse, then A again, and so on, for the whole duration
# below. This is "pulse train interleaving": each round still counts as one pulse train per
# transducer (a pulse plus its own off-time), just alternating instead of each transducer
# repeating its own full pulse train back-to-back before handing off to the other.
#
# This is NOT the only way to alternate between two transducers -- if your experiment instead
# fires transducer A's complete pulse train repetition, then reconfigures and fires transducer
# B's complete pulse train repetition (with real time in between, e.g. to reposition/re-plan),
# you don't need any of this: just call send_protocol()/execute_protocol() twice in a row, once
# per transducer. See ../switch_active_transducer/ for that pattern.
#
# See standalone_yaml.py in this same folder for the simpler, YAML-driven equivalent.
#
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

import sys

from fus_driving_systems.config.logging_config import initialize_logger
from fus_driving_systems.exceptions import FDSError

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

try:
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
    # your experiment (e.g. before sending a new protocol) won't tear down and recreate the
    # connection unnecessarily.
    igt_driving_sys.connect(ds_info.connect_info, log_dir, filename)

    # you can check if the system is still connected by using the following:
    # print(igt_driving_sys.is_connected())

    ##############################################################################
    # define both protocols
    ##############################################################################

    # When interleaving, each protocol contributes exactly one pulse per round of the alternating
    # group -- not a repeated pulse train of its own. pulse_dur/pulse_rep_int are what matter here
    # (pulse_rep_int decides how much of the shared round this protocol's own pulse occupies); every
    # other timing parameter (pulse_train_dur, pulse_train_rep_int, pulse_train_rep_dur) has no
    # effect in this mode and is left unset below, so it falls back to its own default rather than
    # being set to a value that's silently ignored.

    # to check available options for this driving system (no need to add a slot first):
    # print(protocol.get_focus_options()) / print(protocol.get_power_options())
    FOCUS_OPTION = 'Focus wrt exit plane [mm]'
    POWER_OPTION = 'Max. pressure in free water [MPa]'

    # Both protocols below use the same two, physically connected transducers -- defined once here
    # and reused for both, so a change to which transducer is used doesn't need to be repeated (and
    # can't accidentally drift apart between the two protocols).
    # to check available transducers: print(transducer.get_tran_serials())
    # choose transducers from that list as input
    TRANSDUCER_1 = 'IS_PCD15287_01001'
    TRANSDUCER_2 = 'IS_PCD15287_01002'

    # Ramping is a whole-group setting for the generator, not something each interleaved protocol
    # configures independently -- send_protocol() below only ever reads it from the first protocol
    # given (protocol_a), and exits with a clear error if the interleaved protocols don't all declare
    # the same values. Defined once here and reused for both protocols' own configure_timing() calls
    # below so they can never accidentally drift apart.
    RAMP_SHAPE = 'Tukey'
    RAMP_DUR = 5  # [ms], with at least 70 us between ramping up and down

    # Trigger configuration (trigger_option/n_triggers) is a call-level parameter of
    # IGT.wait_for_trigger() now, not of any one TUSProtocol (see TUSProtocol's own docstring for
    # why) -- there is exactly one trigger event for the whole interleaved group, so these live here
    # as plain variables instead of on either protocol, reused below when actually sending/waiting
    # on the group.
    TRIGGER_OPTION = 'TriggerWholeProtocol'
    N_TRIGGERS = None  # only applies (and is required) when TRIGGER_OPTION == 'TriggerOnePulseTrain'

    protocol_a = tus_protocol.TUSProtocol('IGT-32-ch_comb_2x10-ch')
    slot_a1 = protocol_a.add_slot(
        TRANSDUCER_1,
        FOCUS_OPTION, 40,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0.5,  # [MPa], maximum pressure in free water.
        oper_freq=300,  # [kHz], operating frequency
    )
    slot_a2 = protocol_a.add_slot(
        TRANSDUCER_2,
        FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0,  # [MPa], maximum pressure in free water.
        oper_freq=300,  # [kHz], operating frequency
    )
    protocol_a.configure_timing(
        pulse_dur=45,  # [ms], pulse duration
        pulse_ramp_shape=RAMP_SHAPE,
        pulse_ramp_dur=RAMP_DUR,
        pulse_rep_int=100,  # [ms], pulse repetition interval
    )

    # Ramping must match protocol_a's exactly (send_protocol() enforces this) -- reusing the same
    # RAMP_SHAPE/RAMP_DUR constants above, rather than repeating the values, makes that impossible to
    # get wrong by accident.
    protocol_b = tus_protocol.TUSProtocol('IGT-32-ch_comb_2x10-ch')
    slot_b1 = protocol_b.add_slot(
        TRANSDUCER_1,
        FOCUS_OPTION, 40,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0,  # [MPa], maximum pressure in free water.
        oper_freq=300,  # [kHz], operating frequency
    )
    slot_b2 = protocol_b.add_slot(
        TRANSDUCER_2,
        FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0.5,  # [MPa], maximum pressure in free water.
        oper_freq=300,  # [kHz], operating frequency
    )
    protocol_b.configure_timing(
        pulse_dur=45,  # [ms], pulse duration
        pulse_ramp_shape=RAMP_SHAPE,
        pulse_ramp_dur=RAMP_DUR,
        pulse_rep_int=100,  # [ms], pulse repetition interval
    )

    # How long the alternating group as a whole keeps repeating [ms]. Required whenever more than
    # one protocol is given -- there's no per-protocol fallback for this (unlike a single protocol,
    # which derives its own repetition count from its own pulse_train_rep_dur/pulse_train_rep_int).
    total_alternating_duration_ms = 80000

    ##############################################################################
    # send and execute the protocols
    ##############################################################################

    # sending the interleaved group, and executing it when appropriate, can be done when
    # initializing your experiment. When appropriate, execute it by implementing
    # 'execute_protocol()' into your code or by using the external trigger.

    try:
        igt_driving_sys.send_protocol([protocol_a, protocol_b], total_alternating_duration_ms)

        #igt_driving_sys.execute_protocol([protocol_a, protocol_b], total_alternating_duration_ms)

        # or even better wait for trigger
        igt_driving_sys.wait_for_trigger([protocol_a, protocol_b], TRIGGER_OPTION, N_TRIGGERS,
                                         total_alternating_duration_ms)

        # wait_for_trigger() above only arms the protocol to fire on the external trigger and
        # returns immediately -- it does NOT wait for, or check, the actual execution result. The
        # driving system only reports success/failure once the triggered execution is actually
        # finished, which can happen at an unpredictable moment later (whenever your external
        # trigger fires).
        #
        # Call wait_for_trigger_result() once you expect the trigger to have fired (or with a
        # generous timeout covering your full protocol) to block until completion and exit if the
        # driving system reports the execution failed. total_alternating_duration_ms above is reused
        # here since it already describes how long this triggered protocol is expected to take.
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
        # whether the protocol has finished. Your own loop condition (e.g. "still waiting on the
        # scanner") isn't necessarily tied to the protocol's actual completion, so disconnecting
        # right after such a loop can cut off a still-running protocol. If you use this pattern
        # instead of wait_for_trigger_result(), make sure you have your own way of confirming the
        # protocol actually finished (e.g. also call wait_for_trigger_result() once you expect it
        # to have) before disconnecting.
        igt_driving_sys.wait_for_trigger_result(timeout_s=total_alternating_duration_ms / 1000.0)

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

except FDSError as e:
    sys.exit(str(e))
