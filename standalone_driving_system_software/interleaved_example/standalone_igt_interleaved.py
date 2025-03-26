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
If you use this kit in your research or project, please include the following attribution:
Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 1.0),
https://github.com/Donders-Institute/Radboud-FUS-measurement-kit
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

# When this code is embedded in other code with logging, ignore above commands and sync the logger
# in the following way:

# from fus_driving_systems.config.logging_config import sync_logger
# sync_logger(logger)  # logger needs to be created with logging.getLogger()

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

igt_driving_sys = igt_ds.IGT(log_dir)

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
        print(f'\n session {i} of {n_sessions} \n')
        igt_driving_sys.execute_sequence(seq1, seq2)
        igt_driving_sys.execute_sequence(seq3, seq4)

finally:
    # When the sequence is executed using execute_sequence(), the system will be disconnected
    # automatically. In the case your code is stopped abruptly, the driving system will be
    # disconnected. Otherwise, there is a change that it keeps on firing ultrasound sequences.
    # When using the external trigger, disconnect the driving system yourself.
    if not seq1.wait_for_trigger:
        igt_driving_sys.disconnect()
