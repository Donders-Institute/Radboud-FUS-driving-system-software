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

# Sonic Concepts example: a single transducer, defined in protocol.yaml (edit that file to
# change your protocol). See standalone_plain.py in this same folder for the full manual-Python
# equivalent.

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "standalone_yaml"
logger = initialize_logger(log_dir, filename)

from fus_driving_systems.sonic_concepts import sonic_concepts_ds
from fus_driving_systems.protocol_loader import load_protocol

# load_protocol() returns a 5-tuple: (protocols, total_alternating_duration_ms, trigger_option,
# n_triggers, buffer_num). total_alternating_duration_ms/n_triggers/buffer_num don't apply here
# -- SonicConcepts has no interleaving, per-trigger-count, or buffer concept. trigger_option is
# used below to decide whether to arm for an external trigger (wait_for_trigger()) or execute
# directly (execute_protocol()).
#
# require_hash=False (the default) -- set to True once you have a real protocol.yaml you don't
# want accidentally changed; see README.md's "Load a protocol from a YAML file" section.
protocols, total_alternating_duration_ms, trigger_option, n_triggers, _ = load_protocol(
    'protocol.yaml', require_hash=False)
protocol = protocols[0]

# trigger_option is None when protocol.yaml omits the key entirely, or the literal string 'None'
# when it's set explicitly (as protocol.yaml does here) -- either way means no trigger at all.
wait_for_trigger = trigger_option not in (None, 'None')

# The driving system serial only needs to live in protocol.yaml -- load_protocol() already
# resolved it into a real DrivingSystem, reachable via the protocol's own driving_sys. The COM
# port is machine-specific, though, and not something ds_config.ini can know in advance --
# override it here so send_protocol()/execute_protocol()'s automatic reconnect (if the
# connection ever drops) also uses the right port.
protocol.driving_sys.connect_info = 'COM5'  # COM port the driving system is connected to here

sc_ds = sonic_concepts_ds.SonicConcepts()
sc_ds.connect(protocol.driving_sys.connect_info)

# optional: check if correct transducer is selected on driving system before continuing
sc_ds.check_tran_sel()

try:
    sc_ds.send_protocol(protocol)

    # If wait_for_trigger is true, the protocol is armed and will be executed by the external
    # trigger. If false, the protocol is executed directly.
    if wait_for_trigger:
        sc_ds.wait_for_trigger(protocol)
    else:
        sc_ds.execute_protocol(protocol)

finally:
    # When the protocol is executed using execute_protocol(), the system is disconnected
    # automatically -- when using the external trigger instead, disconnect it yourself.
    if not wait_for_trigger:
        sc_ds.disconnect()
