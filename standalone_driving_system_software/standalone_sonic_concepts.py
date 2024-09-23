# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 14:27:56 2024

Author: ir. Margely Cornelissen, FUS Initiative, Radboud University

"""

# Sonic Concepts example
# Note: you can click on each parameter to get more information

##############################################################################
# initialize logging.
##############################################################################

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_sc"
logger = initialize_logger(log_dir, filename)

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

##############################################################################
# import the 'fus_driving_systems - sequence' into your code
##############################################################################

from fus_driving_systems import driving_system, transducer
from fus_driving_systems import sequence

##############################################################################
# create a sequence for a SC driving system
# a sequence can be created in advance and a new sequence can be defined
# later on in the code
##############################################################################

seq = sequence.Sequence()

# equipment
# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
seq.driving_sys = '203-035'
seq.driving_sys.connect_info = 'COM3'  # COM port the driving system is connected to

# set wait_for_trigger to true if you want to use trigger
seq.wait_for_trigger = True

# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
seq.transducer = 'CTX-250-009'

# set general parameters
seq.oper_freq = 250  # [kHz], operating frequency
seq.focus = 40  # [mm], focal depth
seq.global_power = 5  # [W], global power. NOTE: DIFFERENT THAN IGT

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.socsci.ru.nl/fusinitiative/tuscalculator/

# ## pulse ## #
seq.pulse_dur = 10  # [ms], pulse duration
seq.pulse_rep_int = 200  # [ms], pulse repetition interval

# pulse ramping
# to check available ramp shapes: print(seq.get_ramp_shapes())
# choose one ramp shape from that list as input
seq.pulse_ramp_shape = 'Rectangular - no ramping'

# ramping up and ramping down duration are equal and are equal to ramp duration
seq.pulse_ramp_dur = 0  # [ms], ramp duration

# ## pulse train ## #
# if you only want one pulse train, keep the values equal to the pulse repetition interval
seq.pulse_train_dur = 200  # [ms], pulse train duration

# to get a summary of your entered sequence: print(seq)
logger.info(f'The following sequence is used: {seq}')

##############################################################################
# connect with driving system and execute sequence
##############################################################################

# creating a SC driving system instance, connecting to it and sending your first sequence can be
# done when initializing your experiment. When appropriate, execute your sequence by implementing
# 'execute_sequence()' into your code.

# when you want to change your sequence in the middle of your experimental code, create a new
# sequence as above and send the new sequence: 'send_sequence()'. When appropriate, execute your
# sequence by implementing 'execute_sequence()' into your code.

# It is important to place your experimental code into a try-finally block, so if your code is
# stopped abruptly, the driving system will be disconnected. Otherwise, there is a change that it
# keeps on firing ultrasound sequences.

##############################################################################
# import the 'fus_driving_systems - ds' into your code
##############################################################################


from fus_driving_systems.sonic_concepts import sonic_concepts_ds

sc_ds = sonic_concepts_ds.SC()

try:
    sc_ds.connect(seq.driving_sys.connect_info)

    # you can check if the system is still connected by using the following:
    # print(sc_ds.is_connected())

    # optional: check if correct transducer is selected on driving system before continuining
    sc_ds.check_tran_sel()

    # If wait_for_trigger is true, only the sequence is sent and will be executed by the external trigger
    if seq.wait_for_trigger:
        sc_ds.send_sequence(seq)  # currently, triggermode is set to 1. Triggermode of 2 is not supported yet.
    
    # If wait_for_trigger is false, the sequence is sent and can be executed directly using the execute_sequence() function
    else:
        sc_ds.send_sequence(seq)
        sc_ds.execute_sequence()

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected automatically,
    # In the case your code is stopped abruptly, the driving system will be disconnected. Otherwise, there
    # is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not seq.wait_for_trigger:
        sc_ds.disconnect()
