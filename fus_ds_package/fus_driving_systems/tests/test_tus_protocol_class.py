# -*- coding: utf-8 -*-
"""
Characterization tests for fus_driving_systems.tus_protocol.TUSProtocol.

TUSProtocol.__init__ pulls in several config-driven defaults. To keep these tests fast and
independent of any specific driving-system/transducer/config combination, every test here builds
the instance with TUSProtocol.__new__(TUSProtocol) (bypassing __init__ entirely) and sets only
the private attributes the method-under-test actually reads.

Covers:
- configure_timing() -- the only way to set any timing/trigger parameter (pulse_dur,
  pulse_rep_int, pulse_train_dur, pulse_train_rep_int, pulse_train_rep_dur, pulse_ramp_shape,
  pulse_ramp_dur, trigger_option, n_triggers all have getters only), including the cascade
  defaults each level falls back to when not given, and the trigger_option-dependent choice
  between n_triggers and pulse_train_rep_int/pulse_train_rep_dur.
- add_slot() and _validate_channel_count(). driving_sys itself is read-only (set once, at
  construction) -- see its getter's own docstring for why swapping it isn't supported at all.
  add_slot() itself delegates transducer/focus/power configuration entirely to
  TransducerSlot.update_transducer() -- see test_transducer_slot.py for that method's own
  coverage (including swapping an already-added slot's transducer directly via
  protocol.slots[i].update_transducer(...), and the per-slot element-count check it runs).

There are no single-slot delegating properties on TUSProtocol (no protocol.press/
protocol.transducer/etc.) -- every per-transducer attribute is always addressed via
protocol.slots[i].<attribute>, whether there's one slot or several, so a script never has to
guess which access style applies. Power/focus setter logic itself (everything TransducerSlot
owns) moved to test_transducer_slot.py -- see that module instead.
"""
from types import SimpleNamespace

import pytest

from fus_driving_systems.tus_protocol import TUSProtocol


def _bare_protocol():
    """A TUSProtocol instance with __init__ skipped entirely."""
    return TUSProtocol.__new__(TUSProtocol)


def _fake_slot(serial='TRAN-A', elements=1, ampl=None):
    """A minimal stand-in for a TransducerSlot, for tests that only need TUSProtocol's own
    bookkeeping (slots list, delegation, channel counting) and not any real power/focus
    calculation."""
    return SimpleNamespace(
        transducer=SimpleNamespace(serial=serial, elements=elements), ampl=ampl)


# --- get_ramp_shapes ----------------------------------------------------------

def test_get_ramp_shapes_splits_config_value_on_newline(patch_config):
    patch_config.set('Ramp', 'Options', 'Rectangular - no ramping\nLinear\nTukey')
    protocol = _bare_protocol()

    assert protocol.get_ramp_shapes() == ['Rectangular - no ramping', 'Linear', 'Tukey']


# --- wait_for_trigger --------------------------------------------------------
# Derived from trigger_option, not stored independently -- True whenever trigger_option is
# anything other than the config's designated "no trigger" option (option.none).

def test_wait_for_trigger_is_false_for_the_none_trigger_option(patch_config):
    patch_config.set('Trigger', 'option.none', 'None')
    protocol = _bare_protocol()
    protocol._trigger_option = 'None'

    assert protocol.wait_for_trigger is False


def test_wait_for_trigger_is_true_for_any_other_trigger_option(patch_config):
    patch_config.set('Trigger', 'option.none', 'None')
    protocol = _bare_protocol()
    protocol._trigger_option = 'TriggerOnePulseTrain'

    assert protocol.wait_for_trigger is True


# --- configure_timing --------------------------------------------------------
# The only way to set any timing/trigger parameter -- pulse_dur, pulse_rep_int, pulse_train_dur,
# pulse_train_rep_int, pulse_train_rep_dur, pulse_ramp_shape, pulse_ramp_dur, trigger_option and
# n_triggers all have getters only. Applies every one of them in one fixed, always-safe internal
# order (lowest cascade level first), regardless of the order its own keyword arguments were
# given in. pulse_dur is the only required parameter: every level above it defaults to the level
# directly below it when not given, so a single pulse train, repeated once, is already a
# complete, self-consistent result. trigger_option/pulse_ramp_shape/pulse_ramp_dur left as None
# reset to their own safe/off default EVERY call (the config's "no trigger" option; "no ramping"
# and 0) rather than inheriting whatever an earlier, unrelated call left them at. There is no
# wait_for_trigger parameter -- it's derived from trigger_option (see above).

def test_configure_timing_requires_only_pulse_dur(patch_config):
    """pulse_dur is the only required parameter -- everything else, including trigger_option,
    resets to its own safe/off default rather than requiring an explicit value."""
    patch_config.set('Trigger', 'option.none', 'None')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._n_triggers = 'unchanged'

    protocol.configure_timing(pulse_dur=10)

    assert protocol.pulse_dur == 10
    assert protocol.pulse_rep_int == 10
    assert protocol.pulse_train_dur == 10
    assert protocol.pulse_train_rep_int == 10
    assert protocol.pulse_train_rep_dur == 10
    assert protocol.trigger_option == 'None'
    assert protocol._n_triggers == 'unchanged'  # left untouched -- n_triggers itself wasn't given


def test_configure_timing_resets_trigger_option_to_none_when_not_given(patch_config):
    """Unlike pulse_rep_int/pulse_train_dur/etc. (which are freshly re-derived from THIS call's
    pulse_dur every time, so there's nothing stale to inherit), trigger_option has no such
    cascade -- so leaving it out must reset to the safe "no trigger" default, not silently keep
    whatever an earlier, unrelated call left it at."""
    patch_config.set('Trigger', 'option.none', 'None')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'TriggerOnePulseTrain'  # a stale value from some earlier call

    protocol.configure_timing(pulse_dur=10)

    assert protocol.trigger_option == 'None'


def test_configure_timing_resets_ramp_to_no_ramping_when_not_given(patch_config):
    patch_config.set('Ramp', 'option.rect', 'Rectangular - no ramping')
    protocol = _bare_protocol()
    # A stale ramp from some earlier call -- must not survive a call that doesn't mention ramping.
    protocol._timing_param = {'pulse_ramp_shape': 'Linear', 'pulse_ramp_dur': 3}

    protocol.configure_timing(pulse_dur=10)

    assert protocol.pulse_ramp_shape == 'Rectangular - no ramping'
    assert protocol.pulse_ramp_dur == 0


def test_configure_timing_rejects_zero_pulse_dur():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=0)


def test_configure_timing_rejects_negative_pulse_dur():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=-5)


def test_configure_timing_exits_for_unavailable_trigger_option():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, trigger_option='Something else')


def test_configure_timing_pulse_rep_int_overrides_default_but_leaves_pulse_dur():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=5, pulse_rep_int=30)

    assert protocol.pulse_dur == 5  # untouched
    assert protocol.pulse_rep_int == 30
    assert protocol.pulse_train_dur == 30  # defaults to the level below it, not to pulse_dur
    # ...and the cascade keeps propagating past that one level, all the way to the top.
    assert protocol.pulse_train_rep_int == 30
    assert protocol.pulse_train_rep_dur == 30


def test_configure_timing_pulse_train_dur_overrides_default_but_leaves_lower_levels():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=5, pulse_rep_int=10, pulse_train_dur=40)

    assert protocol.pulse_dur == 5
    assert protocol.pulse_rep_int == 10
    assert protocol.pulse_train_dur == 40
    # ...and the two levels above it default from THIS value, not from pulse_dur/pulse_rep_int.
    assert protocol.pulse_train_rep_int == 40
    assert protocol.pulse_train_rep_dur == 40


def test_configure_timing_sets_pulse_ramp_shape(patch_config):
    patch_config.set('Ramp', 'Options', 'Linear\nTukey')
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=10, pulse_ramp_shape='Linear')

    assert protocol.pulse_ramp_shape == 'Linear'


def test_configure_timing_exits_for_unavailable_ramp_shape(patch_config):
    patch_config.set('Ramp', 'Options', 'Linear\nTukey')
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, pulse_ramp_shape='Something else')


def test_configure_timing_pulse_ramp_dur_accepts_zero():
    """check_nonzero=False for this parameter -- 0 is a legitimate 'no ramp duration set yet'
    value, unlike pulse_dur/pulse_rep_int/pulse_train_dur above."""
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=10, pulse_ramp_dur=0)

    assert protocol.pulse_ramp_dur == 0


def test_configure_timing_rejects_negative_pulse_ramp_dur():
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, pulse_ramp_dur=-1)


def test_configure_timing_forces_single_trigger_for_whole_protocol_option(patch_config):
    patch_config.set('Trigger', 'option.whole_protocol', 'TriggerWholeProtocol')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'None'
    protocol._n_triggers = 5

    protocol.configure_timing(pulse_dur=10, trigger_option='TriggerWholeProtocol')

    assert protocol.n_triggers == 1


def test_configure_timing_leaves_n_triggers_untouched_for_the_none_option(patch_config):
    patch_config.set('Trigger', 'option.whole_protocol', 'TriggerWholeProtocol')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'TriggerOnePulseTrain'
    protocol._n_triggers = 7

    protocol.configure_timing(pulse_dur=10, trigger_option='None')

    assert protocol.n_triggers == 7  # untouched -- forcing to 1 is specific to the ptr option


def test_configure_timing_sets_every_level_via_n_triggers(patch_config):
    patch_config.set('Trigger', 'option.whole_protocol', 'TriggerWholeProtocol')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'None'
    protocol._n_triggers = 0

    protocol.configure_timing(pulse_dur=10, pulse_rep_int=200, pulse_train_dur=200,
                              trigger_option='TriggerOnePulseTrain',
                              pulse_ramp_shape='Linear', pulse_ramp_dur=5, n_triggers=4)

    assert protocol.pulse_dur == 10
    assert protocol.pulse_rep_int == 200
    assert protocol.pulse_train_dur == 200
    assert protocol.trigger_option == 'TriggerOnePulseTrain'
    assert protocol.n_triggers == 4
    assert protocol.pulse_ramp_shape == 'Linear'
    assert protocol.pulse_ramp_dur == 5
    # Don't apply to this trigger mode (n_triggers governs repetition instead), but still
    # cascade to their own "repeat once" default rather than being left unset/stale.
    assert protocol.pulse_train_rep_int == 200
    assert protocol.pulse_train_rep_dur == 200


def test_configure_timing_sets_every_level_via_duration(patch_config):
    patch_config.set('Trigger', 'option.whole_protocol', 'TriggerWholeProtocol')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'None'
    protocol._n_triggers = 0

    protocol.configure_timing(pulse_dur=10, pulse_rep_int=200, pulse_train_dur=200,
                              trigger_option='TriggerWholeProtocol',
                              pulse_train_rep_int=200, pulse_train_rep_dur=2)

    assert protocol.pulse_train_rep_int == 200
    assert protocol.pulse_train_rep_dur == 2000  # stored in ms, setter takes seconds
    # n_triggers isn't valid for this trigger mode -- forced to 1 regardless of what's given
    # (nothing is given here), purely for ControlDrivingSystem implementations' own logging.
    assert protocol.n_triggers == 1


def test_configure_timing_is_order_independent():
    """The exact scenario configure_timing() exists to prevent: with no public setters left,
    the only way this could still go wrong is configure_timing() itself applying its own
    arguments in the order they were listed/passed in, rather than always lowest-cascade-level
    first -- pulse_train_dur given before pulse_dur must not have pulse_dur's own default
    silently clobber it back down."""
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_train_dur=500, pulse_dur=10, pulse_rep_int=200,
                              pulse_train_rep_int=500, pulse_train_rep_dur=5)

    assert protocol.pulse_dur == 10
    assert protocol.pulse_train_dur == 500  # not clobbered back down to 10


def test_configure_timing_derives_pulse_train_rep_dur_from_rep_int_alone():
    """Giving only pulse_train_rep_int derives pulse_train_rep_dur as exactly one repetition of
    that interval -- the same ms<->s relationship as the "repeat once" default used when neither
    is given, just anchored to the explicitly given value instead of pulse_train_dur."""
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=10, pulse_train_rep_int=300)

    assert protocol.pulse_train_rep_int == 300
    assert protocol.pulse_train_rep_dur == 300  # stored in ms -- 300/1e3 s * 1e3 = 300 ms


def test_configure_timing_pulse_train_rep_dur_alone_repeats_back_to_back():
    """Unlike giving only pulse_train_rep_int (which derives pulse_train_rep_dur to match, i.e.
    "repeat once"), giving only pulse_train_rep_dur -- a total span to repeat over -- fills that
    span back-to-back: pulse_train_rep_int defaults to pulse_train_dur, not to a value derived
    from the given pulse_train_rep_dur (which would make the given value self-referential)."""
    protocol = _bare_protocol()
    protocol._timing_param = {}

    protocol.configure_timing(pulse_dur=10, pulse_train_rep_dur=0.3)

    assert protocol.pulse_train_rep_int == 10  # pulse_train_dur, unrelated to the given rep_dur
    assert protocol.pulse_train_rep_dur == 300  # stored in ms -- 0.3 s * 1e3, kept as given


def test_configure_timing_exits_when_both_trigger_modes_given(patch_config):
    patch_config.set('Trigger', 'option.pulse_train', 'TriggerOnePulseTrain')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'None'

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, pulse_rep_int=200, pulse_train_dur=200,
                                  trigger_option='TriggerOnePulseTrain',
                                  n_triggers=4, pulse_train_rep_int=200, pulse_train_rep_dur=2)


def test_configure_timing_exits_when_n_triggers_given_for_non_pulse_train_trigger_option(
        patch_config):
    """n_triggers only applies when trigger_option is the "trigger per pulse train" option --
    giving it alongside any other trigger_option (the default, 'None', here) is a mismatch,
    not silently corrected."""
    patch_config.set('Trigger', 'option.pulse_train', 'TriggerOnePulseTrain')
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, n_triggers=4)


def test_configure_timing_exits_when_duration_given_for_pulse_train_trigger_option(patch_config):
    """pulse_train_rep_int/pulse_train_rep_dur don't apply when trigger_option is the "trigger
    per pulse train" option -- give n_triggers instead."""
    patch_config.set('Trigger', 'option.pulse_train', 'TriggerOnePulseTrain')
    protocol = _bare_protocol()
    protocol._timing_param = {}
    protocol._trigger_option = 'None'

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, trigger_option='TriggerOnePulseTrain',
                                  pulse_train_rep_int=200, pulse_train_rep_dur=2)


def test_configure_timing_exits_when_n_triggers_omitted_for_pulse_train_trigger_option(
        patch_config):
    """One pulse train fires per trigger under 'TriggerOnePulseTrain' -- the driving system
    genuinely needs to know in advance how many triggers to expect, so unlike every other
    parameter in this method, n_triggers has no sensible default to silently fall back to."""
    patch_config.set('Trigger', 'option.pulse_train', 'TriggerOnePulseTrain')
    protocol = _bare_protocol()
    protocol._timing_param = {}

    with pytest.raises(SystemExit):
        protocol.configure_timing(pulse_dur=10, trigger_option='TriggerOnePulseTrain')


# --- buffer_num ---------------------------------------------------------------
# Which of the driving system's hardware buffers this protocol targets -- only meaningful for a
# driving system that actually has more than one (see DrivingSystem.max_buffers); a driving
# system with none at all (max_buffers == 1, the default) only ever accepts buffer_num == 0.

def test_buffer_num_defaults_to_zero():
    protocol = _bare_protocol()
    protocol._buffer_num = 0

    assert protocol.buffer_num == 0


def test_buffer_num_setter_accepts_value_within_range():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_buffers=2)

    protocol.buffer_num = 1

    assert protocol.buffer_num == 1


def test_buffer_num_setter_rejects_negative_value():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_buffers=2)

    with pytest.raises(SystemExit):
        protocol.buffer_num = -1


def test_buffer_num_setter_exits_when_at_or_above_max_buffers():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_buffers=2)

    with pytest.raises(SystemExit):
        protocol.buffer_num = 2  # only 0 and 1 are valid when max_buffers == 2


def test_buffer_num_setter_exits_for_any_nonzero_value_when_driving_system_has_no_buffers():
    """max_buffers defaults to 1 for a driving system with no real buffer concept at all --
    buffer_num can then only ever be 0."""
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_buffers=1)

    with pytest.raises(SystemExit):
        protocol.buffer_num = 1


# --- driving_sys ------------------------------------------------------------
# Read-only -- set once, at construction (see __init__), never changed afterward. Swapping which
# physical driving system a TUSProtocol targets mid-experiment isn't supported: construct a new
# TUSProtocol and re-add_slot() every transducer instead (see the getter's own docstring for why).

def test_driving_sys_has_no_setter():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace()

    with pytest.raises(AttributeError):
        protocol.driving_sys = SimpleNamespace()


# --- get_power_options / get_focus_options -----------------------------------
# Available straight off the driving system, before any slot has been added -- add_slot() itself
# needs a valid option string, so callers must be able to query these first.

def test_get_power_options_forwards_to_driving_sys():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(power_options=['Global power [mW]'])

    assert protocol.get_power_options() == ['Global power [mW]']


def test_get_focus_options_forwards_to_driving_sys():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(focus_options=['Focus wrt exit plane [mm]'])

    assert protocol.get_focus_options() == ['Focus wrt exit plane [mm]']


# --- slots / add_slot / _dispatch_focus / _dispatch_power -------------------

def _configure_transducer(patch_config, serial, elements=2):
    """Configures a minimal, real 'Equipment.Transducer.*' section -- add_slot() assigns a real
    transducer serial via TransducerSlot.transducer's setter, which does a real config lookup
    (unlike driving_sys, which add_slot()'s other tests get away with faking via a plain
    SimpleNamespace)."""
    section = f'Equipment.Transducer.{serial}'
    patch_config.set(section, 'Elements', str(elements))
    patch_config.set(section, 'Fund. freq.', '300')
    patch_config.set(section, 'Min. focus', '0')
    patch_config.set(section, 'Max. focus', '100')
    patch_config.set(section, 'Exit plane - first element dist.', '5')
    patch_config.set(section, 'Steer information', '')
    patch_config.set(section, 'Active?', 'True')


def test_add_slot_exits_when_max_tran_slots_exceeded():
    protocol = _bare_protocol()
    protocol._engineering_mode = False
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_tran_slots=1)
    protocol._slots = [_fake_slot()]

    with pytest.raises(SystemExit):
        protocol.add_slot('TRAN-B', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)


def test_add_slot_exits_when_transducer_exceeds_elements_per_slot(patch_config):
    """Slots are always evenly divided, so the per-slot ceiling is simply
    available_ch / max_tran_slots -- no separate config key for it. A transducer with more
    elements than that must be rejected before ever touching focus/power, regardless of how the
    *other* slots end up filled."""
    _configure_transducer(patch_config, 'TRAN-BIG', elements=60)
    protocol = _bare_protocol()
    protocol._engineering_mode = False
    protocol._driving_sys = SimpleNamespace(serial='DS1', max_tran_slots=4, available_ch=208,
                                            tran_comp=['TRAN-BIG'])
    protocol._slots = []

    with pytest.raises(SystemExit, match='60 elements'):
        protocol.add_slot('TRAN-BIG', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)


def test_add_slot_accepts_transducer_at_exactly_the_per_slot_ceiling(patch_config):
    _configure_transducer(patch_config, 'TRAN-52', elements=52)
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    protocol = _bare_protocol()
    protocol._engineering_mode = True
    protocol._driving_sys = SimpleNamespace(
        serial='DS1', max_tran_slots=4, available_ch=208, tran_comp=['TRAN-52'],
        power_options=['Amplitude [%]'], focus_options=['Focus wrt exit plane [mm]'],
        native_power_params=['Amplitude [%]'], native_focus_params=['Focus wrt exit plane [mm]'])
    protocol._slots = []

    slot = protocol.add_slot('TRAN-52', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)

    assert slot.transducer.elements == 52


def test_add_slot_sets_optional_oper_freq_and_dephasing_degree(patch_config):
    _configure_transducer(patch_config, 'TRAN-A', elements=2)
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    protocol = _bare_protocol()
    protocol._engineering_mode = True
    protocol._driving_sys = SimpleNamespace(
        serial='DS1', max_tran_slots=1, available_ch=2, tran_comp=['TRAN-A'],
        power_options=['Amplitude [%]'], focus_options=['Focus wrt exit plane [mm]'],
        native_power_params=['Amplitude [%]'], native_focus_params=['Focus wrt exit plane [mm]'])
    protocol._slots = []

    slot = protocol.add_slot('TRAN-A', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30,
                             oper_freq=500, dephasing_degree=[90, 180])

    assert slot.oper_freq == 500
    assert slot.dephasing_degree == [90, 180]


def test_add_slot_defaults_oper_freq_to_transducer_fund_freq_when_not_given(patch_config):
    """oper_freq has no calibration-ordering hazard (unlike focus/power) -- it's optional, and
    when not given keeps whatever TransducerSlot.transducer's own setter already derived from
    the transducer's fundamental frequency."""
    _configure_transducer(patch_config, 'TRAN-A', elements=2)
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    protocol = _bare_protocol()
    protocol._engineering_mode = True
    protocol._driving_sys = SimpleNamespace(
        serial='DS1', max_tran_slots=1, available_ch=2, tran_comp=['TRAN-A'],
        power_options=['Amplitude [%]'], focus_options=['Focus wrt exit plane [mm]'],
        native_power_params=['Amplitude [%]'], native_focus_params=['Focus wrt exit plane [mm]'])
    protocol._slots = []

    slot = protocol.add_slot('TRAN-A', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)

    assert slot.oper_freq == 300  # transducer's own 'Fund. freq.', from _configure_transducer
    assert slot.dephasing_degree is None


# --- _validate_channel_count -------------------------------------------------

def test_validate_channel_count_exits_when_total_elements_exceed_available_ch():
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(available_ch=4)
    protocol._slots = [_fake_slot(elements=3), _fake_slot(elements=3)]

    with pytest.raises(SystemExit):
        protocol._validate_channel_count()


def test_validate_channel_count_allows_building_up_to_the_exact_total():
    """Deliberately not an exact-equality check -- a driving system with more than one slot
    (max_tran_slots > 1) is legitimately 'not done yet' after just the first add_slot() call."""
    protocol = _bare_protocol()
    protocol._driving_sys = SimpleNamespace(available_ch=4)
    protocol._slots = [_fake_slot(elements=2)]

    protocol._validate_channel_count()  # must not raise -- 2 < 4, still room for another slot
