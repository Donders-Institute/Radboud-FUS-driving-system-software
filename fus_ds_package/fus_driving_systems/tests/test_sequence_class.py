# -*- coding: utf-8 -*-
"""
Characterization tests for fus_driving_systems.sequence.Sequence.

Sequence.__init__ pulls in ~25 config-driven defaults and, depending on
the chosen driving-system/transducer combo, can trigger real JSON file
loading via extract_and_define_pp. To keep these tests fast and
independent of any specific driving-system/transducer/config
combination, every test here builds the instance with
Sequence.__new__(Sequence) (bypassing __init__ entirely) and sets only
the private attributes the method-under-test actually reads.

Covers:
- The cascading timing-property setters: pulse_dur -> pulse_rep_int ->
  pulse_train_dur -> pulse_train_rep_int -> pulse_train_rep_dur.
- The private _calc_* pressure/amplitude/voltage conversion methods,
  driven by small hand-built scipy.interpolate.PPoly objects (same
  pattern as test_sequence_pure.py's linear_pp/decreasing_pp fixtures).
"""
from types import SimpleNamespace

import pytest
from scipy.interpolate import PPoly

from fus_driving_systems.sequence import Sequence


def _bare_sequence():
    """A Sequence instance with __init__ skipped entirely."""
    return Sequence.__new__(Sequence)


def _identity_pp(a, b):
    """A piecewise polynomial with pp(x) == x over the domain [a, b]."""
    return PPoly(c=[[1.0], [a]], x=[a, b], extrapolate=False)


# --- pulse_dur ---------------------------------------------------------
# pulse_dur is the lowest timing level: setting it cascades its own value
# down to every higher level (pulse_rep_int, pulse_train_dur,
# pulse_train_rep_int, pulse_train_rep_dur), each stored internally in ms.

def test_pulse_dur_setter_cascades_to_all_downstream_levels():
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerSequence'  # not the ptr option -> no n_triggers side effect

    seq.pulse_dur = 20

    assert seq.pulse_dur == 20
    assert seq.pulse_rep_int == 20
    assert seq.pulse_train_dur == 20
    assert seq.pulse_train_rep_int == 20
    # pulse_train_rep_dur's own setter takes SECONDS and stores ms
    # (value * 1e3); pulse_dur's cascade passes pulse_dur / 1e3, so the
    # ms<->s conversions cancel out and the stored ms value still equals
    # pulse_dur.
    assert seq.pulse_train_rep_dur == 20


def test_pulse_dur_setter_rejects_zero():
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerSequence'

    with pytest.raises(SystemExit):
        seq.pulse_dur = 0


def test_pulse_dur_setter_rejects_negative():
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerSequence'

    with pytest.raises(SystemExit):
        seq.pulse_dur = -5


# --- pulse_rep_int -------------------------------------------------------
# Cascades upward only -- it must not touch pulse_dur, the level below it.

def test_pulse_rep_int_setter_cascades_up_but_not_down():
    seq = _bare_sequence()
    seq._timing_param = {'pulse_dur': 5}
    seq._trigger_option = 'TriggerSequence'

    seq.pulse_rep_int = 30

    assert seq.pulse_dur == 5  # untouched
    assert seq.pulse_rep_int == 30
    assert seq.pulse_train_dur == 30
    assert seq.pulse_train_rep_int == 30
    assert seq.pulse_train_rep_dur == 30


# --- pulse_train_dur -----------------------------------------------------

def test_pulse_train_dur_setter_cascades_up_but_not_down():
    seq = _bare_sequence()
    seq._timing_param = {'pulse_dur': 5, 'pulse_rep_int': 10}
    seq._trigger_option = 'TriggerSequence'

    seq.pulse_train_dur = 40

    assert seq.pulse_dur == 5
    assert seq.pulse_rep_int == 10
    assert seq.pulse_train_dur == 40
    assert seq.pulse_train_rep_int == 40
    assert seq.pulse_train_rep_dur == 40


# --- pulse_train_rep_int --------------------------------------------------
# Only cascades to pulse_train_rep_dur -- pulse_train_dur is left alone.

def test_pulse_train_rep_int_setter_cascades_only_to_rep_dur():
    seq = _bare_sequence()
    seq._timing_param = {'pulse_dur': 5, 'pulse_rep_int': 10, 'pulse_train_dur': 20}
    seq._trigger_option = 'TriggerSequence'

    seq.pulse_train_rep_int = 50

    assert seq.pulse_train_dur == 20  # untouched
    assert seq.pulse_train_rep_int == 50
    assert seq.pulse_train_rep_dur == 50


# --- pulse_train_rep_dur ---------------------------------------------------
# Top of the cascade: takes SECONDS (unlike every level below it, which is
# ms) and stores the value converted to ms. Also has a side effect wholly
# unrelated to timing: when the trigger option is
# 'TriggerOnePulseTrainRepetition' it forces n_triggers to 1.

def test_pulse_train_rep_dur_setter_converts_seconds_to_ms():
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerSequence'

    seq.pulse_train_rep_dur = 2  # seconds

    assert seq.pulse_train_rep_dur == 2000  # ms


def test_pulse_train_rep_dur_setter_forces_single_trigger_for_ptr_option(patch_config):
    patch_config.set('Trigger', 'option.ptr', 'TriggerOnePulseTrainRepetition')
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerOnePulseTrainRepetition'
    seq._n_triggers = 5

    seq.pulse_train_rep_dur = 1

    assert seq._n_triggers == 1


def test_pulse_train_rep_dur_setter_leaves_n_triggers_for_other_options(patch_config):
    patch_config.set('Trigger', 'option.ptr', 'TriggerOnePulseTrainRepetition')
    seq = _bare_sequence()
    seq._timing_param = {}
    seq._trigger_option = 'TriggerSequence'
    seq._n_triggers = 7

    seq.pulse_train_rep_dur = 1

    assert seq._n_triggers == 7  # untouched


# --- _calc_eq_factor -------------------------------------------------------

def test_calc_eq_factor_evaluates_pp_at_focus_wrt_exit_plane():
    seq = _bare_sequence()
    seq._conv_param = {'eq_curve_pp': _identity_pp(0.0, 10.0)}
    seq._focus_wrt_exit_plane = 5

    seq._calc_eq_factor()

    assert float(seq._eq_factor) == pytest.approx(5.0)


def test_calc_eq_factor_exits_when_focus_is_not_numeric():
    """
    The except ValueError branch is only reachable when focus_wrt_exit_plane
    can't be converted to a float at all (e.g. a string) -- verified
    directly against scipy: PPoly.__call__ with extrapolate=False returns
    NaN for an out-of-range NUMERIC value rather than raising. So an
    out-of-range (but numeric) focus does NOT hit this except block at all;
    it silently produces a NaN eq_factor and continues. That gap is noted
    separately (see the plan's findings list) -- this test only documents
    the one input shape that actually does raise.
    """
    seq = _bare_sequence()
    seq._conv_param = {'eq_curve_pp': _identity_pp(0.0, 10.0)}
    seq._focus_wrt_exit_plane = 'not-a-number'
    seq.transducer = SimpleNamespace(min_foc=0, max_foc=10)

    with pytest.raises(SystemExit):
        seq._calc_eq_factor()


# --- _calc_volt --------------------------------------------------------

def test_calc_volt_finds_x_for_each_amplitude():
    seq = _bare_sequence()
    seq._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}
    seq._ampl = [20, 80]

    seq._calc_volt()

    assert seq._volt == pytest.approx([20.0, 80.0])


def test_calc_volt_defaults_to_zero_when_amplitude_out_of_range():
    """Characterizes the fallback: when no x can be found for a given
    amplitude, _calc_volt does not raise -- it silently records 0 V for
    that entry."""
    seq = _bare_sequence()
    seq._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}
    seq._ampl = [999]  # above the pp's range

    seq._calc_volt()

    assert seq._volt == [0]


# --- _calc_ampl ----------------------------------------------------------
# calc_ampl = power_curve_pp(press[Pa] * eq_factor). Three outcomes when
# in range: normal (0-100 inclusive), clamped to 100 (exits), clamped to 0
# (does not exit). x_value outside the pp's domain entirely exits too.

def test_calc_ampl_rounds_normal_in_range_value():
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1.0
    seq._press = 50e-6  # MPa -> press_pa = 50, x_value = 50 * eq_factor = 50

    seq._calc_ampl()

    assert seq._ampl == [50.0]
    assert seq._input_press_mpa == seq._press
    assert seq._eq_press_mpa == pytest.approx(50e-6)


def test_calc_ampl_exits_when_x_value_above_pp_range():
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1.0
    seq._press = 2000e-6  # x_value = 2000, above the pp's max of 1000

    with pytest.raises(SystemExit):
        seq._calc_ampl()


def test_calc_ampl_exits_when_x_value_below_pp_range():
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1.0
    seq._press = -20e-6  # x_value = -20, below the pp's min of -10

    with pytest.raises(SystemExit):
        seq._calc_ampl()


def test_calc_ampl_clamps_to_100_and_exits_when_calculated_above_100():
    """calc_ampl > 100 (but still within the pp's domain) is clamped to
    100%, _press/_volt are recalculated from that clamped 100%, and only
    then does the method exit -- it never returns a >100 amplitude."""
    seq = _bare_sequence()
    seq._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    seq._eq_factor = 1.0
    seq._press = 150e-6  # x_value = 150 -> calc_ampl = 150 > 100
    seq._focus_wrt_exit_plane = 5

    with pytest.raises(SystemExit):
        seq._calc_ampl()

    assert seq._ampl == [100]
    assert seq._press == pytest.approx(1e-4)
    assert seq._volt == pytest.approx([100.0])


def test_calc_ampl_clamps_to_0_without_exiting_when_calculated_below_0():
    """calc_ampl < 0 (but still within the pp's domain) is clamped to 0%,
    _press/_volt are recalculated, and the method returns normally --
    unlike the >100 case, this is not treated as an error."""
    seq = _bare_sequence()
    seq._conv_param = {
        # pp(x) = x - 50, so an in-range x can still yield a negative y
        'power_curve_pp': PPoly(c=[[1.0], [-50.0]], x=[0.0, 100.0], extrapolate=False),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    seq._eq_factor = 1.0
    seq._press = 20e-6  # x_value = 20 -> calc_ampl = 20 - 50 = -30 < 0
    seq._focus_wrt_exit_plane = 5

    seq._calc_ampl()  # must not raise

    assert seq._ampl == [0]
    assert seq._press == pytest.approx(5e-5)
    assert seq._volt == pytest.approx([0.0])


# --- _calc_ampl_using_volt -------------------------------------------------
# Mirrors _calc_ampl but keyed off self._volt instead of self._press, and
# is NOT symmetric with it: below-range here just clamps to 0% and moves
# on (no exit), while _calc_ampl's below-range case above always exits.

def test_calc_ampl_using_volt_rounds_normal_in_range_value():
    seq = _bare_sequence()
    seq._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}
    seq._volt = [50]

    seq._calc_ampl_using_volt()

    assert seq._ampl == [50.0]


def test_calc_ampl_using_volt_clamps_to_0_without_exiting_when_below_range():
    seq = _bare_sequence()
    seq._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}
    seq._volt = [-20]  # below the pp's min of -10

    seq._calc_ampl_using_volt()  # must not raise

    assert seq._ampl == [0.0]


def test_calc_ampl_using_volt_clamps_to_100_and_exits_when_above_range():
    seq = _bare_sequence()
    seq._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    seq._eq_factor = 1.0
    seq._press = 0  # overwritten by the _calc_press() call triggered below
    seq._focus_wrt_exit_plane = 5
    seq._volt = [300]  # above the pp's max of 200

    with pytest.raises(SystemExit):
        seq._calc_ampl_using_volt()

    assert seq._ampl == [100]


# --- _calc_press -----------------------------------------------------------
# Inverse of _calc_ampl: finds the pressure that reproduces the given
# amplitude, then enforces the configured max free-water pressure.

def test_calc_press_computes_pressure_within_limit(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1.0
    seq._ampl = [50]

    seq._calc_press()

    assert seq._press == pytest.approx(5e-5)


def test_calc_press_exits_when_result_exceeds_configured_max(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1e-5  # inflates press_mpa well above the 1 MPa limit
    seq._ampl = [50]

    with pytest.raises(SystemExit):
        seq._calc_press()


def test_calc_press_sets_none_when_amplitude_out_of_range():
    """Characterizes the fallback: when no x can be found for the target
    amplitude, _calc_press does not raise -- it records _press as None."""
    seq = _bare_sequence()
    seq._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}
    seq._eq_factor = 1.0
    seq._ampl = [9999]  # above the pp's monotonic range

    seq._calc_press()

    assert seq._press is None
