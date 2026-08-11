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

# Sonic Concepts example
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_sc_demo"
logger = initialize_logger(log_dir, filename)

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
from fus_driving_systems.sonic_concepts import sonic_concepts_ds

# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('203-035')
ds_info.connect_info = 'COM5'  # COM port the driving system is actually connected to on this machine

sc_ds = sonic_concepts_ds.SonicConcepts()
sc_ds.connect(ds_info.connect_info)

# you can check if the system is still connected by using the following:
# print(sc_ds.is_connected())

# optional: check if correct transducer is selected on driving system before continuining
sc_ds.check_tran_sel()

##############################################################################
# create a sequence for a SC driving system
# a sequence can be created in advance and a new sequence can be defined
# later on in the code
##############################################################################

from fus_driving_systems import sequence, transducer

# equipment: same driving system already used to connect() above
slow_seq = sequence.Sequence(ds_info.serial)

# send_sequence()/execute_sequence() automatically reconnect using slow_seq.driving_sys.connect_info
# if the connection ever drops -- propagate this machine's actual COM port onto the sequence's own
# driving system too (ds_info above is a separate object), so that automatic reconnect uses the
# right port instead of falling back to whatever ds_config.ini happens to default to.
slow_seq.driving_sys.connect_info = ds_info.connect_info

# add_slot() fully configures one transducer -- serial, focus, and power all at once (no
# partial/half-configured slot). This driving system currently supports only one transducer slot
# (see ds_info.max_tran_slots) -- add another add_slot() call for each additional transducer if a
# future SC driving system ever supports more.
# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
slow_slot = slow_seq.add_slot(
    'CTX-250-014',
    'Focus wrt exit plane [mm]', 40,  # [mm], focal depth
    'Global power [mW]', 15,  # [W], global power. NOTE: DIFFERENT THAN IGT
    oper_freq=250,  # [kHz], operating frequency
)

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.socsci.ru.nl/fusinitiative/tuscalculator/

# configure_timing() sets every pulse/pulse-train/trigger parameter together, in one call --
# it's the only way to set any of them (pulse_dur, pulse_rep_int, pulse_ramp_shape, ...,
# trigger_option, n_triggers all have getters only), precisely because they cascade/interact
# with each other and are prone to ordering hazards if set individually and out of order.
slow_seq.configure_timing(
    # ## pulse ## #
    pulse_dur=100,  # [ms], pulse duration

    # pulse ramping
    # to check available ramp shapes: print(slow_seq.get_ramp_shapes())
    # choose one ramp shape from that list as input
    pulse_ramp_shape='Rectangular - no ramping',
    # ramping up and ramping down duration are equal and are equal to ramp duration
    pulse_ramp_dur=0,  # [ms], ramp duration

    # ## pulse train ## #
    pulse_rep_int=1000,  # [ms], pulse repetition interval

    # if you only want one pulse train, you don't need to set this at all -- it defaults to
    # pulse_rep_int. Set explicitly here for clarity.
    pulse_train_dur=80000,  # [ms], pulse train duration

    # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. Use
    # 'None' (this template's default) to not use a trigger at all; 'TriggerOnePulseTrain' to fire
    # one pulse train per trigger received; 'TriggerWholeProtocol' to fire the entire, already
    # fully-timed sequence at once with a single trigger (equivalent to executing it directly,
    # just gated behind that one trigger). To check available trigger options:
    # print(slow_seq.get_trigger_options())
    trigger_option='None',
    # trigger_option='TriggerOnePulseTrain',
    # trigger_option='TriggerWholeProtocol'
)


#################################################################

# equipment: same driving system already used to connect() above
fast_seq = sequence.Sequence(ds_info.serial)

# send_sequence()/execute_sequence() automatically reconnect using fast_seq.driving_sys.connect_info
# if the connection ever drops -- propagate this machine's actual COM port onto the sequence's own
# driving system too (ds_info above is a separate object), so that automatic reconnect uses the
# right port instead of falling back to whatever ds_config.ini happens to default to.
fast_seq.driving_sys.connect_info = ds_info.connect_info

# add_slot() fully configures one transducer -- serial, focus, and power all at once (no
# partial/half-configured slot). This driving system currently supports only one transducer slot
# (see ds_info.max_tran_slots) -- add another add_slot() call for each additional transducer if a
# future SC driving system ever supports more.
# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
fast_slot = fast_seq.add_slot(
    'CTX-250-014',
    'Focus wrt exit plane [mm]', 40,  # [mm], focal depth
    'Global power [mW]', 15,  # [W], global power. NOTE: DIFFERENT THAN IGT
    oper_freq=250,  # [kHz], operating frequency
)

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.itrusst.com/tus-calculator

# configure_timing() sets every pulse/pulse-train/trigger parameter together, in one call --
# it's the only way to set any of them (pulse_dur, pulse_rep_int, pulse_ramp_shape, ...,
# trigger_option, n_triggers all have getters only), precisely because they cascade/interact
# with each other and are prone to ordering hazards if set individually and out of order.
fast_seq.configure_timing(
    # ## pulse ## #
    pulse_dur=0.1,  # [ms], pulse duration

    # pulse ramping
    # to check available ramp shapes: print(fast_seq.get_ramp_shapes())
    # choose one ramp shape from that list as input
    pulse_ramp_shape='Rectangular - no ramping',
    # ramping up and ramping down duration are equal and are equal to ramp duration
    pulse_ramp_dur=0,  # [ms], ramp duration

    # ## pulse train ## #
    pulse_rep_int=1,  # [ms], pulse repetition interval

    # if you only want one pulse train, you don't need to set this at all -- it defaults to
    # pulse_rep_int. Set explicitly here for clarity.
    pulse_train_dur=80000,  # [ms], pulse train duration

    # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. Use
    # 'None' (this template's default) to not use a trigger at all; 'TriggerOnePulseTrain' to fire
    # one pulse train per trigger received; 'TriggerWholeProtocol' to fire the entire, already
    # fully-timed sequence at once with a single trigger (equivalent to executing it directly,
    # just gated behind that one trigger). To check available trigger options:
    # print(fast_seq.get_trigger_options())
    trigger_option='None',
    # trigger_option='TriggerOnePulseTrain',
    # trigger_option='TriggerWholeProtocol'
)

##############################################################################
# send and execute the sequence
##############################################################################

# sending your first sequence, and executing it when appropriate, can be done when initializing
# your experiment. When appropriate, execute your sequence by implementing
# 'execute_sequence()' into your code.

# when you want to change your sequence in the middle of your experimental code, create a new
# sequence as above (the driving system is already connected, see above) and send the new
# sequence: 'send_sequence()'. When appropriate, execute your sequence by implementing
# 'execute_sequence()' into your code.

# It is important to place your experimental code into a try-finally block, so if your code is
# stopped abruptly, the driving system will be disconnected. Otherwise, there is a change that it
# keeps on firing ultrasound sequences.

try:
    # If wait_for_trigger is true, only the sequence is sent and will be executed by the external trigger
    if slow_seq.wait_for_trigger:
        sc_ds.send_sequence(slow_seq)  # currently, triggermode is set to 1. Triggermode of 2 is not supported yet.

    # If wait_for_trigger is false, the sequence is sent and can be executed directly using the execute_sequence() function
    else:
        sc_ds.send_sequence(slow_seq)
        sc_ds.execute_sequence(slow_seq)

        sc_ds.send_sequence(fast_seq)
        sc_ds.execute_sequence(fast_seq)

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected automatically,
    # In the case your code is stopped abruptly, the driving system will be disconnected. Otherwise, there
    # is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not slow_seq.wait_for_trigger:
        sc_ds.disconnect()
