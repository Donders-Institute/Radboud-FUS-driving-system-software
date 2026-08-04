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
import json
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


# --- get_ramp_shapes / pulse_ramp_shape / pulse_ramp_dur --------------------

def test_get_ramp_shapes_splits_config_value_on_newline(patch_config):
    patch_config.set('Ramp', 'Options', 'Rectangular - no ramping\nLinear\nTukey')
    seq = _bare_sequence()

    assert seq.get_ramp_shapes() == ['Rectangular - no ramping', 'Linear', 'Tukey']


def test_pulse_ramp_shape_setter_accepts_a_configured_option(patch_config):
    patch_config.set('Ramp', 'Options', 'Linear\nTukey')
    seq = _bare_sequence()
    seq._timing_param = {}

    seq.pulse_ramp_shape = 'Linear'

    assert seq.pulse_ramp_shape == 'Linear'


def test_pulse_ramp_shape_setter_exits_for_unavailable_option(patch_config):
    patch_config.set('Ramp', 'Options', 'Linear\nTukey')
    seq = _bare_sequence()
    seq._timing_param = {}

    with pytest.raises(SystemExit):
        seq.pulse_ramp_shape = 'Something else'


def test_pulse_ramp_dur_setter_accepts_zero():
    """check_nonzero=False for this setter -- 0 is a legitimate 'no ramp
    duration set yet' value, unlike the pulse_dur family above."""
    seq = _bare_sequence()
    seq._timing_param = {}

    seq.pulse_ramp_dur = 0

    assert seq.pulse_ramp_dur == 0


def test_pulse_ramp_dur_setter_rejects_negative():
    seq = _bare_sequence()
    seq._timing_param = {}

    with pytest.raises(SystemExit):
        seq.pulse_ramp_dur = -1


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
    # 'transducer' is itself a property whose setter expects a serial
    # number string (it does a config lookup) -- set the private
    # attribute it's backed by directly, same as everywhere else in this
    # file.
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=10)

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


# --- chosen_power / chosen_focus --------------------------------------------

def test_chosen_power_setter_accepts_a_configured_option(patch_config):
    patch_config.set('Power', 'Options', 'Global power [W]\nAmplitude [%]')
    seq = _bare_sequence()

    seq.chosen_power = 'Global power [W]'

    assert seq.chosen_power == 'Global power [W]'


def test_chosen_power_setter_exits_for_unavailable_option(patch_config):
    patch_config.set('Power', 'Options', 'Global power [W]\nAmplitude [%]')
    seq = _bare_sequence()

    with pytest.raises(SystemExit):
        seq.chosen_power = 'Something else'


def test_chosen_focus_setter_accepts_a_configured_option(patch_config):
    patch_config.set('Focus', 'Options', 'Focus wrt exit plane [mm]\nFocus wrt mid bowl [mm]')
    seq = _bare_sequence()

    seq.chosen_focus = 'Focus wrt exit plane [mm]'

    assert seq.chosen_focus == 'Focus wrt exit plane [mm]'


def test_chosen_focus_setter_exits_for_unavailable_option(patch_config):
    patch_config.set('Focus', 'Options', 'Focus wrt exit plane [mm]\nFocus wrt mid bowl [mm]')
    seq = _bare_sequence()

    with pytest.raises(SystemExit):
        seq.chosen_focus = 'Something else'


# --- global_power ------------------------------------------------------------
# No _calc_* orchestration here (unlike press/volt/ampl below) -- it just
# validates the value and records it, or exits if the option isn't available.

def test_global_power_setter_sets_value_when_option_available(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(power_options=['Global power [mW]'])

    seq.global_power = 5

    assert seq._global_power == 5
    assert seq._chosen_power == 'Global power [mW]'
    assert seq._ampl == 0  # reset at the top of the setter, and never re-set here


def test_global_power_setter_exits_when_option_unavailable(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(power_options=['Some other option'])

    with pytest.raises(SystemExit):
        seq.global_power = 5


# --- press -------------------------------------------------------------------
# Validates the power option is available, validates/limits the value, and
# THEN -- only if require_conv_eq and the combo is known -- recalculates
# amplitude and voltage (for logging) via the already-tested _calc_* methods.

def test_press_setter_without_conversion_sets_value_directly(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], require_conv_eq=False)

    seq.press = 0.5

    assert seq._press == 0.5
    assert seq._chosen_power == 'Max. pressure in free water [MPa]'


def test_press_setter_with_known_combo_triggers_conversion(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], require_conv_eq=True)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    seq._eq_factor = 1.0

    seq.press = 50e-6  # MPa -> press_pa = 50, x_value = 50 * eq_factor = 50

    # press setter stores the raw input value directly -- _calc_ampl/_calc_volt
    # are only triggered for logging purposes here, not to overwrite _press.
    assert seq._press == 50e-6
    assert seq._ampl == [50.0]
    assert seq._volt == pytest.approx([50.0])


def test_press_setter_exits_when_power_option_unavailable(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(power_options=['Some other option'], require_conv_eq=False)

    with pytest.raises(SystemExit):
        seq.press = 0.5


def test_press_setter_exits_when_combo_unknown_but_required(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], require_conv_eq=True)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    with pytest.raises(SystemExit):
        seq.press = 0.5


def test_press_setter_exits_when_above_configured_max(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], require_conv_eq=False)

    with pytest.raises(SystemExit):
        seq.press = 5


# --- volt ----------------------------------------------------------------
# Same shape as press, plus: requires engineering_mode, accepts scalar or
# list, and only calls _calc_press() (in addition to _calc_ampl_using_volt())
# when exactly one value was given.

def test_volt_setter_raises_when_engineering_mode_disabled():
    seq = _bare_sequence()
    seq._engineering_mode = False

    with pytest.raises(RuntimeError):
        seq.volt = 50


def test_volt_setter_without_conversion_sets_value_directly():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], require_conv_eq=False, available_ch=1)

    seq.volt = 50

    assert seq._volt == [50]
    assert seq._chosen_power == 'Voltage [V]'


def test_volt_setter_with_known_combo_triggers_conversion():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], require_conv_eq=True, available_ch=1)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    seq._eq_factor = 1.0

    seq.volt = 50  # single value -> _calc_ampl_using_volt() then _calc_press()

    assert seq._volt == [50]
    assert seq._ampl == [50.0]
    assert seq._press == pytest.approx(5e-5)


def test_volt_setter_with_multiple_values_skips_press_calculation():
    """When more than one voltage is given, _calc_press() is deliberately not
    called (pressure cannot be derived from a per-element voltage array)."""
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], require_conv_eq=True, available_ch=2)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    seq._eq_factor = 1.0
    seq._press = 'untouched'  # sentinel: must survive since _calc_press is skipped

    seq.volt = [50, 60]

    assert seq._volt == [50, 60]
    assert seq._ampl == pytest.approx([50.0, 60.0])
    assert seq._press == 'untouched'


def test_volt_setter_exits_when_power_option_unavailable():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(power_options=['Some other option'], require_conv_eq=False)

    with pytest.raises(SystemExit):
        seq.volt = 50


def test_volt_setter_exits_on_wrong_length_list():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], require_conv_eq=False, available_ch=4)

    with pytest.raises(SystemExit):
        seq.volt = [10, 20]  # neither 1 entry nor 4 (available_ch) entries


def test_volt_setter_exits_when_combo_unknown_but_required():
    """Mirrors test_press_setter_exits_when_combo_unknown_but_required --
    volt's setter has the identical 'require_conv_eq True but combo not in
    _equip_combos' -> sys.exit branch as press (this is the behavior ampl's
    setter deviates from, per the already-documented asymmetry)."""
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(power_options=['Voltage [V]'], require_conv_eq=True,
                                       available_ch=1)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    with pytest.raises(SystemExit):
        seq.volt = 50


# --- ampl ------------------------------------------------------------------
# Mirrors volt (engineering_mode guard, scalar-or-list, wrong-length exit),
# but its handling of an unavailable power option AND of an unknown-but
# -required combo both diverge from press/volt -- see the two tests below
# documenting each asymmetry.

def test_ampl_setter_raises_when_engineering_mode_disabled():
    seq = _bare_sequence()
    seq._engineering_mode = False

    with pytest.raises(RuntimeError):
        seq.ampl = 50


def test_ampl_setter_without_conversion_sets_value_directly():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], require_conv_eq=False, available_ch=1)

    seq.ampl = 50

    assert seq._ampl == [50]
    assert seq._chosen_power == 'Amplitude [%]'


def test_ampl_setter_with_known_combo_triggers_conversion():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], require_conv_eq=True, available_ch=1)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    seq._eq_factor = 1.0

    seq.ampl = 50  # single value -> _calc_volt() then _calc_press()

    assert seq._ampl == [50]
    assert seq._volt == pytest.approx([50.0])
    assert seq._press == pytest.approx(5e-5)


def test_ampl_setter_exits_on_wrong_length_list():
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], require_conv_eq=False, available_ch=4)

    with pytest.raises(SystemExit):
        seq.ampl = [10, 20]  # neither 1 entry nor 4 (available_ch) entries


def test_ampl_setter_silently_noops_when_power_option_unavailable():
    """FINDING: unlike press's and volt's setters, which both have an
    explicit `else: sys.exit(...)` when the power option isn't in
    driving_sys.power_options (sequence.py lines ~682-687 and ~770-775),
    ampl's setter (~line 806) has NO else-branch at all for that same
    'if power_option in self.driving_sys.power_options:' check. If the
    option is unavailable, the setter just falls off the end having already
    reset self._ampl to 0 at the top -- it neither sets the requested value
    nor raises/logs an error. This looks like a missing-else bug relative
    to its two structurally-identical siblings; characterized here rather
    than fixed, since this task is test-only."""
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(power_options=['Some other option'], available_ch=1)

    seq.ampl = 50  # must not raise, unlike press/volt in the same situation

    assert seq._ampl == 0  # reset value from the top of the setter, never actually set to 50


def test_ampl_setter_does_not_exit_when_combo_unknown_but_required():
    """FINDING: press's and volt's setters both sys.exit when
    require_conv_eq is True but the combo is unknown ('Conversion
    equations unknown but required for ...', a logger.critical + sys.exit).
    ampl's setter (sequence.py ~line 849-851) hits the same situation but
    only logger.debug()s a highly similar message ('Conversion equations
    unknown for ...') and returns normally -- no exit. Another asymmetry
    among the three otherwise-parallel setters, characterized here."""
    seq = _bare_sequence()
    seq._engineering_mode = True
    seq._driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], require_conv_eq=True, available_ch=1)
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    seq.ampl = 50  # must not raise, unlike press/volt in the same situation

    assert seq._ampl == [50]


# --- focus_wrt_exit_plane ----------------------------------------------------

def test_focus_wrt_exit_plane_setter_without_conversion_uses_exit_plane_offset():
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=False)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')

    seq.focus_wrt_exit_plane = 20

    assert seq.focus_wrt_exit_plane == 20
    assert seq.focus_wrt_mid_bowl == 25  # focus + exit_plane_dist


def test_focus_wrt_exit_plane_setter_with_known_combo_uses_focus_curve_and_recalculates():
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    seq._press = 2e-6  # MPa -> press_pa = 2

    seq.focus_wrt_exit_plane = 20

    assert seq.focus_wrt_exit_plane == 20
    assert seq.focus_wrt_mid_bowl == pytest.approx(20.0)  # focus_curve_pp(20) via identity
    assert float(seq._eq_factor) == pytest.approx(20.0)  # eq_curve_pp(20) via identity
    # x_value = press_pa(2) * eq_factor(20) = 40 -> power_curve_pp identity -> ampl = 40
    assert seq._ampl == [40.0]
    assert seq._volt == pytest.approx([40.0])


def test_focus_wrt_exit_plane_setter_exits_when_out_of_transducer_range():
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=False)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')

    with pytest.raises(SystemExit):
        seq.focus_wrt_exit_plane = 200


def test_focus_wrt_exit_plane_setter_exits_when_combo_unknown_but_required():
    """The first block only warns and falls back when the combo is unknown;
    it's the second, unconditional block further down that always
    sys.exit()s in this situation -- so the fallback state from the first
    block is still visible after the exit is caught."""
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    with pytest.raises(SystemExit):
        seq.focus_wrt_exit_plane = 20

    assert seq.focus_wrt_exit_plane == 20
    assert seq.focus_wrt_mid_bowl == 25  # fallback: focus + exit_plane_dist


# --- focus_wrt_mid_bowl / set_focus_wrt_mid_bowl -----------------------------
# focus_wrt_mid_bowl's setter and set_focus_wrt_mid_bowl() are near-duplicates
# of each other (same validation, same find_x_for_y_in_pp usage, same
# fallback and range-check logic) -- the only difference is that
# set_focus_wrt_mid_bowl additionally gates its final recalculation block on
# the no_ampl_input parameter, tested separately below via a mocker spy.

def test_focus_wrt_mid_bowl_setter_without_conversion_uses_exit_plane_offset():
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=False)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')

    seq.focus_wrt_mid_bowl = 25

    assert seq.focus_wrt_mid_bowl == 25
    assert seq.focus_wrt_exit_plane == 20  # focus - exit_plane_dist


def test_focus_wrt_mid_bowl_setter_with_known_combo_finds_x_via_pp_and_recalculates():
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    seq._press = 2e-6

    seq.focus_wrt_mid_bowl = 20  # within focus_curve_pp's [0, 100] range -> found

    assert seq.focus_wrt_exit_plane == pytest.approx(20.0)
    assert seq.focus_wrt_mid_bowl == 20
    assert float(seq._eq_factor) == pytest.approx(20.0)
    assert seq._ampl == [40.0]
    assert seq._volt == pytest.approx([40.0])


def test_focus_wrt_mid_bowl_setter_falls_back_when_x_not_found():
    """When find_x_for_y_in_pp can't find an x value for the target
    focus_wrt_mid_bowl (target outside the focus_curve_pp's y-range), the
    setter logs a warning and falls back to focus - exit_plane_dist rather
    than raising."""
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=-100, max_foc=1000, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(-1000.0, 1000.0),
        'power_curve_pp': _identity_pp(-1000.0, 1000.0),
        'volt_curve_pp': _identity_pp(-1000.0, 1000.0),
    }
    seq._press = 0

    seq.focus_wrt_mid_bowl = 500  # outside focus_curve_pp's [0, 100] y-range -> not found

    assert seq.focus_wrt_exit_plane == 495  # fallback: focus - exit_plane_dist
    assert seq._ampl == [0.0]
    assert seq._volt == pytest.approx([0.0])


def test_focus_wrt_mid_bowl_setter_exits_when_combo_unknown_but_required():
    """
    Mirrors set_focus_wrt_mid_bowl's equivalent test below. This property
    setter has no no_ampl_input escape hatch, so with require_conv_eq=True
    and an unknown combo it always exits -- unlike set_focus_wrt_mid_bowl,
    which can skip that exit via no_ampl_input=False.

    Note: a repo-wide grep (including every standalone example script)
    shows this setter -- and set_focus_wrt_mid_bowl() -- have ZERO active
    call sites anywhere; every real script sets focus_wrt_exit_plane
    instead, and only reads focus_wrt_mid_bowl (the getter, used by
    igt_ds.py's _set_phases). Added for symmetry/coverage, not because a
    live usage was found needing it -- see the plan's no_ampl_input finding
    for whether this whole direct-bowl-middle setter API is still needed.
    """
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    with pytest.raises(SystemExit):
        seq.focus_wrt_mid_bowl = 20


def test_set_focus_wrt_mid_bowl_no_ampl_input_true_triggers_recalculation(mocker):
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {'focus_curve_pp': _identity_pp(0.0, 100.0)}
    seq._ampl = [50.0]
    seq._volt = [10.0]
    seq._press = 0.5
    seq._eq_factor = 1.0  # _calc_eq_factor is mocked below, so it never gets (re)set otherwise

    spy_eq_factor = mocker.patch.object(seq, '_calc_eq_factor')
    mocker.patch.object(seq, '_calc_ampl')
    mocker.patch.object(seq, '_calc_volt')

    seq.set_focus_wrt_mid_bowl(20, no_ampl_input=True)

    spy_eq_factor.assert_called_once()


def test_set_focus_wrt_mid_bowl_no_ampl_input_false_skips_recalculation(mocker):
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = ['combo1']
    seq._conv_param = {'focus_curve_pp': _identity_pp(0.0, 100.0)}
    seq._ampl = [50.0]
    seq._volt = [10.0]
    seq._press = 0.5

    spy_eq_factor = mocker.patch.object(seq, '_calc_eq_factor')
    mocker.patch.object(seq, '_calc_ampl')
    mocker.patch.object(seq, '_calc_volt')

    seq.set_focus_wrt_mid_bowl(20, no_ampl_input=False)

    spy_eq_factor.assert_not_called()


def test_set_focus_wrt_mid_bowl_exits_when_combo_unknown_and_no_ampl_input_true():
    """
    With no_ampl_input=True (the default) and require_conv_eq=True but the
    combo unknown, this method hits the SAME combo-unknown condition
    twice: first inside the is_validated block (only warns + falls back to
    focus - exit_plane_dist, does not exit), then again in the
    no_ampl_input-gated recalculation block at the end (which does exit).
    Net effect: a SystemExit, after the fallback focus value was already
    computed.
    """
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    with pytest.raises(SystemExit):
        seq.set_focus_wrt_mid_bowl(20, no_ampl_input=True)


def test_set_focus_wrt_mid_bowl_does_not_exit_when_combo_unknown_and_no_ampl_input_false():
    """no_ampl_input=False short-circuits 'if no_ampl_input and require_conv_eq:'
    entirely, so the combo-unknown sys.exit at the end never runs here --
    only the mid-function warning+fallback does."""
    seq = _bare_sequence()
    seq._driving_sys = SimpleNamespace(require_conv_eq=True)
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    seq._ds_tran_combo = 'combo1'
    seq._equip_combos = []  # combo unknown

    seq.set_focus_wrt_mid_bowl(20, no_ampl_input=False)  # must not raise

    assert seq.focus_wrt_exit_plane == 15  # fallback: focus - exit_plane_dist


# --- _update_conv_param -----------------------------------------------------

def _write_identity_fit_json(tmp_path, name, x0, x1):
    """
    Writes a synthetic single-piece FitParams JSON file to tmp_path whose
    resulting PPoly is the identity function pp(x) == x over [x0, x1] --
    same convention as _identity_pp above (c=[[1.0], [x0]]) -- and returns
    its absolute path as a string, suitable for passing straight to
    extract_and_define_pp/_update_conv_param via patch_config (see the
    module docstring's note on absolute tmp_path resolution).
    """
    fit_params = {
        "xTransform": "none",
        "FitParams": {"breaks": [x0, x1], "coefs": [[1.0, x0]]},
    }
    path = tmp_path / name
    path.write_text(json.dumps(fit_params))
    return str(path)


def test_update_conv_param_populates_all_four_curves_and_updates_transducer_range(
        tmp_path, patch_config):
    seq = _bare_sequence()
    seq._ds_tran_combo = 'combo1'
    seq._transducer = SimpleNamespace(min_foc=0, max_foc=0)
    seq._focus_wrt_exit_plane = 20
    seq._press = 2e-6  # MPa -> press_pa = 2

    eq_file = _write_identity_fit_json(tmp_path, 'eq.json', 0.0, 100.0)
    focus_file = _write_identity_fit_json(tmp_path, 'focus.json', 0.0, 100.0)
    power_file = _write_identity_fit_json(tmp_path, 'power.json', -10.0, 1000.0)
    volt_file = _write_identity_fit_json(tmp_path, 'volt.json', -10.0, 200.0)

    section = 'Equipment.Combination.combo1'
    patch_config.set(section, 'EqualizationCurveFit json file', eq_file)
    patch_config.set(section, 'FocusCurveFit json file', focus_file)
    patch_config.set(section, 'PowerCurveFit json file', power_file)
    patch_config.set(section, 'VoltageCurveFit json file', volt_file)

    seq._update_conv_param()

    assert seq._conv_param['eq_curve_pp'] is not None
    assert seq._conv_param['focus_curve_pp'] is not None
    assert seq._conv_param['power_curve_pp'] is not None
    assert seq._conv_param['volt_curve_pp'] is not None

    # transducer.min_foc/max_foc are (re)set from the equalization curve's breaks
    assert seq.transducer.min_foc == 0.0
    assert seq.transducer.max_foc == 100.0

    # eq_curve_pp(focus_wrt_exit_plane=20) -> eq_factor, via identity
    assert float(seq._eq_factor) == pytest.approx(20.0)
    # x_value = press_pa(2) * eq_factor(20) = 40 -> power_curve_pp identity -> ampl = 40
    assert seq._ampl == [40.0]
    assert seq._volt == pytest.approx([40.0])
