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

# IGT example: two transducers, both part of the same protocol (fire together, not alternating),
# defined in protocol.yaml (edit that file to change your protocol). See standalone_plain.py in
# this same folder for the full manual-Python equivalent.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_yaml"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

# load_protocol() returns a 5-tuple: (protocols, total_alternating_duration_ms, trigger_option,
# n_triggers, buffer_num). total_alternating_duration_ms is only relevant when interleaving more
# than one protocol -- ignored here (a single protocol, even with 2 slots). trigger_option/
# n_triggers are used below. buffer_num is unused here.
#
# require_hash=False (the default) -- set to True once you have a real protocol.yaml you don't
# want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, total_alternating_duration_ms, trigger_option, n_triggers, _ = load_protocol(
    'protocol.yaml', require_hash=False)

# trigger_option is None when protocol.yaml omits the key entirely, or the literal string 'None'
# when it's set explicitly (as protocol.yaml does here) -- either way means no trigger at all.
wait_for_trigger = trigger_option not in (None, 'None')

# The driving system serial only needs to live in protocol.yaml -- load_protocol() already
# resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys.
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocols[0].driving_sys.connect_info, log_dir, filename)

try:
    igt_driving_sys.send_protocol(protocols)

    # If wait_for_trigger is true (set via protocol.yaml's own trigger_option), only the
    # protocol is sent and will be executed by the external trigger. If false (protocol.yaml's
    # default), the protocol is sent and can be executed directly using execute_protocol(). See
    # ../single_transducer/igt/standalone_wait_for_trigger.py/standalone_wait_for_trigger_poll.py
    # for the full wait_for_trigger_result()/has_execution_error() explanation this pattern
    # relies on.
    if wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocols, trigger_option, n_triggers)
        igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)
    else:
        igt_driving_sys.execute_protocol(protocols)
finally:
    # Always safe to disconnect here -- execute_protocol()/wait_for_trigger_result() only
    # return once it's done. If your code stops abruptly before this point (e.g. a crash),
    # disconnect the driving system yourself, otherwise it may keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
