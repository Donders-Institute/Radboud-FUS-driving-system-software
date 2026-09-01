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

# IGT example: a single transducer, defined in wait_for_trigger.yaml (edit that file to change
# your protocol), armed to fire on a single external trigger. Blocks until the triggered
# execution finishes (or times out), then reacts if it failed.
#
# Have other work to do while waiting instead (e.g. waiting on other equipment)? See
# standalone_wait_for_trigger_poll.py in this same folder for a non-blocking alternative.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_wait_for_trigger"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

# load_protocol() returns a 5-tuple: (protocols, total_alternating_duration_ms, trigger_option,
# n_triggers, buffer_num). total_alternating_duration_ms is only relevant when interleaving more
# than one protocol -- ignored here (a single protocol). trigger_option/n_triggers are used
# below, forwarded straight into wait_for_trigger() -- wait_for_trigger.yaml sets trigger_option
# to 'TriggerWholeProtocol' and omits n_triggers (not needed for that trigger_option). buffer_num
# is unused here.
#
# require_hash=False (the default) -- set to True once you have a real wait_for_trigger.yaml you
# don't want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, total_alternating_duration_ms, trigger_option, n_triggers, _ = load_protocol(
    'wait_for_trigger.yaml', require_hash=False)

# The driving system serial only needs to live in wait_for_trigger.yaml -- load_protocol()
# already resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys.
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocols[0].driving_sys.connect_info, log_dir, filename)

try:
    igt_driving_sys.send_protocol(protocols)

    # Only arms the protocol to fire on the external trigger and returns immediately -- does NOT
    # wait for, or check, the actual execution result. The driving system only reports success/
    # failure once the triggered execution is actually finished, which can happen at an
    # unpredictable moment later (whenever your external trigger fires).
    igt_driving_sys.wait_for_trigger(protocols, trigger_option, n_triggers)

    # Blocks until the triggered execution completes (or the timeout expires), then exits if the
    # driving system reports the execution failed. Adjust the timeout to match how long your
    # triggered protocol is expected to take. An execution error is always logged immediately
    # when it happens, but your code only actively reacts to it (via sys.exit()) once this is
    # called -- calling it late means reacting late.
    igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)

finally:
    # Safe to disconnect here: wait_for_trigger_result() above blocks until the triggered
    # execution completes (or its timeout expires). If your code stops abruptly before this
    # point instead (e.g. a crash), disconnect the driving system yourself, otherwise it may
    # keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
