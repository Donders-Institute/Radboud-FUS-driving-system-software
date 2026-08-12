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

##############################################################################
# import the 'fus_driving_systems - tus_protocol' into your code
##############################################################################

from fus_driving_systems import driving_system, transducer
from fus_driving_systems import tus_protocol


def create_protocol(logger):
    ##############################################################################
    # create a protocol for an IGT driving system
    # a protocol can be created in advance and a new protocol can be defined
    # later on in the code
    ##############################################################################

    # equipment
    # to check available driving systems: print(driving_system.get_ds_serials())
    # choose one driving system from that list as input
    protocol = tus_protocol.TUSProtocol('IGT-32-ch_comb_2x10-ch')

    # Each add_slot() call fully configures one transducer -- serial, focus, and power all at
    # once (no partial/half-configured slot, and no separate available-channels check needed:
    # that's enforced automatically once the driving system's expected number of slots have been
    # added). Either use 'Max. pressure in free water [MPa]', 'Voltage [V]' or 'Amplitude [%]' as
    # POWER_OPTION. To check available options for this driving system (no need to add a slot
    # first): print(protocol.get_focus_options()) / print(protocol.get_power_options())
    FOCUS_OPTION = 'Focus wrt exit plane [mm]'
    POWER_OPTION = 'Max. pressure in free water [MPa]'

    # to check available transducers: print(transducer.get_tran_serials())
    # choose one transducer from that list as input
    slot3 = protocol.add_slot(
        'IS_PCD15287_01001',
        FOCUS_OPTION, 40,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0,  # [MPa], maximum pressure in free water. NOTE: DIFFERENT THAN SC
        oper_freq=300,  # [kHz], operating frequency

        # Degree used to dephase every nth elemen based on chosen degree. None = no dephasing
        # One value (>0) is the degree of dephasing, for example [90] with 4 elements: 1 elem: 0
        # dephasing, 2 elem: 90 dephasing, 3 elem: 180 dephasing, 4 elem: 270 dephasing.
        # When the amount of values match the amount of elements, it will override the
        # calculated phases based on the set focus.
        dephasing_degree=None,  # [degrees]: None, [120] or [0, 135, 239, 90]
    )

    # Using more than one transducer at once? Just add another slot -- as many as this driving
    # system's config allows (see protocol.driving_sys.max_tran_slots). Remove this second
    # add_slot() call entirely if you only have one transducer connected.
    # to check available transducers: print(transducer.get_tran_serials())
    # choose one transducer from that list as input
    slot4 = protocol.add_slot(
        'IS_PCD15287_01002',
        FOCUS_OPTION, 80,  # [mm], focal depth w.r.t. the exit plane and FWHM middle
        POWER_OPTION, 0.5,  # [MPa], maximum pressure in free water. NOTE: DIFFERENT THAN SC
        oper_freq=300,  # [kHz], operating frequency

        # Degree used to dephase every nth elemen based on chosen degree. None = no dephasing
        # One value (>0) is the degree of dephasing, for example [90] with 4 elements: 1 elem: 0
        # dephasing. 2 elem: 90 dephasing, 3 elem: 180 dephasing, 4 elem: 270 dephasing.
        # When the amount of values match the amount of elements, it will override the
        # calculated phases based on the set focus.
        dephasing_degree=None,  # [degrees]: None, [120] or [0, 135, 239, 90]
    )

    # # timing parameters # #
    # you can use the TUS Calculator to visualize the timing parameters:
    # https://www.socsci.ru.nl/fusinitiative/tuscalculator/

    # Compensate for delay measured with PicoScope
    interleave_diff = 0  # [ms]

    # configure_timing() sets every pulse/pulse-train/trigger parameter together, in one call --
    # each individual setter (pulse_dur, pulse_rep_int, ...) cascades its own value forward to
    # every level above it, so calling them one by one in the wrong order can silently overwrite
    # an earlier one (e.g. setting pulse_train_dur before pulse_dur). Passing everything to
    # configure_timing() at once avoids relying on any particular calling order.
    protocol.configure_timing(
        # ## pulse ## #
        pulse_dur=45,  # [ms], pulse duration

        # pulse ramping -- this protocol is passed second to send_protocol() in
        # standalone_igt_interleaved.py, so these ramp settings are actually ignored: only the
        # first protocol's ramping takes effect for the whole interleaved group (see that
        # script's own comment on the call). Set here anyway, matching tus_protocol_1_10_ch.py's
        # values, so nothing changes if the call order there is ever swapped.
        # to check available ramp shapes: print(protocol.get_ramp_shapes())
        # choose one ramp shape from that list as input
        pulse_ramp_shape='Tukey',
        # ramping up and ramping down duration are equal and are equal to ramp duration
        pulse_ramp_dur=5,  # [ms], ramp duration, with at least 70 us between ramping up and down

        # ## pulse train ## #
        pulse_rep_int=100 - interleave_diff,  # [ms], pulse repetition interval

        # if you only want one pulse train, you don't need to set this at all -- it defaults to
        # pulse_rep_int. Set explicitly here for clarity. NOTE: when interleaving (as this
        # protocol is, via send_protocol([protocol_a, protocol_b], ...)), each protocol
        # contributes exactly one pulse per round -- pulse_train_dur below has no effect in that
        # case; pulse_dur/pulse_rep_int above still do (pulse_rep_int decides how much of the
        # shared round this protocol's own pulse occupies).
        pulse_train_dur=100 - interleave_diff,  # [ms], pulse train duration

        # wait_for_trigger is derived from trigger_option -- there is no separate flag to set. Use
        # 'None' to not use a trigger at all; 'TriggerOnePulseTrain' to fire one pulse train per
        # trigger received (you must also give n_triggers below -- how many triggers to expect);
        # 'TriggerWholeProtocol' to fire the entire, already fully-timed protocol at
        # once with a single trigger (equivalent to executing it directly, just gated behind that
        # one trigger). To check available trigger options: print(protocol.get_trigger_options())
        # trigger_option='None',
        # trigger_option='TriggerOnePulseTrain',
        trigger_option='TriggerWholeProtocol',

        # Not used here -- n_triggers is only required for (and only settable with)
        # trigger_option='TriggerOnePulseTrain' (one pulse train fires per trigger received).
        # n_triggers=4,

        # ## pulse train repetition ## #
        # if you only want one pulse train repetition, you don't need to set either of these at
        # all -- pulse_train_rep_int defaults to pulse_train_dur, and pulse_train_rep_dur then
        # defaults to that (i.e. "repeat exactly once"). Set explicitly here for clarity. NOTE:
        # like pulse_train_dur above, these two have no effect when interleaving -- see the pulse
        # train section's own note.
        # [ms], pulse train repetition interval, NOTE: DIFFERENT THAN SC
        pulse_train_rep_int=100 - interleave_diff,
        # [s], pulse train repetition duration, NOTE: DIFFERENT THAN SC
        pulse_train_rep_dur=(100 - interleave_diff) / 1000,
    )

    # to get a summary of your entered protocol: print(protocol)

    return protocol
