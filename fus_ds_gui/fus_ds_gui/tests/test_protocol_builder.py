# -*- coding: utf-8 -*-
"""
Tests for ProtocolBuilder and its module-level helpers. Uses the patch_config fixture (see
conftest.py) with synthetic 'UNITTEST_*' serials, so these don't depend on whatever real driving
systems/transducers happen to be listed in the shipped ds_config.ini.
"""
import pytest

from fus_driving_systems.exceptions import FDSConfigError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts

from fus_ds_gui.models.protocol_builder import ProtocolBuilder, _create_ds_instance


def _configure_driving_system(patch_config, serial, manufacturer='IGT', max_tran_slots=1,
                              available_ch=2, tran_comp=('UNITTEST_TRAN',)):
    patch_config.set('Equipment', 'Driving systems', serial)
    section = f'Equipment.Driving system.{serial}'
    patch_config.set(section, 'Name', f'Test {manufacturer}')
    patch_config.set(section, 'Manufacturer', manufacturer)
    patch_config.set(section, 'Available channels', str(available_ch))
    patch_config.set(section, 'Connection info', 'COM1')
    patch_config.set(section, 'Transducer compatibility', '\n'.join(tran_comp))
    # 'Amplitude [%]' is deliberately included as a *non*-native option here: it's
    # engineering-only in the real, shipped ds_config.ini, and several tests below rely on
    # exactly that to exercise the engineering-only filter. 'Max. pressure in free water [MPa]'
    # is the native one instead, so add_slot() calls that aren't testing that filter can use it
    # without needing an active calibration combo.
    patch_config.set(section, 'Power options',
                     'Amplitude [%]\nMax. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options',
                     'Focus wrt exit plane [mm]\nFocus wrt mid bowl [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', str(max_tran_slots))
    patch_config.set(section, 'Active?', 'True')


def _configure_transducer(patch_config, serial, elements=2):
    patch_config.set('Equipment', 'Transducers', serial)
    section = f'Equipment.Transducer.{serial}'
    patch_config.set(section, 'Elements', str(elements))
    patch_config.set(section, 'Fund. freq.', '300')
    patch_config.set(section, 'Min. focus', '0')
    patch_config.set(section, 'Max. focus', '100')
    patch_config.set(section, 'Exit plane - first element dist.', '5')
    patch_config.set(section, 'Steer information', '')
    patch_config.set(section, 'Active?', 'True')


@pytest.fixture
def igt_with_transducer(patch_config):
    """A synthetic IGT-manufactured driving system, plus one compatible transducer, with no
    active calibration combo, so focus/power stay simple, uncalibrated values (matching
    native_power_params/native_focus_params above), same simplification the core package's own
    add_slot() tests use."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', manufacturer='IGT')
    _configure_transducer(patch_config, 'UNITTEST_TRAN')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return ds


def test_create_ds_instance_maps_igt(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT', manufacturer='IGT')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')

    assert isinstance(_create_ds_instance(ds), IGT)


def test_create_ds_instance_maps_sonic_concepts_case_insensitively(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_SC', manufacturer='sonic concepts')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')

    assert isinstance(_create_ds_instance(ds), SonicConcepts)


def test_create_ds_instance_raises_for_unsupported_manufacturer(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_X', manufacturer='Acme Corp')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_X')

    with pytest.raises(FDSConfigError):
        _create_ds_instance(ds)


def test_focus_options_excludes_engineering_only(patch_config, igt_with_transducer):
    patch_config.set('Focus', 'Engineering-only options', 'Focus wrt mid bowl [mm]')

    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.focus_options() == ['Focus wrt exit plane [mm]']


def test_focus_options_excludes_xyz_by_default(patch_config, igt_with_transducer):
    """No transducer given, and igt_with_transducer's own selected transducer has
    can_3d_steer=False, so the xyz option must not appear even though the driving system
    itself lists it."""
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Focus options',
                     'Focus wrt exit plane [mm]\nFocus xyz wrt exit plane [mm]')

    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.focus_options() == ['Focus wrt exit plane [mm]']
    tran = builder.compatible_transducers()[0]
    assert builder.focus_options(tran) == ['Focus wrt exit plane [mm]']


def test_focus_options_includes_xyz_for_a_3d_steering_capable_transducer(patch_config,
                                                                         igt_with_transducer):
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Focus options',
                     'Focus wrt exit plane [mm]\nFocus xyz wrt exit plane [mm]')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Can 3D steer?', 'True')
    # Transducer.set_transducer_info() itself requires an .ini steer path whenever
    # can_3d_steer=True (see its own FDSConfigError check); the content doesn't matter here,
    # only the extension.
    patch_config.set(tran_section, 'Steer information', 'unittest_steer.ini')

    builder = ProtocolBuilder(igt_with_transducer)
    tran = builder.compatible_transducers()[0]

    assert builder.focus_options(tran) == ['Focus wrt exit plane [mm]',
                                           'Focus xyz wrt exit plane [mm]']
    # Not selecting a transducer at all still excludes it: there's no transducer yet to know
    # can_3d_steer for.
    assert builder.focus_options() == ['Focus wrt exit plane [mm]']


def test_power_options_excludes_engineering_only(igt_with_transducer):
    """Relies on the real, shipped ds_config.ini's own default ('Amplitude [%]' is
    engineering-only) rather than overriding it; this is exactly the real-world case the GUI
    must handle correctly."""
    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.power_options() == ['Max. pressure in free water [MPa]']


def _configure_igt_with_native_amplitude(patch_config):
    """A variant of igt_with_transducer's own setup where 'Amplitude [%]' (not 'Max. pressure in
    free water [MPa]') is native. ProtocolBuilder.__init__ re-reads DrivingSystem fresh from
    config at construction time (see TUSProtocol.__init__), so this must all be in place
    *before* a DrivingSystem is constructed, not applied to an already-built one (that's why
    this doesn't just reuse the igt_with_transducer fixture and patch it afterward)."""
    _configure_driving_system(patch_config, 'UNITTEST_IGT', manufacturer='IGT')
    patch_config.set('Equipment.Driving system.UNITTEST_IGT', 'Native power parameters',
                     'Amplitude [%]')
    # 'Amplitude [%]' is engineering-only in the real, shipped ds_config.ini (see
    # _configure_driving_system's own comment); irrelevant to what this test is about, so
    # cleared here rather than picking a still-engineering-only option as the native one.
    patch_config.set('Power', 'Engineering-only options', '')
    _configure_transducer(patch_config, 'UNITTEST_TRAN')

    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    return ds


def test_power_options_excludes_non_native_option_without_an_active_combo(patch_config):
    """No transducer given, and no Equipment.Combination.* section exists for
    UNITTEST_IGT~UNITTEST_TRAN, so the non-native option must not appear, matching the same
    reasoning focus_options() already applies to the xyz options."""
    ds = _configure_igt_with_native_amplitude(patch_config)

    builder = ProtocolBuilder(ds)

    assert builder.power_options() == ['Amplitude [%]']
    tran = builder.compatible_transducers()[0]
    assert builder.power_options(tran) == ['Amplitude [%]']


def test_power_options_includes_non_native_option_with_an_active_combo(patch_config):
    ds = _configure_igt_with_native_amplitude(patch_config)
    patch_config.set('Equipment.Combination.UNITTEST_IGT~UNITTEST_TRAN', 'Active?', 'True')

    builder = ProtocolBuilder(ds)
    tran = builder.compatible_transducers()[0]

    assert builder.power_options(tran) == ['Amplitude [%]', 'Max. pressure in free water [MPa]']


def test_compatible_transducers_filters_by_tran_comp(patch_config, igt_with_transducer):
    _configure_transducer(patch_config, 'UNITTEST_OTHER_TRAN')
    # UNITTEST_OTHER_TRAN is now active/globally listed, but not in this driving system's own
    # tran_comp (only UNITTEST_TRAN is, see _configure_driving_system's default).
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN\nUNITTEST_OTHER_TRAN')

    builder = ProtocolBuilder(igt_with_transducer)

    assert [t.serial for t in builder.compatible_transducers()] == ['UNITTEST_TRAN']


def test_can_add_slot_respects_max_tran_slots(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_IGT', manufacturer='IGT', max_tran_slots=1)
    _configure_transducer(patch_config, 'UNITTEST_TRAN')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_IGT')
    builder = ProtocolBuilder(ds)

    assert builder.can_add_slot() is True

    # 'Max. pressure in free water [MPa]', not 'Amplitude [%]': the latter is engineering-only
    # in the real, shipped ds_config.ini (confirmed directly), and this test isn't exercising
    # that filtering; see test_power_options_excludes_engineering_only for that.
    builder.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 20,
                     'Max. pressure in free water [MPa]', 0.5)

    assert builder.can_add_slot() is False


def test_validate_returns_empty_list_before_any_slot(igt_with_transducer):
    """Genuinely nothing wrong yet: a fresh protocol's own config-driven timing defaults are
    self-consistent, and there's no slot yet for either driving system's per-slot checks to
    report on. Not validate() skipping work just because protocol.slots is empty (see
    validate()'s own docstring: it always calls through now, see the next test)."""
    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.validate() == []


def test_validate_reports_a_timing_error_before_any_slot_exists(igt_with_transducer):
    """A researcher configuring timing before ever adding a transducer slot must still see a
    timing problem immediately: timing validation doesn't need a slot to exist at all (see
    ControlDrivingSystem.validate_protocol()'s own pulse_dur/pulse_rep_int check)."""
    builder = ProtocolBuilder(igt_with_transducer)
    builder.configure_timing(pulse_dur=10, pulse_rep_int=5)

    errors = builder.validate()

    assert any('Pulse Duration' in e for e in errors)


def test_validate_reports_a_slot_error_and_a_timing_error_together(igt_with_transducer):
    """Distinct from test_validate_reports_a_timing_error_before_any_slot_exists above: proves
    validate() surfaces a per-slot problem and a cross-field timing problem *together*, not just
    whichever one happens to be checked first. igt_with_transducer's own driving system has no
    active calibration combo, so 'Max. pressure...' (native here) still leaves slot.ampl at
    None (confirmed directly): IGT.validate_protocol()'s per-slot ampl check and
    ControlDrivingSystem.validate_protocol()'s own pulse_dur/pulse_rep_int check both fire on
    the very same protocol."""
    builder = ProtocolBuilder(igt_with_transducer)
    builder.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 20,
                     'Max. pressure in free water [MPa]', 0.5)
    assert builder.protocol.slots[0].ampl is None
    # pulse_dur (10) > pulse_rep_int (5) violates ControlDrivingSystem.validate_protocol()'s own
    # check.
    builder.configure_timing(pulse_dur=10, pulse_rep_int=5)

    errors = builder.validate()

    assert any('Pulse Duration' in e for e in errors)
    assert any('Amplitude is None' in e for e in errors)


def test_validate_is_clean_for_a_well_formed_protocol(patch_config):
    """Uses a Sonic-Concepts-manufactured synthetic driving system rather than
    igt_with_transducer: IGT.validate_protocol() also requires slot.ampl to be set, which is
    only ever derived from a *real*, active calibration combo (a genuine hardware fact: IGT's
    native power parameter is always amplitude, whatever power option was chosen), not something
    a synthetic, no-active-combo fixture like this one can produce. SonicConcepts.
    validate_protocol() only requires global_power, so it exercises the same "well-formed
    protocol validates clean" behavior without needing real calibration curve files."""
    _configure_driving_system(patch_config, 'UNITTEST_SC', manufacturer='Sonic Concepts')
    section = 'Equipment.Driving system.UNITTEST_SC'
    patch_config.set(section, 'Power options', 'Global power [mW]')
    patch_config.set(section, 'Native power parameters', 'Global power [mW]')
    _configure_transducer(patch_config, 'UNITTEST_TRAN')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')

    builder = ProtocolBuilder(ds)
    builder.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 20, 'Global power [mW]', 5.0)
    builder.configure_timing(pulse_dur=1, pulse_rep_int=2, pulse_train_dur=10)

    assert builder.validate() == []


def test_pressure_power_option_reads_the_configured_label(igt_with_transducer):
    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.pressure_power_option() == 'Max. pressure in free water [MPa]'


def test_demo_max_pressure_reads_the_configured_value(patch_config, igt_with_transducer):
    patch_config.set('Power', 'Demo maximum pressure allowed in free water [MPa]', '0.5')
    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.demo_max_pressure() == pytest.approx(0.5)


def test_uses_pulse_train_repetition_true_for_igt(igt_with_transducer):
    builder = ProtocolBuilder(igt_with_transducer)

    assert builder.uses_pulse_train_repetition() is True


def test_uses_pulse_train_repetition_false_for_sonic_concepts(patch_config):
    _configure_driving_system(patch_config, 'UNITTEST_SC', manufacturer='Sonic Concepts')
    section = 'Equipment.Driving system.UNITTEST_SC'
    patch_config.set(section, 'Power options', 'Global power [mW]')
    patch_config.set(section, 'Native power parameters', 'Global power [mW]')
    _configure_transducer(patch_config, 'UNITTEST_TRAN')
    from fus_driving_systems import driving_system
    ds = driving_system.DrivingSystem()
    ds.set_ds_info('UNITTEST_SC')
    builder = ProtocolBuilder(ds)

    assert builder.uses_pulse_train_repetition() is False


def test_create_control_instance_returns_a_fresh_instance_each_time(igt_with_transducer):
    """A distinct instance from builder's own internal _ds_instance (which stays throwaway,
    used only for validate()), and a distinct instance on every call: the Executing panel must
    never accidentally reuse one across two separate connections."""
    builder = ProtocolBuilder(igt_with_transducer)

    first = builder.create_control_instance()
    second = builder.create_control_instance()

    assert isinstance(first, IGT)
    assert first is not second
    assert first is not builder._ds_instance  # pylint: disable=protected-access
