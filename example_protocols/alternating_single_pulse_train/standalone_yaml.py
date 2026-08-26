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

# IGT example: two protocols interleaved as one alternating group, defined in protocol.yaml (edit
# that file to change your protocols). See standalone_plain.py in this same folder for the full
# manual-Python equivalent, including a longer explanation of what "pulse train interleaving"
# means and how it differs from ../switch_active_transducer/.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C:\\Temp"
filename = "standalone_yaml"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

# require_hash=False (the default) -- set to True once you have a real protocol.yaml you don't
# want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, total_alternating_duration_ms = load_protocol('protocol.yaml', require_hash=False)

# The driving system serial only needs to live in protocol.yaml -- load_protocol() already
# resolved it into a real DrivingSystem, reachable via either protocol's own driving_sys (both
# protocols in an interleaved group always target the same driving system).
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocols[0].driving_sys.connect_info, log_dir, filename)

try:
    igt_driving_sys.send_protocol(protocols, total_alternating_duration_ms)

    # wait for the external trigger rather than executing directly -- see standalone_plain.py
    # for the has_execution_error()/wait_for_trigger_result() explanation this pattern relies on.
    igt_driving_sys.wait_for_trigger(protocols, total_alternating_duration_ms)
    igt_driving_sys.wait_for_trigger_result(protocols[0].buffer_num,
                                            timeout_s=total_alternating_duration_ms / 1000.0)

finally:
    # By the time we reach here, the protocol has actually finished executing: wait_for_trigger_
    # result() above blocks until the triggered execution completes (or its timeout expires). If
    # your code stops abruptly before this point instead (like a kernel death/crash), disconnect
    # the driving system yourself, otherwise it may keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
