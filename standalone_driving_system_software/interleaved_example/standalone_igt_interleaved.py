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

from fus_driving_systems.config.config import config_info as config

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "D:\\Users\julkos\logs"
filename = "standalone_igt"
logger = initialize_logger(log_dir, filename)

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

##############################################################################
# first sequence collection
##############################################################################
from sequences import sequence_1_10_ch

seq1, seq2 = sequence_1_10_ch.create_sequence_collection()
##############################################################################
# second sequence collection
##############################################################################
from sequences import sequence_17_26_ch

seq3, seq4 = sequence_17_26_ch.create_sequence_collection()

total_duration_s = 80  # [s]

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
    igt_driving_sys.connect(seq1.driving_sys.connect_info, log_dir, filename)

    # you can check if the system is still connected by using the following:
    # print(igt_ds.is_connected())

    igt_driving_sys.send_sequence(seq1, seq2)

    # send other sequence using different buffer
    igt_driving_sys.send_sequence(seq3, seq4)

    one_interleaved_session_ms = seq1.pulse_train_rep_dur + seq3.pulse_train_rep_dur
    n_sessions = round(total_duration_s / (one_interleaved_session_ms/1000))
    for i in range(n_sessions):
        igt_driving_sys.execute_sequence(seq1, seq2)
        igt_driving_sys.execute_sequence(seq3, seq4)

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected
    # automatically. In the case your code is stopped abruptly, the driving system will be
    # disconnected. Otherwise, there is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not seq1.wait_for_trigger:
        igt_driving_sys.disconnect()
