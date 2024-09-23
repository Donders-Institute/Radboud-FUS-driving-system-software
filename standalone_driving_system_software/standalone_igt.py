# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 16:13:58 2024

Author: ir. Margely Cornelissen, FUS Initiative, Radboud University

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
# import the 'fus_driving_systems - sequence' into your code
##############################################################################

from fus_driving_systems import driving_system, transducer
from fus_driving_systems import sequence

##############################################################################
# create a sequence for an IGT driving system
# a sequence can be created in advance and a new sequence can be defined
# later on in the code
##############################################################################

seq = sequence.Sequence()

# equipment
# to check available driving systems: print(driving_system.get_ds_serials())
# choose one driving system from that list as input
seq.driving_sys = 'IGT-128-ch_comb_1x10-ch'

# set wait_for_trigger to true if you want to use trigger
seq.wait_for_trigger = True

# to check available transducers: print(transducer.get_tran_serials())
# choose one transducer from that list as input
seq.transducer = 'IS_PCD15287_01001'

# set general parameters
seq.oper_freq = 300  # [kHz], operating frequency
seq.focus = 40  # [mm], focal depth

# Degree used to dephase every nth elemen based on chosen degree. 0 = no dephasing
seq.dephasing_degree = 0  # [degrees]

# either set maximum pressure in free water [MPa], voltage [V] or amplitude [%]
# seq.volt = 0  # [V], voltage per channel

# # timing parameters # #
# you can use the TUS Calculator to visualize the timing parameters:
# https://www.socsci.ru.nl/fusinitiative/tuscalculator/

# ## pulse ## #

# pulse ramping
# to check available ramp shapes: print(seq.get_ramp_shapes())
# choose one ramp shape from that list as input

# ramping up and ramping down duration are equal and are equal to ramp duration

# ## pulse train ## #
# if you only want one pulse train, keep the values equal to the pulse repetition interval

# ## pulse train repetition ## #
# if you only want one pulse train, keep the value equal to the pulse repetition interval
# if you only want one pulse train repetition block, keep the value equal to the pulse train
# repetition interval

# to get a summary of your entered sequence: print(seq)
logger.info(f'The following sequence is used: {seq}')

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
# import the 'fus_driving_systems - ds' into your code
##############################################################################

from fus_driving_systems.igt import igt_ds

igt_driving_sys = igt_ds.IGT()

try:
    igt_driving_sys.connect(seq.driving_sys.connect_info)

    # you can check if the system is still connected by using the following:
    # print(igt_ds.is_connected())

    # If wait_for_trigger is true, only the sequence is sent and will be executed by the external trigger
    if seq.wait_for_trigger:
        igt_driving_sys.send_sequence(seq)
    
    # If wait_for_trigger is false, the sequence is sent and can be executed directly using the execute_sequence() function
    else:
        igt_driving_sys.send_sequence(seq)
        igt_driving_sys.execute_sequence()

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected automatically,
    # In the case your code is stopped abruptly, the driving system will be disconnected. Otherwise, there
    # is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not seq.wait_for_trigger:
        igt_driving_sys.disconnect()
