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

# IGT example: a single transducer, defined in direct_execute.yaml (edit that file to change
# your protocol) and executed directly -- no external trigger involved. See
# standalone_wait_for_trigger.py/standalone_wait_for_trigger_poll.py in this same folder for the
# trigger-based alternative.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_direct_execute"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

# engineering_mode=True here would allow direct_execute.yaml to use engineering-only options
# (e.g. 'Voltage [V]', 'Amplitude [%]', 'Focus wrt mid bowl [mm]') -- left False (the default)
# since this example doesn't need them. engineering_mode is only ever set here, in Python --
# never in the YAML file itself.
#
# load_protocol() returns a 5-tuple: (protocols, total_alternating_duration_ms, trigger_option,
# n_triggers, buffer_num). total_alternating_duration_ms is only relevant when interleaving more
# than one protocol, trigger_option/n_triggers only when waiting for an external trigger, and
# buffer_num only for a driving system with more than one hardware buffer -- none of that
# applies here (a single protocol, executed directly, on today's driving systems), so there's
# nothing to read or pass on for any of the three.
#
# require_hash=False (the default) -- set to True once you have a real direct_execute.yaml you
# don't want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, total_alternating_duration_ms, trigger_option, n_triggers, _ = load_protocol(
    'direct_execute.yaml', require_hash=False)

# The driving system serial only needs to live in direct_execute.yaml -- load_protocol() already
# resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys, so there's
# no separate DrivingSystem() to build (and no risk of it drifting out of sync with the YAML).
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocols[0].driving_sys.connect_info, log_dir, filename)

try:
    igt_driving_sys.send_protocol(protocols)
    igt_driving_sys.execute_protocol(protocols)
finally:
    # Always safe to disconnect here -- execute_protocol() only returns once it's done. If your
    # code stops abruptly before this point (e.g. a crash), disconnect the driving system
    # yourself, otherwise it may keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
