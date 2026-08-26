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

# IGT example: a single transducer, defined in wait_for_trigger.yaml (same file
# standalone_wait_for_trigger.py uses -- edit it to change your protocol), armed to fire on a
# single external trigger. Unlike that script, this one does NOT block waiting for the result --
# it polls has_execution_error() in its own loop instead, so it can do other work (e.g. waiting
# on other equipment) while the trigger hasn't fired yet.

import time

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_wait_for_trigger_poll"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

# total_alternating_duration_ms (load_protocol()'s second return value) is only relevant when
# interleaving more than one protocol -- ignored here (a single protocol).
#
# require_hash=False (the default) -- set to True once you have a real wait_for_trigger.yaml you
# don't want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, _ = load_protocol('wait_for_trigger.yaml', require_hash=False)

# The driving system serial only needs to live in wait_for_trigger.yaml -- load_protocol()
# already resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys.
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocols[0].driving_sys.connect_info, log_dir, filename)

try:
    igt_driving_sys.send_protocol(protocols)
    igt_driving_sys.wait_for_trigger(protocols)

    # has_execution_error() only tells you whether an error has occurred SO FAR -- not whether
    # the protocol has finished. Replace the time-based condition below with your own (e.g.
    # "still waiting on the stimuli").
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if igt_driving_sys.has_execution_error() is not None:
            break  # react immediately (log, stop other equipment, sys.exit(), ...)
        time.sleep(0.1)  # <do other work here instead, in a real experiment>

    # Your own loop condition above isn't necessarily tied to the protocol's actual completion,
    # so disconnecting right after it can cut off a still-running protocol -- call
    # wait_for_trigger_result() once you expect the trigger to have fired, to confirm the
    # protocol actually finished (and exit if it reports failure) before disconnecting below.
    igt_driving_sys.wait_for_trigger_result(protocols[0].buffer_num, timeout_s=5.0)

finally:
    # Safe to disconnect here: wait_for_trigger_result() above confirmed the protocol actually
    # finished. If your code stops abruptly before this point instead (e.g. a crash), disconnect
    # the driving system yourself, otherwise it may keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
