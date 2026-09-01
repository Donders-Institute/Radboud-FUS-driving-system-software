# -*- coding: utf-8 -*-
"""
Characterization tests for fus_driving_systems.transducer_slot.TransducerSlot.

This is where all of TUSProtocol's former power/focus test coverage moved to in Phase 3 (multi-
transducer slots) -- the logic itself moved essentially verbatim, so most assertions are
unchanged; only the calc methods' calling convention changed (explicit parameters and return
values instead of implicit self._X reads/writes -- see the class docstring/plan for why).

Every test here builds the instance with TransducerSlot.__new__(TransducerSlot) (bypassing
__init__ entirely) and sets only the private attributes the method-under-test actually reads,
same pattern as test_tus_protocol_class.py.
"""
import json
from types import SimpleNamespace

import pytest
from scipy.interpolate import PPoly

from fus_driving_systems.transducer_slot import TransducerSlot


def _bare_slot():
    """A TransducerSlot instance with __init__ skipped entirely."""
    return TransducerSlot.__new__(TransducerSlot)


def _identity_pp(a, b):
    """A piecewise polynomial with pp(x) == x over the domain [a, b]."""
    return PPoly(c=[[1.0], [a]], x=[a, b], extrapolate=False)


# --- _calc_eq_factor -------------------------------------------------------

def test_calc_eq_factor_evaluates_pp_at_focus_wrt_exit_plane():
    slot = _bare_slot()
    slot._conv_param = {'eq_curve_pp': _identity_pp(0.0, 10.0)}

    eq_factor = slot._calc_eq_factor(5)

    assert float(eq_factor) == pytest.approx(5.0)


def test_calc_eq_factor_exits_when_focus_is_not_numeric():
    """
    A non-numeric focus_wrt_exit_plane (e.g. a string) raises TypeError inside
    safe_evaluate_pp's own range comparison ('<' unsupported between str and float) -- caught
    and turned into a clean sys.exit(), same as the out-of-range case below.
    """
    slot = _bare_slot()
    slot._conv_param = {'eq_curve_pp': _identity_pp(0.0, 10.0)}
    # 'transducer' is itself a property whose setter expects a serial
    # number string (it does a config lookup) -- set the private
    # attribute it's backed by directly, same as everywhere else in this
    # file.
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=10)

    with pytest.raises(SystemExit):
        slot._calc_eq_factor('not-a-number')


def test_calc_eq_factor_exits_when_focus_is_out_of_range():
    """Fixes a previously-undetected gap (issue #93): PPoly.__call__ with extrapolate=False
    returns NaN for an out-of-range numeric value rather than raising -- the old bare call plus
    `except ValueError` never actually caught this, so eq_factor silently became NaN. Now uses
    safe_evaluate_pp to detect the out-of-range case explicitly and exit."""
    slot = _bare_slot()
    slot._conv_param = {'eq_curve_pp': _identity_pp(0.0, 10.0)}

    with pytest.raises(SystemExit):
        slot._calc_eq_factor(50)  # outside the curve's [0, 10] domain


# --- _convert_ampl_to_volt --------------------------------------------------------

def test_convert_ampl_to_volt_finds_x_for_each_amplitude():
    slot = _bare_slot()
    slot._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}

    volt = slot._convert_ampl_to_volt([20, 80])

    assert volt == pytest.approx([20.0, 80.0])


def test_convert_ampl_to_volt_records_none_when_amplitude_out_of_range():
    """BUGFIX: when no x can be found for a given amplitude, _convert_ampl_to_volt does not
    raise -- it records None for that entry, not 0 (0 would look like a genuine, calculated
    voltage to any later read of self._volt, when really no value could be found at all)."""
    slot = _bare_slot()
    slot._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}

    volt = slot._convert_ampl_to_volt([999])  # above the pp's range

    assert volt == [None]


# --- _convert_press_to_ampl ----------------------------------------------------------
# calc_ampl = power_curve_pp(press[Pa] * eq_factor). Three outcomes when
# in range: normal (0-100 inclusive), clamped to 100 (exits), clamped to 0
# (does not exit). x_value outside the pp's domain entirely exits too.
# _convert_press_to_ampl no longer reads/writes self._X -- it takes press/eq_factor as
# explicit parameters and returns a dict of results, so these tests check
# the returned dict directly rather than instance state.

def test_convert_press_to_ampl_rounds_normal_in_range_value():
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    # MPa -> press_pa = 50, x_value = 50 * eq_factor = 50
    result = slot._convert_press_to_ampl(50e-6, 1.0)

    assert result['ampl'] == [50.0]
    assert result['input_press_mpa'] == 50e-6
    assert result['eq_press_mpa'] == pytest.approx(50e-6)


def test_convert_press_to_ampl_exits_when_x_value_above_pp_range():
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    with pytest.raises(SystemExit):
        slot._convert_press_to_ampl(2000e-6, 1.0)  # x_value = 2000, above the pp's max of 1000


def test_convert_press_to_ampl_exits_when_x_value_below_pp_range():
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    with pytest.raises(SystemExit):
        slot._convert_press_to_ampl(-20e-6, 1.0)  # x_value = -20, below the pp's min of -10


def test_convert_press_to_ampl_clamps_to_100_and_exits_when_calculated_above_100():
    """calc_ampl > 100 (but still within the pp's domain) is clamped to 100% just long enough
    to compute the press/volt shown in the error message, then the method exits without
    returning anything -- unlike the pre-Phase-3 self-mutating version, there is no self._ampl
    left behind to clear: the setters that call this now reset self._ampl to None themselves
    before calling, precisely because this function can no longer do it on their behalf."""
    slot = _bare_slot()
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }

    with pytest.raises(SystemExit):
        slot._convert_press_to_ampl(150e-6, 1.0)  # x_value = 150 -> calc_ampl = 150 > 100


def test_convert_press_to_ampl_clamps_to_0_without_exiting_when_calculated_below_0():
    """calc_ampl < 0 (but still within the pp's domain) is clamped to 0%, and 'press' is kept
    exactly as given rather than re-derived through the curve's own inverse -- unlike the >100
    case, this is not treated as an error. Correcting volt for this same case is left to the
    caller (every caller already recomputes volt from the returned ampl unconditionally)."""
    slot = _bare_slot()
    slot._conv_param = {
        # pp(x) = x - 50, so an in-range x can still yield a negative y
        'power_curve_pp': PPoly(c=[[1.0], [-50.0]], x=[0.0, 100.0], extrapolate=False),
    }

    # x_value = 20 -> calc_ampl = 20 - 50 = -30 < 0
    result = slot._convert_press_to_ampl(20e-6, 1.0)

    assert result['ampl'] == [0]
    assert result['press'] == 20e-6  # kept exactly as given, not re-derived


def test_convert_press_to_ampl_keeps_press_at_exactly_zero_when_curve_dips_negative_at_zero():
    """The specific case that originally motivated the fix above: a press of exactly 0 must
    come back as press=0 too, not some small non-zero artifact from re-deriving it through the
    curve's own imprecision near the origin -- press is already guaranteed non-negative before
    this method is ever called (see press's own setter's validate_value(..., check_pos=True,
    ...)), so there is no "genuinely wrong request" case here for keeping it as-is to mask."""
    slot = _bare_slot()
    slot._conv_param = {
        # pp(x) = x - 5, so even x=0 (the domain's own minimum) yields a negative y --
        # mirrors a real calibration curve that doesn't pass exactly through the origin.
        'power_curve_pp': PPoly(c=[[1.0], [-5.0]], x=[0.0, 100.0], extrapolate=False),
    }

    result = slot._convert_press_to_ampl(0, 1.0)  # x_value = 0 -> calc_ampl = 0 - 5 = -5 < 0

    assert result['ampl'] == [0]
    assert result['press'] == 0


# --- _convert_volt_to_ampl -------------------------------------------------
# Mirrors _convert_press_to_ampl exactly, keyed off volt instead of press: a voltage outside
# volt_curve_pp's own domain always exits (above and below alike), while an in-range voltage
# whose curve-fit result spills slightly past 0/100 is clamped (100 -> exit, 0 -> proceed).

def test_convert_volt_to_ampl_rounds_normal_in_range_value():
    slot = _bare_slot()
    slot._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}

    ampl = slot._convert_volt_to_ampl([50], 1.0)

    assert ampl == [50.0]


def test_convert_volt_to_ampl_exits_when_volt_is_below_pp_range():
    slot = _bare_slot()
    slot._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}

    with pytest.raises(SystemExit):
        slot._convert_volt_to_ampl([-20], 1.0)  # below the pp's min of -10


def test_convert_volt_to_ampl_exits_when_volt_is_above_pp_range():
    slot = _bare_slot()
    slot._conv_param = {'volt_curve_pp': _identity_pp(-10.0, 200.0)}

    with pytest.raises(SystemExit):
        slot._convert_volt_to_ampl([300], 1.0)  # above the pp's max of 200


def test_convert_volt_to_ampl_clamps_to_100_and_exits_when_calculated_above_100():
    """Mirrors test_convert_press_to_ampl_clamps_to_100_and_exits_when_calculated_above_100 --
    an in-range voltage whose curve-fit result exceeds 100%, not a voltage outside the curve's
    own domain
    (that's the above_range case above, which now exits before ever reaching this check).
    Nothing to clear here either, since this is a pure function; the caller (volt's setter)
    resets its own self._ampl to None before calling, for the same reason."""
    slot = _bare_slot()
    slot._conv_param = {
        # pp(x) = x + 50, so an in-range x can still yield a >100 y
        'volt_curve_pp': PPoly(c=[[1.0], [50.0]], x=[0.0, 100.0], extrapolate=False),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }

    with pytest.raises(SystemExit):
        slot._convert_volt_to_ampl([60], 1.0)  # in range -> calc_ampl = 60 + 50 = 110 > 100


def test_convert_volt_to_ampl_clamps_to_0_without_exiting_when_calculated_below_0():
    """Mirrors test_convert_press_to_ampl_clamps_to_0_without_exiting_when_calculated_below_0 --
    an in-range voltage whose curve-fit result dips slightly below 0%, not a voltage outside the
    curve's own domain (that's the below_range case above, which now exits before ever reaching
    this check)."""
    slot = _bare_slot()
    slot._conv_param = {
        # pp(x) = x - 50, so an in-range x can still yield a negative y
        'volt_curve_pp': PPoly(c=[[1.0], [-50.0]], x=[0.0, 100.0], extrapolate=False),
    }

    ampl = slot._convert_volt_to_ampl([20], 1.0)  # in range -> calc_ampl = 20 - 50 = -30 < 0

    assert ampl == [0.0]


# --- _convert_ampl_to_press -----------------------------------------------------------
# Inverse of _convert_press_to_ampl: finds the pressure that reproduces the given
# amplitude, then enforces the configured max free-water pressure.

def test_convert_ampl_to_press_computes_pressure_within_limit(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    press = slot._convert_ampl_to_press([50], 1.0)

    assert press == pytest.approx(5e-5)


def test_convert_ampl_to_press_accepts_pressure_exactly_at_the_configured_max(patch_config):
    """The check is strict '>' (see _convert_ampl_to_press's own code), not '>=' -- a derived
    pressure exactly at the configured limit must be accepted, not rejected. The two tests
    around this one only ever use comfortably-within or well-over values; this is the one that
    actually proves the boundary itself, for THE software safety limit."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', str(5e-5))
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    press = slot._convert_ampl_to_press([50], 1.0)  # produces exactly 5e-5 MPa

    assert press == pytest.approx(5e-5)


def test_convert_ampl_to_press_exits_when_result_exceeds_configured_max(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    with pytest.raises(SystemExit):
        slot._convert_ampl_to_press([50], 1e-5)  # inflates press_mpa well above the 1 MPa limit


def test_convert_ampl_to_press_returns_none_when_amplitude_out_of_range():
    """Characterizes the fallback: when no x can be found for the target
    amplitude, _convert_ampl_to_press does not raise -- it returns None."""
    slot = _bare_slot()
    slot._conv_param = {'power_curve_pp': _identity_pp(-10.0, 1000.0)}

    press = slot._convert_ampl_to_press([9999], 1.0)  # above the pp's monotonic range
    assert press is None


def test_convert_ampl_to_press_exits_when_given_more_than_one_amplitude_value():
    """A multi-channel amplitude array has no one pressure that represents it -- rejected
    outright rather than silently deriving a value from just the first entry."""
    slot = _bare_slot()

    with pytest.raises(SystemExit, match='2 entries'):
        slot._convert_ampl_to_press([50, 60], 1.0)


# --- _non_engineering_options -------------------------------------------------
# Used to make an "engineering_mode required" RuntimeError actionable -- naming a hardcoded
# alternative could be wrong (not offered by this driving system, or also engineering-only for
# this institution), so it's computed from the driving system's own options instead.

def test_non_engineering_options_excludes_engineering_only_power_options(patch_config):
    patch_config.set('Power', 'Engineering-only options', 'Voltage [V]\nAmplitude [%]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(power_options=[
        'Global power [mW]', 'Max. pressure in free water [MPa]', 'Voltage [V]',
        'Amplitude [%]'])

    assert slot._non_engineering_options('Power') == [
        'Global power [mW]', 'Max. pressure in free water [MPa]']


def test_non_engineering_options_excludes_engineering_only_focus_options(patch_config):
    patch_config.set('Focus', 'Engineering-only options', 'Focus wrt mid bowl [mm]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'])

    assert slot._non_engineering_options('Focus') == ['Focus wrt exit plane [mm]']


def test_volt_setter_names_available_alternatives_when_engineering_mode_disabled(patch_config):
    """The message must name what's actually available for THIS driving system, not a
    hardcoded alternative -- e.g. suggesting press would be wrong if this driving system
    doesn't even offer it, or if it's also configured as engineering-only."""
    patch_config.set('Power', 'Engineering-only options', 'Voltage [V]\nAmplitude [%]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=[
        'Global power [mW]', 'Max. pressure in free water [MPa]', 'Voltage [V]',
        'Amplitude [%]'])

    with pytest.raises(RuntimeError) as exc_info:
        slot._set_volt(50)
    message = str(exc_info.value)
    assert 'Global power [mW]' in message
    assert 'Max. pressure in free water [MPa]' in message
    assert 'Voltage [V]' not in message.split(':', 1)[1]  # not offered as its own alternative


# --- chosen_power / chosen_focus ---------------------------------------------
# Read-only -- there is no setter for either; both are only ever set as a side effect of
# _set_power()/_set_focus() (see the tests for those below), never independently.

# --- global_power ------------------------------------------------------------
# No _calc_* orchestration here (unlike press/volt/ampl below) -- it just
# validates the value and records it, or exits if the option isn't available.

def test_global_power_setter_raises_when_configured_as_engineering_only(patch_config):
    """Which power options are engineering-only is a config-driven institutional policy --
    global power is available to everyone by default, but an institution can gate it too."""
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    patch_config.set('Power', 'Engineering-only options', 'Global power [mW]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=['Global power [mW]'])

    with pytest.raises(RuntimeError):
        slot._set_global_power(5)


def test_global_power_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Global power is available by default, and stays available when explicitly cleared
    from Engineering-only options."""
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    patch_config.set('Power', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=['Global power [mW]'])

    slot._set_global_power(5)  # must not raise

    assert slot._global_power == 5


def test_global_power_setter_sets_value_when_option_available(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(power_options=['Global power [mW]'])

    slot._set_global_power(5)

    assert slot._global_power == 5
    assert slot._chosen_power == 'Global power [mW]'
    # reset to None at the top of the setter, and never re-set here -- 0 would look like a
    # genuine, computed value for a power option that isn't active right now.
    assert slot._ampl is None
    assert slot._press is None
    assert slot._volt is None


def test_global_power_setter_clears_stale_press_diagnostics_from_a_previous_power_option(
        patch_config):
    """Regression test: _input_press_mpa/_eq_press_mpa/_calculated_ampl are only ever populated
    by press's own setter (as a side effect of _convert_press_to_ampl()) -- _reset_power_fields()
    used to leave them untouched, so switching to a different power option afterward left them
    describing the previous, no-longer-active press value instead of being cleared like every
    other power field."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]', 'Global power [mW]'],
        native_power_params=['Amplitude [%]'])
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    slot._eq_factor = 1.0

    slot._set_press(50e-6)
    assert slot.input_press_mpa is not None  # sanity check: the setter did populate it

    slot._set_global_power(5)

    assert slot.input_press_mpa is None
    assert slot.eq_press_mpa is None
    assert slot.calculated_ampl is None


def test_global_power_setter_exits_when_option_unavailable(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(power_options=['Some other option'])

    with pytest.raises(SystemExit):
        slot._set_global_power(5)


# --- press -------------------------------------------------------------------
# Validates the power option is available, validates/limits the value, and THEN
# -- only if press isn't this driving system's native power parameter AND a
# calibration is active -- recalculates amplitude and voltage (for logging)
# via the already-tested _calc_* methods. If press is native, this is always
# settable; if it isn't and no calibration is active, the setter exits.

def test_press_setter_raises_when_configured_as_engineering_only(patch_config):
    """Which power options are engineering-only is a config-driven institutional policy --
    press is available to everyone by default, but an institution can choose to gate it too."""
    patch_config.set('Power', 'Engineering-only options', 'Max. pressure in free water [MPa]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=['Max. pressure in free water [MPa]'])

    with pytest.raises(RuntimeError):
        slot._set_press(0.5)


def test_press_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Press is available by default, and stays available when explicitly cleared from
    Engineering-only options."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    patch_config.set('Power', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'])
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_press(0.5)  # must not raise

    assert slot._press == 0.5


def test_press_setter_without_conversion_sets_value_directly(patch_config):
    """Press is this (hypothetical) driving system's own native power parameter, so no
    calibration is ever needed to set it."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'])
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_press(0.5)

    assert slot._press == 0.5
    assert slot._chosen_power == 'Max. pressure in free water [MPa]'


def test_press_setter_with_known_combo_triggers_conversion(patch_config):
    """Press is non-native (amplitude is), so converting it requires an active calibration --
    provided here via a real 'Equipment.Combination.*' config section, matching IGT."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], native_power_params=['Amplitude [%]'])
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    slot._eq_factor = 1.0

    slot._set_press(50e-6)  # MPa -> press_pa = 50, x_value = 50 * eq_factor = 50

    # press setter stores the raw input value directly -- _convert_press_to_ampl/
    # _convert_ampl_to_volt are only triggered for logging purposes here, not to overwrite
    # _press.
    assert slot._press == 50e-6
    assert slot._ampl == [50.0]
    assert slot._volt == pytest.approx([50.0])


def test_press_setter_exits_when_power_option_unavailable(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(power_options=['Some other option'])

    with pytest.raises(SystemExit):
        slot._set_press(0.5)


def test_press_setter_exits_when_combo_unknown_but_required(patch_config):
    """Press is non-native and no 'Equipment.Combination.*' section exists for this combo at
    all -- _combo_is_active() is False, so there's no way to convert to amplitude."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], native_power_params=['Amplitude [%]'])
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit):
        slot._set_press(0.5)


def test_press_setter_exits_when_above_configured_max(patch_config):
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'])

    with pytest.raises(SystemExit):
        slot._set_press(5)


def test_press_setter_accepts_pressure_exactly_at_the_configured_max(patch_config):
    """The check is strict '>' (see _set_press's own code), not '>=' -- a value exactly at the
    configured limit must be accepted, not rejected. Every other test around this check uses a
    value comfortably within or well over the limit; this is the one that actually proves the
    intentional boundary semantics, for THE software safety limit."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'])
    slot._ds_tran_combo = None  # native power option -- no active combo needed

    slot._set_press(1)  # exactly at the configured max -- must not raise

    assert slot._press == 1


def test_press_setter_reports_missing_calibration_before_value_specific_errors(patch_config):
    """Fail fast: whether this driving system can accept press at all is checked before
    anything about the specific value (is_validated, the max-pressure limit) -- so a value
    that's *both* above the configured max *and* unconvertible (non-native, no active combo)
    surfaces the calibration error, not the (less relevant, in this case) max-pressure one."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Amplitude [%]'])
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit, match='No active calibration available'):
        slot._set_press(5)  # also above the configured max of 1 -- must not be the error surfaced


def test_press_setter_exits_and_clears_ampl_when_calculated_amplitude_exceeds_100(patch_config):
    """_convert_press_to_ampl() itself no longer has any self._ampl to clear on this exit (it's
    a pure function now) -- the setter resets self._ampl to None before calling it, so this
    end-to-end
    guarantee (a rejected request never leaves a stale, valid-looking amplitude behind) survives
    the Phase 3 refactor even though the low-level unit test for it moved to a plain return-value
    check (see test_convert_press_to_ampl_clamps_to_100_and_exits_when_calculated_above_100)."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '10')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'], native_power_params=['Amplitude [%]'])
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    slot._eq_factor = 1.0
    slot._ampl = ['stale']

    with pytest.raises(SystemExit):
        slot._set_press(150e-6)  # x_value = 150 -> calc_ampl = 150 > 100

    assert slot._ampl is None


# --- volt ----------------------------------------------------------------
# Same shape as press, plus: requires engineering_mode, accepts scalar or
# list, and only calls _convert_ampl_to_press() (in addition to _convert_volt_to_ampl())
# when exactly one value was given.

def test_volt_setter_raises_when_engineering_mode_disabled(patch_config):
    patch_config.set('Power', 'Engineering-only options', 'Voltage [V]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=['Voltage [V]'])

    with pytest.raises(RuntimeError):
        slot._set_volt(50)


def test_volt_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Which options are engineering-only is a config-driven institutional policy, not
    hardcoded -- an institution that doesn't list voltage here can set it directly."""
    patch_config.set('Power', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Voltage [V]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_volt(50)  # must not raise

    assert slot._volt == [50]


def test_volt_setter_without_conversion_sets_value_directly():
    """Voltage is this (hypothetical) driving system's own native power parameter, so no
    calibration is ever needed to set it -- matches CITRUS."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Voltage [V]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_volt(50)

    assert slot._volt == [50]
    assert slot._chosen_power == 'Voltage [V]'


def test_volt_setter_with_known_combo_triggers_conversion(patch_config):
    """Voltage is non-native (amplitude is), so converting it requires an active calibration --
    matches IGT."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    slot._eq_factor = 1.0

    slot._set_volt(50)  # single value -> _convert_volt_to_ampl() then _convert_ampl_to_press()

    assert slot._volt == [50]
    assert slot._ampl == [50.0]
    assert slot._press == pytest.approx(5e-5)


def test_volt_setter_logging_only_press_failure_does_not_raise(patch_config):
    """_convert_ampl_to_press() is called here purely to log a derived pressure value -- the
    real value being sent to hardware (voltage/amplitude) was already set independently above.
    If the power curve's domain doesn't cover the resulting amplitude,
    _convert_ampl_to_press() returns None, which must not crash the debug log line right after
    (see format_or_unavailable)."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        # power_curve_pp's domain doesn't cover the resulting amplitude (50) --
        # find_x_for_y_in_pp() inside _convert_ampl_to_press() won't find a match.
        'power_curve_pp': _identity_pp(80.0, 1000.0),
    }
    slot._eq_factor = 1.0

    slot._set_volt(50)  # must not raise

    assert slot._volt == [50]
    assert slot._ampl == pytest.approx([50.0])
    assert slot._press is None


def test_volt_setter_exits_when_derived_press_exceeds_configured_max(patch_config):
    """CONFIRMED INTENDED (not a bug): amplitude is what's actually sent to hardware here
    (voltage is converted to it above), but exceeding the configured safe pressure limit is a
    deliberate safety checkpoint for the engineer, so
    _convert_ampl_to_press()'s max-pressure-exceeded sys.exit() is intentionally left free to
    propagate. The whole voltage request is rejected
    in that case, so the just-assigned _volt (and its derived _ampl) are also cleared back to
    None -- otherwise they'd still look like a valid, current result even though the request as
    a whole was refused."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1.4')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        # identity pp -> volt=50 converts straight to a legitimate ampl=50
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        # pp(x) = x * 1e-5 -> find_x_for_y_in_pp(ampl=50) finds x = 5_000_000, so
        # press_mpa = 5_000_000 * 1e-6 / eq_factor(1.0) = 5.0 MPa, above the 1.4 MPa max.
        'power_curve_pp': PPoly(c=[[1e-5], [0.0]], x=[0.0, 1e8], extrapolate=False),
    }
    slot._eq_factor = 1.0

    with pytest.raises(SystemExit):
        slot._set_volt(50)

    assert slot._press is None
    assert slot._volt is None
    assert slot._ampl is None


def test_volt_setter_with_multiple_values_skips_press_calculation(patch_config):
    """When more than one voltage is given, _convert_ampl_to_press() is deliberately not called
    (pressure cannot be derived from a per-element voltage array) -- self._press stays at the
    None every power setter resets it to upfront, rather than being computed."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Amplitude [%]'], available_ch=2)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    slot._eq_factor = 1.0

    slot._set_volt([50, 60])

    assert slot._volt == [50, 60]
    assert slot._ampl == pytest.approx([50.0, 60.0])
    assert slot._press is None


def test_ampl_setter_with_multiple_values_skips_press_calculation(patch_config):
    """Mirrors test_volt_setter_with_multiple_values_skips_press_calculation -- when more than
    one amplitude is given, _convert_ampl_to_press_for_logging() is deliberately not called
    (pressure cannot be derived from a per-element amplitude array), so self._press stays at
    the None every power setter resets it to upfront, rather than being computed."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=2)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    slot._eq_factor = 1.0

    slot._set_ampl([50, 60])

    assert slot._ampl == [50, 60]
    assert slot._volt == pytest.approx([50.0, 60.0])
    assert slot._press is None


def test_volt_setter_exits_when_power_option_unavailable():
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(power_options=['Some other option'])

    with pytest.raises(SystemExit):
        slot._set_volt(50)


def test_volt_setter_exits_on_wrong_length_list():
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Voltage [V]'], available_ch=4)

    with pytest.raises(SystemExit):
        slot._set_volt([10, 20])  # neither 1 entry nor 4 (available_ch) entries


def test_volt_setter_exits_when_combo_unknown_but_required():
    """Mirrors test_press_setter_exits_when_combo_unknown_but_required -- volt is non-native
    (amplitude is) and no 'Equipment.Combination.*' section exists for this combo at all, so
    there's no way to convert to amplitude (this is the behavior ampl's setter deviates from,
    per the already-documented asymmetry)."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(power_options=['Voltage [V]'],
                                       native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit):
        slot._set_volt(50)


def test_volt_setter_exits_and_clears_ampl_when_calculated_amplitude_exceeds_100(patch_config):
    """Mirrors test_press_setter_exits_and_clears_ampl_when_calculated_amplitude_exceeds_100 --
    _convert_volt_to_ampl()'s own internal >100% exit no longer has a self._ampl to clear
    either; volt's setter resets it to None before calling, for the same reason."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Voltage [V]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    slot._eq_factor = 1.0
    slot._ampl = ['stale']

    with pytest.raises(SystemExit):
        slot._set_volt(300)  # above volt_curve_pp's max of 200 -> calc_ampl > 100

    assert slot._ampl is None


# --- ampl ------------------------------------------------------------------
# Mirrors volt (engineering_mode guard, scalar-or-list, wrong-length exit,
# and now also the unavailable-power-option exit). Its handling of an
# unknown-but-required combo is intentionally different from press/volt --
# see the test below documenting why.

def test_ampl_setter_raises_when_engineering_mode_disabled(patch_config):
    patch_config.set('Power', 'Engineering-only options', 'Amplitude [%]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(power_options=['Amplitude [%]'])

    with pytest.raises(RuntimeError):
        slot._set_ampl(50)


def test_ampl_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Which options are engineering-only is a config-driven institutional policy, not
    hardcoded -- an institution that doesn't list amplitude here can set it directly."""
    patch_config.set('Power', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_ampl(50)  # must not raise

    assert slot._ampl == [50]


def test_ampl_setter_without_conversion_sets_value_directly():
    """Amplitude is this driving system's own native power parameter (matches IGT), so no
    calibration is ever needed to set it -- succeeds even with no active combo. CONFIRMED
    INTENDED asymmetry with press/volt (which both sys.exit() in this same situation, per
    their own tests): without an active calibration those two genuinely cannot derive the
    amplitude actually sent to hardware, whereas ampl already *is* that value."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_ampl(50)

    assert slot._ampl == [50]
    assert slot._chosen_power == 'Amplitude [%]'


def test_ampl_setter_with_known_combo_triggers_conversion(patch_config):
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
    }
    slot._eq_factor = 1.0

    slot._set_ampl(50)  # single value -> _convert_ampl_to_volt() then _convert_ampl_to_press()

    assert slot._ampl == [50]
    assert slot._volt == pytest.approx([50.0])
    assert slot._press == pytest.approx(5e-5)


def test_ampl_setter_logging_only_press_failure_does_not_raise(patch_config):
    """Same shape as test_volt_setter_logging_only_press_failure_does_not_raise, reached via
    ampl's setter instead -- the power curve's domain doesn't cover the set amplitude, so
    _convert_ampl_to_press() returns None, which must not crash the debug log line right after."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        'power_curve_pp': _identity_pp(80.0, 1000.0),  # domain doesn't cover ampl=50
    }
    slot._eq_factor = 1.0

    slot._set_ampl(50)  # must not raise

    assert slot._ampl == [50]
    assert slot._volt == pytest.approx([50.0])
    assert slot._press is None


def test_ampl_setter_exits_when_derived_press_exceeds_configured_max(patch_config):
    """CONFIRMED INTENDED (not a bug): even though amplitude is what's actually sent to
    hardware here (the derived pressure is otherwise only for the log line), exceeding the
    configured safe pressure limit is a deliberate safety checkpoint for the engineer, not
    merely a logging concern -- _convert_ampl_to_press()'s max-pressure-exceeded sys.exit() is
    intentionally left free to propagate through this setter rather than being caught.
    The whole amplitude request is rejected in that case, so the just-assigned _ampl (and its
    derived _volt) are also cleared back to None -- otherwise they'd still look like a valid,
    current result even though the request as a whole was refused."""
    patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '1.4')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
        # identity pp -> find_x_for_y_in_pp(ampl) finds x = ampl = 2_000_000, so
        # press_mpa = 2_000_000 * 1e-6 / eq_factor(1.0) = 2.0 MPa, above the 1.4 MPa max.
        'power_curve_pp': _identity_pp(-10.0, 1e7),
    }
    slot._eq_factor = 1.0

    with pytest.raises(SystemExit):
        slot._set_ampl(2_000_000)

    # Cleared right before the exit, per the "don't leave a stale, valid-looking value behind
    # a rejected request" principle applied consistently across this whole module.
    assert slot._press is None
    assert slot._ampl is None
    assert slot._volt is None


def test_ampl_setter_exits_on_wrong_length_list():
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]'], native_power_params=['Amplitude [%]'], available_ch=4)

    with pytest.raises(SystemExit):
        slot._set_ampl([10, 20])  # neither 1 entry nor 4 (available_ch) entries


def test_ampl_setter_exits_when_power_option_unavailable():
    """SOLVED: ampl's setter now mirrors press/volt with an explicit
    `else: sys.exit(...)` when the power option isn't in
    driving_sys.power_options, instead of silently leaving self._ampl at
    the reset value of 0 with no error."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(power_options=['Some other option'], available_ch=1)

    with pytest.raises(SystemExit):
        slot._set_ampl(50)


def test_ampl_and_volt_setters_both_work_without_calibration_when_both_are_native():
    """native_power_params is a list, not a single value -- a driving system whose hardware
    genuinely accepts more than one power representation directly (no calibration needed for
    either) can declare both as native. Neither should need an active combo. Every power setter
    resets every sibling to None upfront (see e.g. global_power's setter), so the proof that the
    combo-gated conversion is actually skipped is the sibling ending up None, not some stale
    value surviving from before -- a sibling ever landing on the OTHER setter's real value would
    mean the conversion ran when it shouldn't have."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        power_options=['Amplitude [%]', 'Voltage [V]'],
        native_power_params=['Amplitude [%]', 'Voltage [V]'], available_ch=1)
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    slot._set_ampl(50)
    assert slot._ampl == [50]
    assert slot._volt is None  # _convert_ampl_to_volt() skipped -- combo not active

    slot._set_volt(60)
    assert slot._volt == [60]
    assert slot._ampl is None  # _convert_volt_to_ampl() skipped -- combo not active


# --- focus_wrt_exit_plane ----------------------------------------------------

def test_focus_wrt_exit_plane_setter_raises_when_configured_as_engineering_only(patch_config):
    """Which focus options are engineering-only is a config-driven institutional policy --
    exit plane is available to everyone by default, but an institution can gate it too."""
    patch_config.set('Focus', 'Engineering-only options', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(focus_options=['Focus wrt exit plane [mm]'])

    with pytest.raises(RuntimeError):
        slot._set_focus_wrt_exit_plane(20)


def test_focus_wrt_exit_plane_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Mirrors test_focus_wrt_mid_bowl_setter_succeeds_without_engineering_mode_when_not_
    configured_as_such, for the other focus setter -- exit plane is available by default, and
    stays available when explicitly cleared from Engineering-only options."""
    patch_config.set('Focus', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None

    slot._set_focus_wrt_exit_plane(20)  # must not raise

    assert slot.focus_wrt_exit_plane == 20


def test_focus_wrt_exit_plane_setter_without_conversion_uses_exit_plane_offset():
    """Exit plane is this driving system's own native focus parameter (matches Sonic
    Concepts/CITRUS), so no calibration is ever needed to set it."""
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None  # no power chosen yet -> power-derived logging is skipped
    # Sentinels (not None -- that could also be a genuine _calc_* error-path result): must
    # survive untouched, proving the whole power-recompute block (eq_factor included) is
    # skipped when the combo isn't active, not just that the focus values themselves are right.
    slot._eq_factor = 'untouched'
    slot._ampl = 'untouched'
    slot._volt = 'untouched'

    slot._set_focus_wrt_exit_plane(20)

    assert slot.focus_wrt_exit_plane == 20
    assert slot.focus_wrt_mid_bowl == 25  # focus + exit_plane_dist
    assert slot._eq_factor == 'untouched'
    assert slot._ampl == 'untouched'
    assert slot._volt == 'untouched'


def test_focus_wrt_exit_plane_setter_with_known_combo_uses_focus_curve_and_recalculates(
        patch_config):
    """Exit plane is non-native (mid bowl is, matching IGT), so converting it requires an
    active calibration."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
    }

    slot._set_focus_wrt_exit_plane(20)

    assert slot.focus_wrt_exit_plane == 20
    assert slot.focus_wrt_mid_bowl == pytest.approx(20.0)  # focus_curve_pp(20) via identity
    assert float(slot._eq_factor) == pytest.approx(20.0)  # eq_curve_pp(20) via identity


def test_focus_wrt_exit_plane_setter_exits_when_out_of_curve_range_and_not_native(
        patch_config):
    """Mid bowl is native here (exit plane isn't) -- mid bowl is what's actually sent to
    hardware, so a focus value outside focus_curve_pp's own domain must exit rather than
    silently produce an inaccurate value. Uses a transducer min/max range (0-200) deliberately
    WIDER than the curve's own domain (0-50), so the old, now-removed transducer-range check
    would have wrongly let this through -- confirming the fix asks focus_curve_pp itself, not
    a possibly-mismatched proxy (see issue #93)."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=200, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 50.0),
        'eq_curve_pp': _identity_pp(0.0, 200.0),
    }

    with pytest.raises(SystemExit):
        slot._set_focus_wrt_exit_plane(70)  # within transducer range, outside curve's [0, 50]


def test_focus_wrt_exit_plane_setter_falls_back_when_out_of_curve_range_and_native(
        patch_config):
    """Same out-of-curve-range scenario as above, but with exit plane itself native (mid bowl
    is then purely informational, never sent to hardware) -- falling back to the geometric
    approximation is safe here, so the setter logs a warning and proceeds rather than raising."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=200, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._chosen_power = None
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 50.0),
        'eq_curve_pp': _identity_pp(0.0, 200.0),
    }

    slot._set_focus_wrt_exit_plane(70)  # within transducer range, outside curve's [0, 50]

    assert slot.focus_wrt_mid_bowl == 75  # fallback: focus + exit_plane_dist


def test_focus_wrt_exit_plane_setter_updates_eq_factor_but_never_touches_ampl_or_volt(
        patch_config):
    """_calc_eq_factor() must run whenever the combo is active -- it's an input _set_power()
    needs right after this, within the same configure() call. ampl/press/volt are deliberately
    never recomputed/logged here (regardless of self._chosen_power/self._press, which this
    method doesn't even read): _set_focus() only ever runs from configure(), which always calls
    _set_power() immediately after, so any value computed here would only ever describe a
    transient state _set_power() is about to replace or reset anyway."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
    }
    # Sentinels (not None -- that could also be a genuine _convert_* error-path result): must
    # survive untouched, proving _convert_press_to_ampl()/_convert_ampl_to_volt() are never
    # even attempted here.
    slot._ampl = 'untouched'
    slot._volt = 'untouched'

    slot._set_focus_wrt_exit_plane(20)

    assert float(slot._eq_factor) == pytest.approx(20.0)  # eq_curve_pp(20) via identity
    assert slot._ampl == 'untouched'
    assert slot._volt == 'untouched'


def test_focus_wrt_exit_plane_setter_exits_when_out_of_transducer_range():
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit):
        slot._set_focus_wrt_exit_plane(200)


def test_focus_wrt_exit_plane_setter_reports_missing_calibration_before_range_error():
    """Fail fast: whether this driving system can accept focus_wrt_exit_plane at all is
    checked before anything about the specific value (including the transducer's min/max
    range) -- so a value that's *both* out of range *and* unconvertible (non-native, no active
    combo) surfaces the calibration error, not the (less relevant, in this case) range one."""
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit, match='No active calibration available'):
        slot._set_focus_wrt_exit_plane(200)  # also out of the transducer's [0, 100] range


def test_focus_wrt_exit_plane_setter_exits_when_combo_unknown_but_required():
    """Exit plane is non-native (mid bowl is, matching IGT) and no
    'Equipment.Combination.*' section exists for this combo at all, so there's no way to
    convert to mid bowl -- the setter exits immediately, before assigning anything, instead of
    first assigning a geometric fallback value that would then look valid even though the
    request as a whole was rejected."""
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit):
        slot._set_focus_wrt_exit_plane(20)


def test_focus_wrt_exit_plane_setter_exits_when_focus_option_unavailable():
    """Mirrors test_focus_wrt_mid_bowl_setter_exits_when_focus_option_unavailable, for the
    other focus setter."""
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(focus_options=['Focus wrt mid bowl [mm]'])

    with pytest.raises(SystemExit, match='not available'):
        slot._set_focus_wrt_exit_plane(25)


# --- focus_wrt_mid_bowl -------------------------------------------------------

def test_focus_wrt_mid_bowl_setter_raises_when_engineering_mode_disabled(patch_config):
    patch_config.set('Focus', 'Engineering-only options', 'Focus wrt mid bowl [mm]')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(focus_options=['Focus wrt mid bowl [mm]'])

    with pytest.raises(RuntimeError):
        slot._set_focus_wrt_mid_bowl(25)


def test_focus_wrt_mid_bowl_setter_succeeds_without_engineering_mode_when_not_configured_as_such(
        patch_config):
    """Which options are engineering-only is a config-driven institutional policy, not
    hardcoded -- an institution that doesn't list mid bowl here can set it directly."""
    patch_config.set('Focus', 'Engineering-only options', '')
    slot = _bare_slot()
    slot._engineering_mode = False
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None

    slot._set_focus_wrt_mid_bowl(25)  # must not raise

    assert slot.focus_wrt_mid_bowl == 25


def test_focus_wrt_mid_bowl_setter_exits_when_focus_option_unavailable():
    """focus_options is a per-driving-system list, mirroring power_options -- a driving system
    that never offers mid bowl at all (e.g. Sonic Concepts/CITRUS, which only ever have exit
    plane as a curve-free native option) exits with a clear 'not available' message, distinct
    from the separate 'no active calibration' message used when the option is offered but
    unconvertible right now."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(focus_options=['Focus wrt exit plane [mm]'])

    with pytest.raises(SystemExit, match='not available'):
        slot._set_focus_wrt_mid_bowl(25)


def test_focus_wrt_mid_bowl_setter_without_conversion_uses_exit_plane_offset():
    """Mid bowl is this driving system's own native focus parameter (matches IGT), so no
    calibration is ever needed to set it."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None  # no power chosen yet -> power-derived logging is skipped
    # Sentinels (not None -- that could also be a genuine _calc_* error-path result): must
    # survive untouched, proving the whole power-recompute block (eq_factor included) is
    # skipped when the combo isn't active, not just that the focus values themselves are right.
    slot._eq_factor = 'untouched'
    slot._ampl = 'untouched'
    slot._volt = 'untouched'

    slot._set_focus_wrt_mid_bowl(25)

    assert slot.focus_wrt_mid_bowl == 25
    assert slot.focus_wrt_exit_plane == 20  # focus - exit_plane_dist
    assert slot._eq_factor == 'untouched'
    assert slot._ampl == 'untouched'
    assert slot._volt == 'untouched'


def test_focus_wrt_mid_bowl_setter_with_known_combo_finds_x_via_pp_and_recalculates(patch_config):
    """Mid bowl is non-native (exit plane is, matching Sonic Concepts/CITRUS), so converting it
    requires an active calibration."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
    }

    slot._set_focus_wrt_mid_bowl(20)  # within focus_curve_pp's [0, 100] range -> found

    assert slot.focus_wrt_exit_plane == pytest.approx(20.0)
    assert slot.focus_wrt_mid_bowl == 20
    assert float(slot._eq_factor) == pytest.approx(20.0)


def test_focus_wrt_mid_bowl_setter_exits_when_x_not_found_and_not_native(patch_config):
    """When find_x_for_y_in_pp can't find an x value for the target focus_wrt_mid_bowl (target
    outside the focus_curve_pp's y-range) despite an active calibration, AND mid bowl is not
    native (exit plane is, see native_focus_params below) -- exit plane is what's actually sent
    to hardware here, so an imprecise geometric approximation of it is not an acceptable
    fallback."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=-100, max_foc=1000, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(-1000.0, 1000.0),
    }

    with pytest.raises(SystemExit):
        slot._set_focus_wrt_mid_bowl(500)  # outside focus_curve_pp's [0, 100] y-range -> not found


def test_focus_wrt_mid_bowl_setter_falls_back_when_x_not_found_and_native(patch_config):
    """Same not-found scenario as above, but with mid bowl itself native (exit plane is then
    purely informational, never sent to hardware) -- falling back to the geometric approximation
    is safe here, so the setter logs a warning and proceeds rather than raising."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=-100, max_foc=1000, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(-1000.0, 1000.0),
    }

    slot._set_focus_wrt_mid_bowl(500)  # outside focus_curve_pp's [0, 100] y-range -> not found

    assert slot.focus_wrt_exit_plane == 495  # fallback: focus - exit_plane_dist


def test_focus_wrt_mid_bowl_setter_exits_when_combo_unknown_but_required():
    """Mid bowl is non-native (exit plane is, matching Sonic Concepts/CITRUS) and no
    'Equipment.Combination.*' section exists for this combo at all, so there's no way to
    convert to exit plane."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active

    with pytest.raises(SystemExit):
        slot._set_focus_wrt_mid_bowl(20)


def test_focus_wrt_mid_bowl_setter_updates_eq_factor_but_never_touches_ampl_or_volt(
        patch_config):
    """See the identical note in
    test_focus_wrt_exit_plane_setter_updates_eq_factor_but_never_touches_ampl_or_volt."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
    }
    # Sentinels (not None -- that could also be a genuine _convert_* error-path result): must
    # survive untouched, proving _convert_press_to_ampl()/_convert_ampl_to_volt() are never
    # even attempted here.
    slot._ampl = 'untouched'
    slot._volt = 'untouched'

    slot._set_focus_wrt_mid_bowl(20)  # within focus_curve_pp's [0, 100] range -> found

    assert float(slot._eq_factor) == pytest.approx(20.0)  # eq_curve_pp(20) via identity
    assert slot._ampl == 'untouched'
    assert slot._volt == 'untouched'


def test_focus_setters_both_work_without_calibration_when_both_are_native():
    """native_focus_params is a list, not a single value -- a driving system whose hardware
    genuinely accepts more than one focus representation directly (e.g. an exact, curve-free
    geometric relationship for every transducer it supports) can declare both as native.
    Neither should need an active combo."""
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]', 'Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None
    # Sentinels (not None -- that could also be a genuine _calc_* error-path result): must
    # survive untouched, proving the whole power-recompute block (eq_factor included) is
    # skipped for both calls, not just that the focus values themselves are right.
    slot._eq_factor = 'untouched'
    slot._ampl = 'untouched'
    slot._volt = 'untouched'

    slot._set_focus_wrt_exit_plane(20)
    assert slot.focus_wrt_exit_plane == 20

    slot._set_focus_wrt_mid_bowl(30)
    assert slot.focus_wrt_mid_bowl == 30

    assert slot._eq_factor == 'untouched'
    assert slot._ampl == 'untouched'
    assert slot._volt == 'untouched'


# --- transducer ---------------------------------------------------------------

def test_transducer_setter_exits_when_not_compatible(patch_config):
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(serial='DS1', tran_comp=['TRAN-A', 'TRAN-B'])

    with pytest.raises(SystemExit):
        slot._set_transducer('TRAN-C')


def test_transducer_setter_sets_default_oper_freq_and_resets_focus_and_power(patch_config):
    """oper_freq defaults from the new transducer's own fundamental frequency (add_slot()'s own
    oper_freq parameter relies on this) -- but focus and power no longer default to anything,
    they reset to None, since nothing in FDS's own add_slot() flow ever observes that
    intermediate state (configure() always sets the real focus/power right after) and SonoRover
    One (the one known external consumer of the old min_foc default) needs its own rewrite
    against this API regardless. Power is exactly as transducer-specific as focus -- the
    calibration curve a previously chosen power value was computed against belonged to the old
    transducer -- so it's reset for the same reason, not just focus."""
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(serial='DS1', tran_comp=['TRAN-A'])
    slot._transducer = SimpleNamespace(
        serial='', set_transducer_info=lambda serial: setattr(slot._transducer, 'serial', serial),
        fund_freq=300, min_foc=40)
    # Stale values from a previous transducer -- must not survive.
    slot._chosen_focus = 'Focus wrt exit plane [mm]'
    slot._focus_wrt_exit_plane = 20
    slot._focus_wrt_mid_bowl = 25
    slot._chosen_power = 'Max. pressure in free water [MPa]'
    slot._press = 1.0
    slot._volt = [10.0]
    slot._ampl = [50.0]
    slot._global_power = 2.0
    slot._input_press_mpa = 1.0
    slot._eq_press_mpa = 1.1
    slot._calculated_ampl = 50.0

    slot._set_transducer('TRAN-A')

    assert slot.oper_freq == 300
    assert slot._chosen_focus is None
    assert slot._focus_wrt_exit_plane is None
    assert slot._focus_wrt_mid_bowl is None
    assert slot._chosen_power is None
    assert slot._press is None
    assert slot._volt is None
    assert slot._ampl is None
    assert slot._global_power is None
    assert slot._input_press_mpa is None
    assert slot._eq_press_mpa is None
    assert slot._calculated_ampl is None
    assert slot._ds_tran_combo == 'DS1~TRAN-A'


def test_transducer_setter_loads_real_curves_when_combo_active(tmp_path, patch_config):
    """_set_transducer() -> _refresh_combo() -> _update_conv_param() actually runs (and doesn't
    crash) when a calibration combo exists for the new pair -- proven with real curve-fit JSON
    files, not just a mocked _combo_is_active(). Distinct from
    test_update_conv_param_populates_all_four_curves_and_updates_transducer_range, which calls
    _update_conv_param() directly: this one exercises the actual _set_transducer() ->
    _refresh_combo() trigger path. _update_conv_param() itself no longer touches focus/power/
    eq_factor at all (see its own docstring), so there's nothing focus/power-related left to set
    up or assert on here -- this used to also characterize that, back when it still ran a guard
    clause for it."""
    section = 'Equipment.Combination.DS1~TRAN-A'
    patch_config.set(section, 'Active?', 'True')
    eq_file = _write_identity_fit_json(tmp_path, 'eq.json', 0.0, 100.0)
    patch_config.set(section, 'EqualizationCurveFit json file', eq_file)
    patch_config.set(section, 'FocusCurveFit json file', eq_file)
    patch_config.set(section, 'PowerCurveFit json file', eq_file)
    patch_config.set(section, 'VoltageCurveFit json file', eq_file)

    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(serial='DS1', tran_comp=['TRAN-A'])
    slot._transducer = SimpleNamespace(
        serial='', set_transducer_info=lambda serial: setattr(slot._transducer, 'serial', serial),
        fund_freq=300, min_foc=40)

    slot._set_transducer('TRAN-A')  # must not raise

    assert slot._ds_tran_combo == 'DS1~TRAN-A'
    assert slot._conv_param['eq_curve_pp'] is not None  # proves _update_conv_param() really ran


# --- update_transducer --------------------------------------------------------
# Combines _set_transducer() + this slot's own per-slot element-count validation +
# oper_freq/dephasing_degree + configure() -- used both by TUSProtocol.add_slot() (a freshly
# constructed slot) and directly on an already-added slot to swap its transducer later, e.g.
# protocol.slots[0].update_transducer(...). Unlike TUSProtocol's own _validate_channel_count()
# (the *aggregate* check across every slot, which needs the full slots list this method has no
# way to see), the per-slot check here is self-contained -- and is enough on its own to keep the
# aggregate within bounds too: if every existing slot already satisfies its own
# available_ch / max_tran_slots ceiling, and the slot count never exceeds max_tran_slots
# (add_slot()'s own job), the sum can never exceed available_ch either.

def _fake_transducer(elements=2, fund_freq=300):
    tran = SimpleNamespace(serial='', elements=elements, fund_freq=fund_freq, min_foc=0,
                           max_foc=100, name='tran', exit_plane_dist=5)
    tran.set_transducer_info = lambda serial: setattr(tran, 'serial', serial)
    return tran


def _driving_sys_for(*tran_serials, max_tran_slots=4, available_ch=208):
    return SimpleNamespace(
        serial='DS1', max_tran_slots=max_tran_slots, available_ch=available_ch,
        tran_comp=list(tran_serials), power_options=['Amplitude [%]'],
        focus_options=['Focus wrt exit plane [mm]'], native_power_params=['Amplitude [%]'],
        native_focus_params=['Focus wrt exit plane [mm]'])


def test_update_transducer_swaps_transducer_and_reconfigures(patch_config):
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = _driving_sys_for('TRAN-A', 'TRAN-B', max_tran_slots=1, available_ch=2)
    slot._transducer = _fake_transducer(elements=2)
    slot.update_transducer('TRAN-A', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)

    slot.update_transducer('TRAN-B', 'Focus wrt exit plane [mm]', 25, 'Amplitude [%]', 35)

    assert slot.transducer.serial == 'TRAN-B'
    assert slot.focus_wrt_exit_plane == 25
    assert slot.ampl == [35]


def test_update_transducer_defaults_dephasing_degree_to_none_even_when_old_slot_had_one(
        patch_config):
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = _driving_sys_for('TRAN-A', 'TRAN-B', max_tran_slots=1, available_ch=2)
    slot._transducer = _fake_transducer(elements=2)
    slot.update_transducer('TRAN-A', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30,
                           dephasing_degree=[90, 180])

    slot.update_transducer('TRAN-B', 'Focus wrt exit plane [mm]', 25, 'Amplitude [%]', 35)

    # A dephasing list sized for TRAN-A's element count isn't safe to assume for TRAN-B, even
    # though they happen to share the same count here -- it's never carried over automatically.
    assert slot.dephasing_degree is None


def test_update_transducer_validates_new_transducers_element_count(patch_config):
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = _driving_sys_for('TRAN-BIG', max_tran_slots=4, available_ch=208)
    slot._transducer = _fake_transducer(elements=60)

    with pytest.raises(SystemExit, match='60 elements'):
        slot.update_transducer('TRAN-BIG', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)


def test_update_transducer_sets_optional_oper_freq(patch_config):
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = _driving_sys_for('TRAN-A', max_tran_slots=1, available_ch=2)
    slot._transducer = _fake_transducer(elements=2, fund_freq=300)

    slot.update_transducer('TRAN-A', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30,
                           oper_freq=500)

    assert slot.oper_freq == 500


def test_update_transducer_defaults_oper_freq_to_transducer_fund_freq_when_not_given(
        patch_config):
    """Two distinct transducers, each with its own fund_freq (TRAN-A: 300, TRAN-B: 999) --
    starting on TRAN-A and updating to TRAN-B, oper_freq must end up at TRAN-B's fund_freq (999),
    not stay at TRAN-A's (300). A single, fixed fund_freq shared by both couldn't distinguish
    "correctly re-derived from the new transducer" from "coincidentally already the same value".
    Real Transducer.set_transducer_info(serial) reloads every field -- including fund_freq --
    from config for the given serial, mutating the same object in place rather than replacing
    it; simulated here with a serial -> fund_freq lookup instead of _fake_transducer()'s own
    lambda (which only ever updates .serial)."""
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    slot = _bare_slot()
    slot._engineering_mode = True
    slot.driving_sys = _driving_sys_for('TRAN-A', 'TRAN-B', max_tran_slots=1, available_ch=2)
    slot._transducer = _fake_transducer(elements=2, fund_freq=300)  # starts on TRAN-A

    fund_freq_by_serial = {'TRAN-A': 300, 'TRAN-B': 999}

    def _swap(serial):
        slot._transducer.serial = serial
        slot._transducer.fund_freq = fund_freq_by_serial[serial]

    slot._transducer.set_transducer_info = _swap

    slot.update_transducer('TRAN-B', 'Focus wrt exit plane [mm]', 20, 'Amplitude [%]', 30)

    assert slot.oper_freq == 999


# --- _set_focus / _set_power / configure --------------------------------------
# configure() (used by TUSProtocol.add_slot() to build a new slot, and equally usable directly on
# an already-added slot to update its focus/power later) just forwards to these two dispatchers,
# in a fixed safe order (focus first, then power).

def test_set_focus_forwards_to_matching_property(patch_config):
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    patch_config.set('Focus', 'Option.bowl', 'Focus wrt mid bowl [mm]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt mid bowl [mm]'], native_focus_params=['Focus wrt mid bowl [mm]'])
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._chosen_power = None
    slot._engineering_mode = True

    slot._set_focus('Focus wrt mid bowl [mm]', 42)

    assert slot.focus_wrt_mid_bowl == 42


def test_set_focus_exits_for_unknown_option(patch_config):
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    patch_config.set('Focus', 'Option.bowl', 'Focus wrt mid bowl [mm]')
    slot = _bare_slot()

    with pytest.raises(SystemExit):
        slot._set_focus('Something else', 42)


def test_set_power_forwards_to_matching_property(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    patch_config.set('Power', 'Option.press', 'Max. pressure in free water [MPa]')
    patch_config.set('Power', 'Option.volt', 'Voltage [V]')
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'])
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._engineering_mode = True

    slot._set_power('Max. pressure in free water [MPa]', 0.5)

    assert slot.press == 0.5


def test_set_power_exits_for_unknown_option(patch_config):
    patch_config.set('Power', 'Option.glob_pow', 'Global power [mW]')
    patch_config.set('Power', 'Option.press', 'Max. pressure in free water [MPa]')
    patch_config.set('Power', 'Option.volt', 'Voltage [V]')
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    slot = _bare_slot()

    with pytest.raises(SystemExit):
        slot._set_power('Something else', 5)


def test_configure_sets_focus_before_power(patch_config):
    """Focus must be applied before power -- compensation equations may need the just-updated
    focus (specifically, its derived eq_factor) to convert power correctly. Needs a non-native
    power option (press, which converts via eq_factor) and an active combo to actually be
    order-sensitive: with a native power option and no active combo (as an earlier version of
    this test had), neither setter depends on the other at all, so swapping the order produces
    identical final values -- the assertions couldn't have told "focus first" apart from "power
    first" either way. Confirmed directly: calling _set_power() before _set_focus() in this
    exact setup raises AttributeError (self._eq_factor not set yet); configure() must not do
    that."""
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    patch_config.set('Power', 'Option.press', 'Max. pressure in free water [MPa]')
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _bare_slot()
    slot.driving_sys = SimpleNamespace(
        focus_options=['Focus wrt exit plane [mm]'],
        native_focus_params=['Focus wrt exit plane [mm]'],
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Voltage [V]'],  # press is NOT native -> needs eq_factor from focus
        available_ch=1)
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=100, exit_plane_dist=5, name='tran')
    slot._ds_tran_combo = 'combo1'
    slot._chosen_power = None
    slot._engineering_mode = True
    slot._conv_param = {
        'focus_curve_pp': _identity_pp(0.0, 100.0),
        'eq_curve_pp': _identity_pp(0.0, 100.0),
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }

    slot.configure('Focus wrt exit plane [mm]', 20, 'Max. pressure in free water [MPa]', 2e-6)

    assert slot.focus_wrt_exit_plane == 20
    assert slot.press == 2e-6
    assert slot.ampl == [40.0]  # power_curve_pp(press_pa * eq_factor) via identity -- needs
    # eq_factor(20) == 20 to already be correct at this point


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
    """This method only ever runs from _set_transducer() (via update_transducer()), which
    always resets focus to None right before calling it -- so eq_factor is never meaningful to
    compute here; _set_focus()'s own setters do that once configure() provides a real focus
    value moments later. Seeded as a sentinel (not None -- that could also look like a genuine
    fresh-slot default) to prove it's genuinely never touched, not just correct by coincidence."""
    slot = _bare_slot()
    slot._ds_tran_combo = 'combo1'
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=0)
    slot._eq_factor = 'untouched'

    eq_file = _write_identity_fit_json(tmp_path, 'eq.json', 0.0, 100.0)
    focus_file = _write_identity_fit_json(tmp_path, 'focus.json', 0.0, 100.0)
    power_file = _write_identity_fit_json(tmp_path, 'power.json', -10.0, 1000.0)
    volt_file = _write_identity_fit_json(tmp_path, 'volt.json', -10.0, 200.0)

    section = 'Equipment.Combination.combo1'
    patch_config.set(section, 'EqualizationCurveFit json file', eq_file)
    patch_config.set(section, 'FocusCurveFit json file', focus_file)
    patch_config.set(section, 'PowerCurveFit json file', power_file)
    patch_config.set(section, 'VoltageCurveFit json file', volt_file)

    slot._update_conv_param()

    assert slot._conv_param['eq_curve_pp'] is not None
    assert slot._conv_param['focus_curve_pp'] is not None
    assert slot._conv_param['power_curve_pp'] is not None
    assert slot._conv_param['volt_curve_pp'] is not None

    # transducer.min_foc/max_foc are (re)set from the equalization curve's breaks
    assert slot.transducer.min_foc == 0.0
    assert slot.transducer.max_foc == 100.0

    assert slot._eq_factor == 'untouched'


def test_update_conv_param_warns_when_focus_curve_domain_exceeds_eq_curve_domain(
        tmp_path, patch_config, caplog):
    """focus_curve_pp and eq_curve_pp share the same x-axis (focus wrt exit plane) -- if their
    domains don't match, min_foc/max_foc (sourced from eq_curve_pp alone, see issue #93) may not
    accurately bound focus_curve_pp's own valid range. Doesn't affect correctness (every curve
    evaluation checks its own domain independently via safe_evaluate_pp), but likely signals a
    calibration-data problem worth flagging early."""
    slot = _bare_slot()
    slot._ds_tran_combo = 'combo1'
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=0)

    eq_file = _write_identity_fit_json(tmp_path, 'eq.json', 0.0, 50.0)
    focus_file = _write_identity_fit_json(tmp_path, 'focus.json', 0.0, 100.0)  # wider than eq
    power_file = _write_identity_fit_json(tmp_path, 'power.json', -10.0, 1000.0)
    volt_file = _write_identity_fit_json(tmp_path, 'volt.json', -10.0, 200.0)

    section = 'Equipment.Combination.combo1'
    patch_config.set(section, 'EqualizationCurveFit json file', eq_file)
    patch_config.set(section, 'FocusCurveFit json file', focus_file)
    patch_config.set(section, 'PowerCurveFit json file', power_file)
    patch_config.set(section, 'VoltageCurveFit json file', volt_file)

    with caplog.at_level('WARNING'):
        slot._update_conv_param()

    assert 'extends beyond the equalization curve' in caplog.text


def test_update_conv_param_does_not_warn_when_focus_curve_domain_matches_eq_curve_domain(
        tmp_path, patch_config, caplog):
    """Mirrors the mismatch test above -- identical domains, no warning."""
    slot = _bare_slot()
    slot._ds_tran_combo = 'combo1'
    slot._transducer = SimpleNamespace(min_foc=0, max_foc=0)

    eq_file = _write_identity_fit_json(tmp_path, 'eq.json', 0.0, 100.0)
    focus_file = _write_identity_fit_json(tmp_path, 'focus.json', 0.0, 100.0)
    power_file = _write_identity_fit_json(tmp_path, 'power.json', -10.0, 1000.0)
    volt_file = _write_identity_fit_json(tmp_path, 'volt.json', -10.0, 200.0)

    section = 'Equipment.Combination.combo1'
    patch_config.set(section, 'EqualizationCurveFit json file', eq_file)
    patch_config.set(section, 'FocusCurveFit json file', focus_file)
    patch_config.set(section, 'PowerCurveFit json file', power_file)
    patch_config.set(section, 'VoltageCurveFit json file', volt_file)

    with caplog.at_level('WARNING'):
        slot._update_conv_param()

    assert 'extends beyond the equalization curve' not in caplog.text


# --- __str__ -----------------------------------------------------------------

def _str_ready_slot():
    """A slot with just enough set for __str__ to run without crashing: chosen_power ==
    'Global power [mW]' needs the fewest additional fields (no input_press_mpa/eq_press_mpa/
    calculated_ampl to fill in, unlike the press branch)."""
    slot = _bare_slot()
    slot._transducer = SimpleNamespace()
    slot._chosen_power = 'Global power [mW]'
    slot._global_power = 2.5
    slot._ds_tran_combo = 'combo1'  # no matching config section -> combo not active
    slot._oper_freq = 500
    slot._chosen_focus = 'Focus wrt exit plane [mm]'
    slot._focus_wrt_exit_plane = 40
    slot._focus_wrt_mid_bowl = 40
    slot._dephasing_degree = None
    return slot


def test_str_reports_native_power_needs_no_correction_when_combo_inactive():
    """Previously silent in this case (neither the combo-active block nor the old "not
    available" elif applied) -- now always says something, since a native power parameter never
    needing pressure correction in the first place is worth stating explicitly, not omitting."""
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Global power [mW]'], serial='DS-1')

    info = str(slot)

    assert "Global power [mW] is already DS-1's native power parameter" in info
    assert "not available in the configuration file" not in info


def test_str_reports_missing_correction_when_not_native_and_combo_inactive():
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Amplitude [%]'], serial='DS-1')

    info = str(slot)

    assert "not available in the configuration file" in info
    assert "native power parameter" not in info


def test_str_shows_equalized_pressure_when_press_is_non_native_and_combo_active(patch_config):
    """Mirrors the non-native, combo-active case that motivates showing an equalized pressure at
    all -- matches IGT, where pressure must be converted through the calibration curve to reach
    the driving system's actual native parameter (amplitude)."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Amplitude [%]'], serial='DS-1')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    slot._eq_factor = 1.0

    slot._set_press(50e-6)

    info = str(slot)

    assert "Equalized pressure in free water [MPa]" in info
    assert "Equalization factor [-]: 1.00" in info


def test_str_omits_equalized_pressure_and_factor_when_press_is_native_even_if_combo_active(
        patch_config):
    """If pressure is this driving system's native power parameter, _set_press() still computes
    an equalized pressure/derived amplitude whenever a combo happens to be active (purely for
    logging -- see _set_press()'s own comment) -- but there's nothing actually being corrected
    towards, so __str__ must not display either as if a real conversion were happening."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(
        power_options=['Max. pressure in free water [MPa]'],
        native_power_params=['Max. pressure in free water [MPa]'], serial='DS-1')
    slot._ds_tran_combo = 'combo1'
    slot._conv_param = {
        'power_curve_pp': _identity_pp(-10.0, 1000.0),
        'volt_curve_pp': _identity_pp(-10.0, 200.0),
    }
    slot._eq_factor = 1.0

    slot._set_press(50e-6)

    info = str(slot)

    assert "Equalized pressure in free water [MPa]" not in info
    assert "Equalization factor" not in info


def test_str_reports_not_implemented_for_an_unrecognized_chosen_power(patch_config):
    """chosen_power holding a value that isn't None and doesn't match any of the four known
    option strings (e.g. a config-driven power option added/renamed without updating __str__)
    must be reported distinctly from "not yet configured" -- something genuinely was chosen."""
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Global power [mW]'], serial='DS-1')
    slot._chosen_power = 'Some future power option [X]'

    info = str(slot)

    assert "Some future power option [X] (reporting not implemented for this option)" in info
    assert "Chosen power option: not yet configured" not in info


def test_str_reports_no_pressure_correction_info_when_no_power_chosen_yet(patch_config):
    """Mirrors chosen_focus's own guard: a slot whose transducer is already assigned (combo
    active) but whose configure() hasn't run yet must not print sibling press/volt/ampl values
    or a normalized-pressure line right underneath its own "not yet configured" line -- none of
    that means anything until a power option has actually been chosen."""
    patch_config.set('Equipment.Combination.combo1', 'Active?', 'True')
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Global power [mW]'], serial='DS-1')
    slot._chosen_power = None

    info = str(slot)

    assert "Chosen power option: not yet configured" in info
    assert "Voltage [V]" not in info
    assert "Amplitude [%]" not in info
    assert "Equalization factor" not in info
    assert "native power parameter" not in info
    assert "not available in the configuration file" not in info


def test_str_reports_chosen_focus_option():
    """The derived focal depths (exit plane + mid bowl) are deliberately not repeated here --
    whichever focus setter actually ran (_set_focus_wrt_exit_plane/_set_focus_wrt_mid_bowl)
    already logged that exact pair, at configure() time, as its own debug line."""
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Global power [mW]'], serial='DS-1')

    info = str(slot)

    assert "Chosen focus option: Focus wrt exit plane [mm]" in info
    assert "Focal depth wrt exit plane" not in info
    assert "Focal depth wrt bowl middle" not in info


def test_str_reports_not_yet_configured_when_no_focus_chosen():
    slot = _str_ready_slot()
    slot.driving_sys = SimpleNamespace(native_power_params=['Global power [mW]'], serial='DS-1')
    slot._chosen_focus = None

    info = str(slot)

    assert "Chosen focus option: not yet configured" in info


def test_str_does_not_crash_on_a_genuinely_bare_slot():
    """TransducerSlot's own docstring says direct construction isn't a supported entry point
    (use TUSProtocol.add_slot() instead) -- but str() on one must still not crash if a caller
    does construct one directly and inspects it before configuring anything. Regression test:
    _combo_is_active() used to crash with a TypeError trying to string-concatenate
    self._ds_tran_combo (None, since no transducer has ever been assigned) into a config section
    name; further down, the focus fields' :.2f formatting used to crash the same way on None.
    Neither chosen_power nor chosen_focus has ever been set here, so -- mirroring each other --
    both simply report "not yet configured" rather than printing any of their underlying,
    still-unset fields."""
    fake_driving_sys = SimpleNamespace(native_power_params=['Amplitude [%]'], serial='DS-1')
    slot = TransducerSlot(fake_driving_sys, engineering_mode=False)

    info = str(slot)

    assert info.count("not yet configured") == 2


# --- chosen_focus_value / chosen_power_value / intensity_summary() ------------

def test_chosen_focus_value_returns_none_when_not_yet_chosen():
    slot = _bare_slot()
    slot._chosen_focus = None

    assert slot.chosen_focus_value is None


def test_chosen_focus_value_returns_the_matching_field(patch_config):
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    patch_config.set('Focus', 'Option.bowl', 'Focus wrt mid bowl [mm]')
    slot = _bare_slot()
    slot._chosen_focus = 'Focus wrt mid bowl [mm]'
    slot._focus_wrt_mid_bowl = 42.0
    slot._focus_wrt_exit_plane = 10.0

    assert slot.chosen_focus_value == 42.0


def test_chosen_power_value_returns_none_when_not_yet_chosen():
    slot = _bare_slot()
    slot._chosen_power = None

    assert slot.chosen_power_value is None


def test_chosen_power_value_returns_the_matching_field(patch_config):
    patch_config.set('Power', 'Option.press', 'Max. pressure in free water [MPa]')
    slot = _bare_slot()
    slot._chosen_power = 'Max. pressure in free water [MPa]'
    slot._press = 0.3
    slot._ampl = [12.5]

    assert slot.chosen_power_value == 0.3


def test_chosen_power_value_returns_a_list_for_amplitude(patch_config):
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    slot = _bare_slot()
    slot._chosen_power = 'Amplitude [%]'
    slot._ampl = [12.5, 13.0]

    assert slot.chosen_power_value == [12.5, 13.0]


def test_intensity_summary_reports_not_yet_configured_when_bare():
    fake_driving_sys = SimpleNamespace(native_power_params=['Amplitude [%]'], serial='DS-1')
    slot = TransducerSlot(fake_driving_sys, engineering_mode=False)

    summary = slot.intensity_summary()

    assert 'focus not yet configured' in summary
    assert 'power not yet configured' in summary


def test_intensity_summary_reports_scalar_focus_and_power(patch_config):
    patch_config.set('Focus', 'Option.exit', 'Focus wrt exit plane [mm]')
    patch_config.set('Power', 'Option.press', 'Max. pressure in free water [MPa]')
    slot = _bare_slot()
    slot._transducer = SimpleNamespace(serial='IS_PCD15287_01001')
    slot._chosen_focus = 'Focus wrt exit plane [mm]'
    slot._focus_wrt_exit_plane = 40.0
    slot._chosen_power = 'Max. pressure in free water [MPa]'
    slot._press = 0.3

    summary = slot.intensity_summary()

    assert summary == ('IS_PCD15287_01001: Focus wrt exit plane [mm] = 40.00, ' +
                       'Max. pressure in free water [MPa] = 0.30')


def test_intensity_summary_reports_a_list_for_amplitude(patch_config):
    patch_config.set('Focus', 'Option.bowl', 'Focus wrt mid bowl [mm]')
    patch_config.set('Power', 'Option.ampl', 'Amplitude [%]')
    slot = _bare_slot()
    slot._transducer = SimpleNamespace(serial='IS_PCD15287_01001')
    slot._chosen_focus = 'Focus wrt mid bowl [mm]'
    slot._focus_wrt_mid_bowl = 50.0
    slot._chosen_power = 'Amplitude [%]'
    slot._ampl = [12.5, 13.0]

    summary = slot.intensity_summary()

    assert "Amplitude [%] = ['12.50', '13.00']" in summary
