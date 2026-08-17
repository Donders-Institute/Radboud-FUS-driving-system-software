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

# Sonic Concepts example: a single transducer, built directly in Python (full manual control --
# no YAML). See standalone_yaml.py in this same folder for the simpler, YAML-driven equivalent.
# See standalone_plain_demo.py (also in this folder) for sending two different protocols to the
# same driving system in sequence.
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_plain"
logger = initialize_logger(log_dir, filename)

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
from fus_driving_systems.sonic_concepts import sonic_concepts_ds

# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('105-010')
ds_info.connect_info = 'COM5'  # COM port the driving system is actually connected to on this machine

sc_ds = sonic_concepts_ds.SonicConcepts()
sc_ds.connect(ds_info.connect_info)

# you can check if the system is still connected by using the following:
# print(sc_ds.is_connected())

# optional: check if correct transducer is selected on driving system before continuining
sc_ds.check_tran_sel()

##############################################################################
# create a protocol for a SC driving system
# a protocol can be created in advance and a new protocol can be defined
# later on in the code
##############################################################################

from fus_driving_systems import tus_protocol, transducer

# equipment: same driving system already used to connect() above
protocol = tus_protocol.TUSProtocol(ds_info.serial)

# send_protocol()/execute_protocol() automatically reconnect using
# protocol.driving_sys.connect_info if the connection ever drops -- propagate this machine's
# actual COM port onto the protocol's own driving system too (ds_info above is a separate
# object), so that automatic reconnect uses the right port instead of falling back to whatever
# ds_config.ini happens to default to.
protocol.driving_sys.connect_info = ds_info.connect_info

# add_slot() fully configures one transducer -- serial, focus, and power all at once (no
# partial/half-configured slot). This driving system currently supports only one transducer slot
# (see ds_info.max_tran_slots) -- add another add_slot() call for each additional transducer if a
# future SC driving system ever supports more.
# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
# to check available focus/power options for this driving system (no need to add a slot first):
# print(protocol.get_focus_options()) / print(protocol.get_power_options())
slot = protocol.add_slot(
    'CTX-500-026',
    'Focus wrt exit plane [mm]', 40,  # [mm], focal depth
    'Global power [mW]', 2.5,  # [W], global power
    oper_freq=500,  # [kHz], operating frequency
)

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.itrusst.com/tus-calculator

# configure_timing() sets every pulse/pulse-train/trigger parameter together, in one call --
# it's the only way to set any of them (pulse_dur, pulse_rep_int, pulse_ramp_shape, ...,
# trigger_option, n_triggers all have getters only), precisely because they cascade/interact
# with each other and are prone to ordering hazards if set individually and out of order.
protocol.configure_timing(
    # ## pulse ## #
    pulse_dur=10,  # [ms], pulse duration

    # pulse ramping
    # to check available ramp shapes: print(protocol.get_ramp_shapes())
    # choose one ramp shape from that list as input
    pulse_ramp_shape='Rectangular - no ramping',
    # ramping up and ramping down duration are equal and are equal to ramp duration
    pulse_ramp_dur=0,  # [ms], ramp duration

    # ## pulse train ## #
    pulse_rep_int=50,  # [ms], pulse repetition interval -- one pulse every 50 ms

    # if you only want one pulse train, you don't need to set this at all -- it defaults to
    # pulse_rep_int. Set explicitly here for clarity.
    pulse_train_dur=200,  # [ms], pulse train duration -- 4 pulses per train (200 / 50)

    # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. For
    # SC specifically, this is effectively binary: send_protocol()/execute_protocol() only ever
    # check whether a trigger is expected at all (protocol.wait_for_trigger), never which kind --
    # so 'TriggerOnePulseTrain' has no meaningful effect over 'TriggerWholeProtocol' here. Unlike
    # IGT's own 'TriggerWholeProtocol' (one trigger arms every repetition at once), SC's driving
    # system waits for a fresh external trigger each time it needs to fire the pulse train.
    # 'None' (this template's default) means no trigger at all -- executed directly. To check
    # available trigger options:
    # print(protocol.get_trigger_options())
    trigger_option='None',
    # trigger_option='TriggerWholeProtocol'
)

# to get a summary of your entered protocol: print(protocol)
logger.info(f'The following protocol is used: {protocol}')

##############################################################################
# send and execute the protocol
##############################################################################

# sending your first protocol, and executing it when appropriate, can be done when initializing
# your experiment. When appropriate, execute your protocol by implementing
# 'execute_protocol()' into your code.

# when you want to change your protocol in the middle of your experimental code, create a new
# protocol as above (the driving system is already connected, see above) and send the new
# protocol: 'send_protocol()'. When appropriate, execute your protocol by implementing
# 'execute_protocol()' into your code.

# It is important to place your experimental code into a try-finally block, so if your code is
# stopped abruptly, the driving system will be disconnected. Otherwise, there is a change that it
# keeps on firing ultrasound protocols.

try:
    # If wait_for_trigger is true, only the protocol is sent and will be executed by the external trigger
    if protocol.wait_for_trigger:
        # currently, triggermode is set to 1. Triggermode of 2 is not supported yet.
        sc_ds.send_protocol(protocol)

    # If wait_for_trigger is false, the protocol is sent and can be executed directly using the execute_protocol() function
    else:
        sc_ds.send_protocol(protocol)
        sc_ds.execute_protocol(protocol)

finally:
    # When the protocol is executed using execute_protocol(), the system will be disconnected automatically,
    # In the case your code is stopped abruptly, the driving system will be disconnected. Otherwise, there
    # is a change that it keeps on firing ultrasound protocols.
    # When using the external trigger, disconnect the driving system yourself.
    if not protocol.wait_for_trigger:
        sc_ds.disconnect()
