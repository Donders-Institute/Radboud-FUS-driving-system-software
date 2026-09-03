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

# IGT example: two transducers, both part of the SAME protocol -- they fire together, at the
# same time, not alternating (see ../alternating_single_pulse_train/ instead for that). Built
# directly in Python (full manual control -- no YAML). See standalone_yaml.py in this same
# folder for the simpler, YAML-driven equivalent.
#
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

import sys

from fus_driving_systems.config.logging_config import initialize_logger
from fus_driving_systems.exceptions import FDSError

log_dir = "C://Temp"
filename = "standalone_plain"
logger = initialize_logger(log_dir, filename)

try:
    ##############################################################################
    # connect with the driving system
    ##############################################################################

    from fus_driving_systems import driving_system
    from fus_driving_systems.igt import igt_ds

    # to check available driving systems: print(driving_system.get_ds_serials())
    # choose one driving system from that list as input
    ds_info = driving_system.DrivingSystem()
    ds_info.set_ds_info('IGT-32-ch_comb_2x10-ch')

    igt_driving_sys = igt_ds.IGT(log_dir)
    igt_driving_sys.connect(ds_info.connect_info, log_dir, filename)

    ##############################################################################
    # create a protocol for two transducers on an IGT driving system
    ##############################################################################

    from fus_driving_systems import tus_protocol, transducer

    # equipment: same driving system already used to connect() above
    protocol = tus_protocol.TUSProtocol(ds_info.serial)

    # to check available options for this driving system (no need to add a slot first):
    # print(protocol.get_focus_options()) / print(protocol.get_power_options())
    FOCUS_OPTION = 'Focus wrt exit plane [mm]'
    POWER_OPTION = 'Max. pressure in free water [MPa]'  # or 'Global power [mW]'

    # Each add_slot() call fully configures one transducer -- serial, focus, and power all at once.
    # As many slots as this driving system's config allows (see ds_info.max_tran_slots) -- 2 here.
    # to check available transducers: print(transducer.get_tran_serials())
    slot1 = protocol.add_slot(
        'IS_PCD15287_01001',
        FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0.3,  # [MPa], maximum pressure in free water
        oper_freq=300,  # [kHz], operating frequency
    )
    slot2 = protocol.add_slot(
        'IS_PCD15287_01002',
        FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0.3,  # [MPa], maximum pressure in free water
        oper_freq=300,  # [kHz], operating frequency
    )

    # Trigger configuration (trigger_option/n_triggers) is a call-level parameter of
    # IGT.wait_for_trigger(), not an attribute of the protocol itself -- defined here as plain
    # variables instead, reused below when actually sending/waiting for a trigger/executing.
    # Use 'None' (this template's default) to not use a trigger at all; 'TriggerOnePulseTrain' to
    # fire one pulse train per trigger received (you must also give N_TRIGGERS below); or
    # 'TriggerWholeProtocol' to fire the
    # entire, already fully-timed protocol at once with a single trigger. To check available trigger
    # options: print(igt_driving_sys.get_trigger_options())
    TRIGGER_OPTION = 'None'
    # TRIGGER_OPTION = 'TriggerOnePulseTrain'
    # TRIGGER_OPTION = 'TriggerWholeProtocol'

    # Only applies (and is required) when TRIGGER_OPTION == 'TriggerOnePulseTrain' above.
    N_TRIGGERS = None  # e.g. 4 -- number of triggers expected, one pulse train fires per trigger

    # configure_timing() sets every pulse/pulse-train parameter together, in one call -- it's the
    # only way to set any of them, precisely because they cascade/interact with each other and are
    # prone to ordering hazards if set individually and out of order. Applies once, to the whole
    # protocol -- both slots above fire together, on this same timing.
    protocol.configure_timing(
        # Each field below is deliberately a genuinely different value from the one before it (not
        # just mirroring the level below), to show the full timing hierarchy in one place: one
        # pulse, repeated into a pulse train, itself repeated some number of times.
        pulse_dur=10,  # [ms], pulse duration
        pulse_ramp_shape='Rectangular - no ramping',
        pulse_ramp_dur=0,  # [ms], ramp duration
        pulse_rep_int=50,  # [ms], pulse repetition interval -- one pulse every 50 ms
        pulse_train_dur=200,  # [ms], pulse train duration -- 4 pulses per train (200 / 50)

        # a new train starts every 400 ms (200 ms train, then a 200 ms gap before the next)
        pulse_train_rep_int=400,  # [ms]
        # keeps repeating for 2 s in total, i.e. 5 repetitions of the whole train (2000 / 400)
        pulse_train_rep_dur=2,  # [s]
    )

    ##############################################################################
    # send and execute the protocol
    ##############################################################################

    try:
        igt_driving_sys.send_protocol(protocol)

        # If a trigger is configured (TRIGGER_OPTION != 'None'), only the protocol is sent and will
        # be executed by the external trigger. If not (this template's default), the protocol is
        # sent and can be executed directly using execute_protocol(). See
        # ../single_transducer/igt/standalone_wait_for_trigger.py/standalone_wait_for_trigger_poll.py
        # for the full wait_for_trigger_result()/has_execution_error() explanation this pattern
        # relies on.
        if TRIGGER_OPTION != 'None':
            igt_driving_sys.wait_for_trigger(protocol, TRIGGER_OPTION, N_TRIGGERS)
            igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)
        else:
            igt_driving_sys.execute_protocol(protocol)
    finally:
        # Always safe to disconnect here -- execute_protocol()/wait_for_trigger_result() only
        # return once it's done. If your code stops abruptly before this point (e.g. a crash),
        # disconnect the driving system yourself, otherwise it may keep firing ultrasound protocols.
        igt_driving_sys.disconnect()

except FDSError as e:
    sys.exit(str(e))
