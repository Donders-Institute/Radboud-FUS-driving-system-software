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

# IGT example: two physically connected transducers, only one active at a time. The initial
# configuration comes from protocol.yaml (edit that file to change it) -- but switching which
# transducer is active mid-experiment is an imperative action, not something a static
# declarative file can express, so it still happens here in Python via slot.configure(), exactly
# like standalone_plain.py in this same folder.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C:\\Temp"
filename = "standalone_yaml"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.igt import igt_ds
from fus_driving_systems.protocol_loader import load_protocol

protocols, _ = load_protocol('protocol.yaml')
protocol = protocols[0]
slot1, slot2 = protocol.slots

# The driving system serial only needs to live in protocol.yaml -- load_protocol() already
# resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys.
igt_driving_sys = igt_ds.IGT(log_dir)
igt_driving_sys.connect(protocol.driving_sys.connect_info, log_dir, filename)

FOCUS_OPTION = 'Focus wrt exit plane [mm]'
POWER_OPTION = 'Max. pressure in free water [MPa]'
ACTIVE_PRESS = 0.5   # [MPa] -- must match protocol.yaml's own active slot value
INACTIVE_PRESS = 0   # [MPa] -- off, physically connected but not firing

try:
    igt_driving_sys.send_protocol(protocol)

    # If wait_for_trigger is true (set via protocol.yaml's own trigger_option), only the
    # protocol is sent and will be executed by the external trigger. If false (protocol.yaml's
    # default), the protocol is sent and can be executed directly using execute_protocol(). See
    # ../single_transducer/igt/standalone_wait_for_trigger.py/standalone_wait_for_trigger_poll.py
    # for the full wait_for_trigger_result()/has_execution_error() explanation this pattern
    # relies on.
    if protocol.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocol)
        igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)
    else:
        igt_driving_sys.execute_protocol(protocol)

    ##########################################################################
    # ... later in your experiment: switch which transducer is active ...
    ##########################################################################

    # slot.configure() changes an already-added slot's focus/power in place -- no new protocol,
    # no new slots, just the same two transducers with their power values swapped. Focus stays
    # the same here (still the current slot value), only power changes.
    slot1.configure(FOCUS_OPTION, slot1.focus_wrt_exit_plane, POWER_OPTION, INACTIVE_PRESS)
    slot2.configure(FOCUS_OPTION, slot2.focus_wrt_exit_plane, POWER_OPTION, ACTIVE_PRESS)

    # The driving system already has the OLD configuration loaded -- send_protocol() must be
    # called again so it picks up what slot.configure() just changed above.
    igt_driving_sys.send_protocol(protocol)
    if protocol.wait_for_trigger:
        igt_driving_sys.wait_for_trigger(protocol)
        igt_driving_sys.wait_for_trigger_result(timeout_s=5.0)
    else:
        igt_driving_sys.execute_protocol(protocol)

finally:
    # By the time we reach here, the protocol has actually finished executing either way:
    # execute_protocol()/wait_for_trigger_result() only return once it's done. So it's always
    # safe to disconnect here -- if your code stops abruptly before this point instead (like a
    # kernel death/crash), make sure to disconnect the driving system yourself, otherwise it may
    # keep firing ultrasound protocols.
    igt_driving_sys.disconnect()
