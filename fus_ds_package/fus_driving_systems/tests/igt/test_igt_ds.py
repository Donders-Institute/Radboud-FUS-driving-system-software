# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.igt.igt_ds.IGT.

See tests/igt/conftest.py's module docstring for why these tests use the
real unifus native extension for enums/Pulse/sequenceDurationMs, only
patching unifus.FUSSystem (connect()'s sole hardware-touching seam) or the
specific instance (self.gen/self.fus/self.listener, via connected_instance)
downstream of a connection.
"""
import math
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from fus_driving_systems.config import logging_config
from fus_driving_systems.igt import unifus
from fus_driving_systems.igt.igt_ds import IGT


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:

    def test_init_sets_default_attributes(self, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        assert instance.sent_seqs == {}
        assert instance.fus is None
        assert instance.listener is None
        assert instance.n_channels == 0
        assert instance.connected is False

    def test_init_enables_crash_detection_when_not_already_enabled(self, tmp_path):
        """GitHub issue #126: crash detection is normally enabled centrally by whichever of
        initialize_logger()/sync_logger() a script/host application calls to set up logging
        (see logging_config.py) -- this is IGT's own safety net for the case neither has run
        yet, so constructing IGT() directly still gets *some* protection."""
        assert logging_config.is_crash_detection_enabled() is False

        IGT(log_dir=str(tmp_path))

        assert logging_config.is_crash_detection_enabled() is True
        assert (tmp_path / "faulthandler_output.log").exists()

    def test_init_skips_its_own_crash_detection_setup_when_already_enabled(self, mocker,
                                                                           tmp_path):
        """If initialize_logger()/sync_logger() already enabled crash detection (the normal
        case in every documented usage), IGT() must not redundantly call
        enable_crash_detection() again with its own log_dir."""
        logging_config.enable_crash_detection(str(tmp_path), str(tmp_path / "already_active"))
        enable_mock = mocker.patch("fus_driving_systems.igt.igt_ds.enable_crash_detection")

        IGT(log_dir=str(tmp_path / "unused"))

        enable_mock.assert_not_called()

    def test_init_creates_missing_log_dir(self, tmp_path):
        log_dir = tmp_path / "nested" / "log_dir"
        assert not log_dir.exists()

        IGT(log_dir=str(log_dir))

        assert log_dir.exists()


# ---------------------------------------------------------------------------
# is_sequence_sent() / register_sent_sequence()
# ---------------------------------------------------------------------------

class TestIsSequenceSent:
    """Note: IGT.is_sequence_sent(seq_num) takes a required seq_num arg,
    shadowing ControlDrivingSystem.is_sequence_sent() (no args) with an
    incompatible signature -- not a live bug (igt_ds.py always calls its
    own override with seq_num; SonicConcepts calls the base no-arg version
    on its own instances), but worth knowing if this is ever called
    polymorphically without knowing the concrete driving-system type."""

    def test_returns_true_when_seq_num_registered(self, igt_instance):
        igt_instance.sent_seqs[1] = {'seq': []}

        assert igt_instance.is_sequence_sent(1) is True

    def test_returns_false_when_seq_num_not_registered(self, igt_instance):
        assert igt_instance.is_sequence_sent(1) is False


class TestRegisterSentSequence:

    def test_stores_sequence_details_and_total_duration(self, igt_instance, mocker, patch_config):
        patch_config.set('Equipment.Manufacturer.IGT', 'Wait time before responsive [ms]', '50')
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=200.0)

        igt_instance.register_sent_sequence(1, seq=['pulse'], n_pulse_train_rep=3,
                                            pulse_train_delay=5.0, phases=[10.0, 20.0])

        stored = igt_instance.sent_seqs[1]
        assert stored['seq'] == ['pulse']
        assert stored['n_pulse_train_rep'] == 3
        assert stored['pulse_train_delay'] == 5.0
        assert stored['phases'] == [10.0, 20.0]
        assert stored['total_sequence_duration_ms'] == pytest.approx(250.0)  # 200 + 50


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------

class TestConnect:

    @pytest.fixture(autouse=True)
    def _no_real_sleep(self, mocker):
        """connect() now sleeps briefly after every disconnect-then-reconnect (including the
        attempt==0 defensive disconnect, GitHub issue #126) -- patched away so this test class
        doesn't actually pause for real seconds."""
        mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")

    def test_connect_uses_session_log_dir_for_native_igt_log_when_available(
            self, mocker, mock_fus_system, tmp_path):
        """See the matching test in TestInit -- connect() prefers the shared, timestamped
        session folder (get_session_log_dir()) for the native IGT log too, when one is active,
        instead of whatever log_dir happens to be passed to connect() itself."""
        session_dir = tmp_path / "2026-08-05_18-00-00_testrun"
        session_dir.mkdir()
        mocker.patch("fus_driving_systems.igt.igt_ds.get_session_log_dir",
                     return_value=str(session_dir))
        set_log_path_mock = mocker.patch("fus_driving_systems.igt.igt_ds.unifus.setLogPath")
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path / "unused"))

        set_log_path_mock.assert_called_once()
        assert set_log_path_mock.call_args[0][0] == str(session_dir)

    def test_connect_success_sets_connected_and_channel_count(self, mocker, mock_fus_system,
                                                              tmp_path):
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen

        instance = IGT(log_dir=str(tmp_path))
        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        assert instance.connected is True
        assert instance.n_channels == 8
        assert instance.gen is fake_gen
        mock_fus_system.loadConfig.assert_called_once()
        mock_fus_system.connect.assert_called_once()

    def test_connect_forces_a_defensive_disconnect_before_the_first_attempt(self, mocker,
                                                                            mock_fus_system,
                                                                            tmp_path):
        """Experimental mitigation for GitHub issue #126: a throwaway FUSSystem() is
        disconnected before the real connect attempt, in case a previous (possibly crashed)
        session left the native driver holding a stale connection this fresh process has no
        handle to. unifus.FUSSystem() is patched to always return mock_fus_system (see
        conftest.py), so the throwaway instance and the "real" one are indistinguishable here
        -- what matters is that clearListeners()/disconnect() get called exactly once before
        the real connect flow proceeds."""
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        assert mock_fus_system.clearListeners.call_count == 1
        assert mock_fus_system.disconnect.call_count == 1

    def test_connect_survives_when_the_defensive_disconnect_itself_raises(self, mocker,
                                                                          mock_fus_system,
                                                                          tmp_path):
        """The defensive disconnect is a best-effort experiment, not a requirement -- if it
        raises (e.g. nothing was there to clean up), connect() must still proceed normally."""
        mock_fus_system.isConnected.return_value = True
        mock_fus_system.disconnect.side_effect = RuntimeError("nothing to disconnect")
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True

    def test_connect_sleeps_after_the_defensive_disconnect_using_configured_delay(
            self, mocker, mock_fus_system, tmp_path, patch_config):
        """GitHub issue #126: repeatedly hammering the driver without any pause is, on its
        own, a plausible way to worsen an already-fragile connection -- a configurable delay
        follows every disconnect-then-reconnect, starting with the attempt==0 defensive one.

        The patched time.sleep is process-wide (the real time module, not a copy scoped to
        igt_ds.py), so it also picks up ExecListener.wait_connection()'s own unrelated 0.2s
        poll interval -- assertions below count only the reconnect-delay calls, not the full
        call list, to avoid coupling this test to that unrelated polling detail."""
        patch_config.set('General', 'Delay before reconnecting [s]', '3')
        sleep_mock = mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert sleep_mock.call_args_list.count(mocker.call(3.0)) == 1

    def test_connect_sleeps_between_retries_using_configured_delay(self, mocker, mock_fus_system,
                                                                   tmp_path, patch_config):
        """See the docstring above for why this only counts the reconnect-delay calls rather
        than asserting on the full call list."""
        patch_config.set('General', 'Maximum reconnection attempts', '1')
        patch_config.set('General', 'Delay before reconnecting [s]', '5')
        sleep_mock = mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        mock_fus_system.isConnected.return_value = False
        instance = IGT(log_dir=str(tmp_path))
        mocker.patch.object(instance, 'disconnect')  # not under test here

        with pytest.raises(SystemExit):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        # once for the attempt==0 defensive disconnect, once for the actual retry
        assert sleep_mock.call_args_list.count(mocker.call(5.0)) == 2

    def test_connect_exits_immediately_when_fus_system_construction_fails(self, mocker, tmp_path):
        mocker.patch("fus_driving_systems.igt.igt_ds.unifus.FUSSystem",
                     side_effect=RuntimeError("boom"))
        instance = IGT(log_dir=str(tmp_path))

        with pytest.raises(SystemExit):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

    def test_connect_retries_then_exits_when_never_reports_connected(self, mocker, mock_fus_system,
                                                                     tmp_path, patch_config):
        patch_config.set('General', 'Maximum reconnection attempts', '1')
        mock_fus_system.isConnected.return_value = False
        instance = IGT(log_dir=str(tmp_path))
        mocker.patch.object(instance, 'disconnect')  # not under test here

        with pytest.raises(SystemExit):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert instance.disconnect.call_count == 1  # exactly one retry attempted

    def test_connect_returns_true_after_a_successful_retry(self, mocker, mock_fus_system,
                                                           tmp_path, patch_config):
        """The boolean return value must propagate through a retry, not just the first
        (failed) attempt -- connect() recurses via 'return self.connect(...)'."""
        patch_config.set('General', 'Maximum reconnection attempts', '1')
        mock_fus_system.isConnected.side_effect = [False, True]  # fails once, then succeeds
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))
        mocker.patch.object(instance, 'disconnect')  # not under test here

        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        assert instance.connected is True

    def test_connect_skips_reconnection_when_already_connected(self, mocker, mock_fus_system,
                                                               tmp_path):
        """GitHub issues #103/#126: calling connect() while already connected used to always
        tear down and recreate the native unifus.FUSSystem() and re-register a listener on an
        already live connection, a plausible source of instability. It should now be a no-op
        that just confirms the existing connection."""
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = True

        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        mock_fus_system.loadConfig.assert_not_called()
        mock_fus_system.registerListener.assert_not_called()
        mock_fus_system.connect.assert_not_called()


# ---------------------------------------------------------------------------
# validate_sequence
# ---------------------------------------------------------------------------

def _valid_sequence(**overrides):
    values = dict(
        pulse_dur=1.0,
        pulse_rep_int=2.0,
        pulse_train_dur=20.0,
        pulse_train_rep_int=20.0,
        pulse_train_rep_dur=20.0,
        pulse_ramp_dur=0.0,
        pulse_ramp_shape='Rectangular - no ramping',
        ampl=[50.0],
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class TestValidateSequence:

    def test_valid_sequence_has_no_errors(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')

        errors = igt_instance.validate_sequence(_valid_sequence())

        assert errors == []

    def test_pulse_duration_below_minimum_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Min. pulse duration [ms]', '0.5')

        errors = igt_instance.validate_sequence(_valid_sequence(pulse_dur=0.1,
                                                                pulse_rep_int=1.0))

        assert any('Pulse duration' in e for e in errors)

    def test_pulse_rep_int_below_minimum_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Min. pulse rep. interval [ms]', '1.0')

        errors = igt_instance.validate_sequence(_valid_sequence(pulse_dur=0.05,
                                                                pulse_rep_int=0.1,
                                                                pulse_train_dur=1.0,
                                                                pulse_train_rep_int=1.0,
                                                                pulse_train_rep_dur=1.0))

        assert any('Pulse repetition interval' in e for e in errors)

    def test_ramping_too_long_relative_to_pulse_duration_is_flagged(self, igt_instance,
                                                                    patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT',
                         'Min. time in between ramping up and down [ms]', '0.1')

        errors = igt_instance.validate_sequence(_valid_sequence(
            pulse_dur=1.0, pulse_rep_int=1.0, pulse_ramp_dur=0.6, pulse_ramp_shape='Linear'))

        assert any('ramping' in e for e in errors)

    def test_amplitude_none_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')

        errors = igt_instance.validate_sequence(_valid_sequence(ampl=None))

        assert any('Amplitude is None' in e for e in errors)

    def test_too_many_pulses_in_pulse_train_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. pulses in pulse train', '4')

        errors = igt_instance.validate_sequence(_valid_sequence(
            pulse_dur=1.0, pulse_rep_int=1.0, pulse_train_dur=10.0,
            pulse_train_rep_int=10.0, pulse_train_rep_dur=10.0))

        assert any('maximum amount of pulses' in e for e in errors)


# ---------------------------------------------------------------------------
# _get_ramping_amplitude
# ---------------------------------------------------------------------------

class TestGetRampingAmplitude:

    def test_linear_ramp_is_evenly_spaced_from_zero_to_one(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        sequence = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(sequence, pulse_ramp_temp_res=2.0)

        assert ampl_ramp == pytest.approx(np.linspace(0, 1, 5))

    def test_tukey_ramp_starts_at_zero_and_ends_at_one(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        sequence = SimpleNamespace(pulse_ramp_shape='Tukey', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(sequence, pulse_ramp_temp_res=2.0)

        assert len(ampl_ramp) == 5
        assert ampl_ramp[0] == pytest.approx(0.0, abs=1e-9)
        assert ampl_ramp[-1] == pytest.approx(1.0, abs=1e-9)
        assert np.all(np.diff(ampl_ramp) >= -1e-9)  # monotonically non-decreasing


class TestApplyRamping:
    """_apply_ramping builds ramp_up/ramp_down int-percentage arrays from
    _get_ramping_amplitude (already thoroughly tested above) and passes
    them to self.gen.setPulseModulation -- these tests only need to check
    that hand-off, not re-derive the ramp math itself."""

    def test_calls_set_pulse_modulation_with_ramp_arrays(self, connected_instance, patch_config):
        patch_config.set('Equipment.Manufacturer.IGT',
                         'Min. temporal ramping resolution [ms]', '2')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. amount of ramping steps', '1023')
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        sequence = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        connected_instance._apply_ramping(sequence)

        connected_instance.gen.setPulseModulation.assert_called_once()
        ramp_up, up_res, ramp_down, down_res = \
            connected_instance.gen.setPulseModulation.call_args[0]
        assert up_res == pytest.approx(2.0)
        assert down_res == pytest.approx(2.0)
        assert ramp_down == [0, 25, 50, 75, 100]  # linspace(0,1,5) * 100, int()
        assert ramp_up == list(reversed(ramp_down))  # "ramp up descends" per the source comment

    def test_clamps_temporal_resolution_when_step_count_exceeds_max(self, connected_instance,
                                                                    patch_config):
        patch_config.set('Equipment.Manufacturer.IGT',
                         'Min. temporal ramping resolution [ms]', '0.1')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. amount of ramping steps', '10')
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        # ramp_n_steps = pulse_ramp_dur / min_res = 10 / 0.1 = 100 > max_steps (10)
        # -> min_ramp_temp_res gets recomputed as pulse_ramp_dur / max_steps = 1.0
        sequence = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        connected_instance._apply_ramping(sequence)

        _, up_res, _, down_res = connected_instance.gen.setPulseModulation.call_args[0]
        assert up_res == pytest.approx(1.0)
        assert down_res == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _define_pulse_train
# ---------------------------------------------------------------------------

class TestDefinePulseTrain:

    def test_builds_pulse_train_list_and_computes_delay(self, igt_instance):
        pulse = object()
        sequence = SimpleNamespace(pulse_train_dur=10.0, pulse_rep_int=2.0,
                                   pulse_train_rep_int=15.0)

        seq, pulse_train_delay = igt_instance._define_pulse_train(sequence, pulse)

        assert seq == [pulse] * 5
        assert pulse_train_delay == pytest.approx(5.0)

    def test_floors_partial_pulses(self, igt_instance):
        pulse = object()
        sequence = SimpleNamespace(pulse_train_dur=9.0, pulse_rep_int=2.0,
                                   pulse_train_rep_int=9.0)

        seq, pulse_train_delay = igt_instance._define_pulse_train(sequence, pulse)

        assert len(seq) == math.floor(9.0 / 2.0)  # 4, not 4.5
        assert pulse_train_delay == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _define_pulse / _define_two_tran_slots (real unifus.Pulse, no unifus mocking)
# ---------------------------------------------------------------------------

class TestDefinePulse:

    def test_uses_override_phases_when_dephasing_matches_element_count(self, connected_instance):
        connected_instance.n_channels = 2
        fake_transducer = SimpleNamespace(elements=2, steer_info='dummy.ini', natural_foc=0)
        sequence = SimpleNamespace(
            pulse_dur=1.0, pulse_rep_int=2.0, oper_freq=250,
            ampl=[50, 60], dephasing_degree=[10.0, 20.0],
            transducer=fake_transducer, focus_wrt_mid_bowl=50,
        )

        pulse, phases = connected_instance._define_pulse(sequence)

        assert phases == [10.0, 20.0]
        assert pulse.frequencyCount() == 1
        assert pulse.frequency(0) == 250_000
        assert pulse.amplitude(0) == 50
        assert pulse.amplitude(1) == 60
        assert pulse.phase(0) == pytest.approx(10.0)
        assert pulse.phase(1) == pytest.approx(20.0)
        assert pulse.duration() == pytest.approx(1.0)
        assert pulse.delay() == pytest.approx(1.0)  # round(2.0 - 1.0, 1)

    def test_exits_when_amplitude_is_none(self, connected_instance):
        connected_instance.n_channels = 2
        sequence = SimpleNamespace(
            pulse_dur=1.0, pulse_rep_int=2.0, oper_freq=250, ampl=None,
            dephasing_degree=None, transducer=SimpleNamespace(elements=2),
        )

        with pytest.raises(SystemExit):
            connected_instance._define_pulse(sequence)

    def test_computes_phases_via_real_transducer_ini_definition(self, connected_instance):
        """End-to-end (no mocking): _set_phases resolves the bundled real
        .ini transducer file via importlib.resources, transducer_xyz.Transducer
        loads and parses it from disk, and compute_phases runs real trig on
        the resulting elements. Exercises the whole non-dephasing-override
        chain at once."""
        connected_instance.n_channels = 10
        fake_transducer = SimpleNamespace(
            elements=10,
            steer_info='igt/config/imasonic_transducers/transducer_15287_10_300kHz.ini',
            natural_foc=75,
        )
        sequence = SimpleNamespace(
            pulse_dur=1.0, pulse_rep_int=2.0, oper_freq=300,
            ampl=[50] * 10, dephasing_degree=None,
            transducer=fake_transducer, focus_wrt_mid_bowl=75,
        )

        pulse, phases = connected_instance._define_pulse(sequence)

        assert len(phases) == 10
        assert pulse.phaseCount() == 10
        for i, phase in enumerate(phases):
            assert pulse.phase(i) == pytest.approx(phase)


class TestSetPhasesIniBranch:

    def test_ini_branch_loads_real_transducer_and_computes_phases(self, connected_instance):
        """
        Direct test of _set_phases's .ini branch, for symmetry with
        TestSetPhasesExcelBranch's direct tests of the .xlsx branch below.
        (test_computes_phases_via_real_transducer_ini_definition in
        TestDefinePulse already exercises this same path end-to-end via
        _define_pulse -- this test isolates _set_phases itself, calling it
        directly the same way TestSetPhasesExcelBranch does for the other
        branch, with a real unifus.Pulse built the same way _define_pulse
        builds one.)
        """
        connected_instance.n_channels = 10
        pulse = unifus.Pulse(connected_instance.n_channels, 1, 1)
        pulse.setFrequencies([300_000])

        phases = connected_instance._set_phases(
            pulse, focus=75,
            steer_info='igt/config/imasonic_transducers/transducer_15287_10_300kHz.ini',
            natural_foc=75, dephasing_degree=None)

        assert len(phases) == 10


class TestSetPhasesExcelBranch:

    def test_excel_branch_returns_matching_row_as_phases(self, mocker, connected_instance):
        """
        Regression test for a real bug: the .xlsx steer-info branch of
        _set_phases used to build
            phases = [match_row.iloc[0].iloc[1:n+1]].to_list()
        -- the outer `[...]` made this a *plain Python list* containing one
        pandas Series, and then `.to_list()` was called on that outer list.
        Python lists have no `.to_list()` method (only pandas
        Series/DataFrames do), so this always raised AttributeError
        whenever a matching focus row was actually found. Fixed by removing
        the erroneous outer `[...]` so `.to_list()` is called on the Series
        itself: `phases = match_row.iloc[0].iloc[1:n+1].to_list()`.
        """
        connected_instance.n_channels = 2
        df = pd.DataFrame({'Distance': [50.0], 'ch0': [10.0], 'ch1': [20.0]})
        mocker.patch('fus_driving_systems.igt.igt_ds.pd.read_excel', return_value=df)
        mocker.patch('fus_driving_systems.igt.igt_ds.os.path.exists', return_value=True)

        phases = connected_instance._set_phases(mocker.Mock(), focus=50.0,
                                                steer_info='some_table.xlsx',
                                                natural_foc=75, dephasing_degree=None)

        assert phases == [10.0, 20.0]

    def test_excel_branch_exits_when_file_does_not_exist(self, mocker, connected_instance):
        connected_instance.n_channels = 2
        mocker.patch('fus_driving_systems.igt.igt_ds.os.path.exists', return_value=False)

        with pytest.raises(SystemExit):
            connected_instance._set_phases(mocker.Mock(), focus=50.0, steer_info='missing.xlsx',
                                           natural_foc=75, dephasing_degree=None)

    def test_exits_when_steer_info_is_neither_ini_nor_xlsx(self, mocker, connected_instance):
        """DUMMY/CITRUS transducers configure an empty 'Steer information'
        string (they're never used with an IGT driving system either), so
        an unrecognized extension should be rejected rather than silently
        misbehaving."""
        connected_instance.n_channels = 2

        with pytest.raises(SystemExit):
            connected_instance._set_phases(mocker.Mock(), focus=50.0, steer_info='',
                                           natural_foc=75, dephasing_degree=None)


class TestDefineTwoTranSlots:

    def test_combines_phases_frequencies_and_amplitudes_from_both_sequences(self,
                                                                            connected_instance):
        connected_instance.n_channels = 4
        tran1 = SimpleNamespace(elements=2)
        tran2 = SimpleNamespace(elements=2)
        seq1 = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, oper_freq=250, ampl=[50],
                               dephasing_degree=[1.0, 2.0], transducer=tran1)
        seq2 = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, oper_freq=300, ampl=[60, 70],
                               dephasing_degree=[3.0, 4.0], transducer=tran2)

        pulse, phases = connected_instance._define_two_tran_slots(seq1, seq2)

        assert phases == [1.0, 2.0, 3.0, 4.0]
        assert [pulse.amplitude(i) for i in range(4)] == [50, 50, 60, 70]
        assert pulse.frequency(0) == 250_000
        assert pulse.frequency(2) == 300_000


# ---------------------------------------------------------------------------
# send_sequence
# ---------------------------------------------------------------------------

class TestSendSequence:

    def test_defines_pulse_registers_and_sends_when_connected(self, mocker, connected_instance,
                                                              patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_sequence', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse',
                            return_value=(fake_pulse, [1.0, 2.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse, fake_pulse], 5.0))
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_sequence = SimpleNamespace(seq_num=1, pulse_train_rep_dur=20, pulse_train_rep_int=10,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.send_sequence(fake_sequence)

        connected_instance.gen.sendSequence.assert_called_once_with(1, [fake_pulse, fake_pulse])
        assert connected_instance.is_sequence_sent(1) is True

    def test_exits_when_validation_produces_errors(self, mocker, connected_instance):
        mocker.patch.object(connected_instance, 'validate_sequence',
                            return_value=['something is wrong'])
        fake_sequence = SimpleNamespace(seq_num=1)

        with pytest.raises(SystemExit):
            connected_instance.send_sequence(fake_sequence)

    def test_exits_when_seq3_and_seq4_given_without_seq2(self, mocker, connected_instance):
        """Regression test for a real bug: pulse2 was only ever assigned
        inside the 'seq2 is given' branch, but the seq3/seq4 pulse-train
        path below it was reached independently of seq2 -- so calling
        send_sequence(seq1, seq3=X, seq4=Y) without seq2 raised a raw
        NameError on 'pulse2' instead of a clean validation error. Fixed by
        rejecting this parameter combination up front."""
        mocker.patch.object(connected_instance, 'validate_sequence', return_value=[])
        seq1 = SimpleNamespace(seq_num=1)
        seq3 = SimpleNamespace()
        seq4 = SimpleNamespace()

        with pytest.raises(SystemExit):
            connected_instance.send_sequence(seq1, seq3=seq3, seq4=seq4)

    def test_reconnects_and_retries_when_not_connected(self, mocker, tmp_path):
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = False

        def fake_connect(connect_info):
            instance.connected = True
            instance.gen = mocker.Mock()
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)
        mocker.patch.object(instance, 'validate_sequence', return_value=[])
        mocker.patch.object(instance, '_define_pulse', return_value=(mocker.Mock(), [1.0]))
        mocker.patch.object(instance, '_define_pulse_train',
                            return_value=([mocker.Mock()], 5.0))
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_sequence = SimpleNamespace(
            seq_num=1, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_train_rep_dur=20, pulse_train_rep_int=10,
            pulse_ramp_shape='Rectangular - no ramping')

        instance.send_sequence(fake_sequence)

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        assert instance.is_sequence_sent(1) is True

    def test_sends_two_transducer_slots_with_combined_pulse_train_when_four_sequences_given(
            self, mocker, connected_instance, patch_config):
        """The seq3/seq4 path is not just 'more of the same' as a single
        sequence: n_pulse_train_rep is computed from duration_ms and
        seq1+seq3's pulse_train_dur (not seq1.pulse_train_rep_dur/int),
        and _define_two_tran_slots is called twice."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_sequence', return_value=[])
        fake_pulse1, fake_pulse2 = mocker.Mock(), mocker.Mock()
        mocker.patch.object(connected_instance, '_define_two_tran_slots',
                            side_effect=[(fake_pulse1, [1.0]), (fake_pulse2, [2.0])])
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        seq1 = SimpleNamespace(seq_num=1, pulse_train_dur=10,
                               pulse_ramp_shape='Rectangular - no ramping')
        seq2 = SimpleNamespace()
        seq3 = SimpleNamespace(pulse_train_dur=15)
        seq4 = SimpleNamespace()

        connected_instance.send_sequence(seq1, seq2, seq3, seq4, duration_ms=100)

        # n_pulse_train_rep = floor(duration_ms / (seq1.pulse_train_dur + seq3.pulse_train_dur))
        #                    = floor(100 / (10 + 15)) = 4
        connected_instance.gen.sendSequence.assert_called_once_with(1, [fake_pulse1, fake_pulse2])
        stored = connected_instance.sent_seqs[1]
        assert stored['n_pulse_train_rep'] == 4
        assert stored['pulse_train_delay'] == 0

    def test_applies_ramping_when_ramp_shape_is_not_rectangular(self, mocker, connected_instance,
                                                                patch_config):
        """Only the rectangular/no-ramping branch was exercised elsewhere
        (via gen.setPulseModulation/setPulseRamp); this confirms
        send_sequence actually routes to _apply_ramping (already tested in
        isolation above) for any other ramp shape."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_sequence', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse', return_value=(fake_pulse, [1.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse], 5.0))
        mock_apply_ramping = mocker.patch.object(connected_instance, '_apply_ramping')
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_sequence = SimpleNamespace(seq_num=1, pulse_train_rep_dur=20,
                                        pulse_train_rep_int=10, pulse_ramp_shape='Linear')

        connected_instance.send_sequence(fake_sequence)

        mock_apply_ramping.assert_called_once_with(fake_sequence)
        connected_instance.gen.setPulseModulation.assert_not_called()


# ---------------------------------------------------------------------------
# execute_sequence
# ---------------------------------------------------------------------------

class TestExecuteSequence:

    def test_starts_sequence_and_waits_when_already_sent(self, mocker, connected_instance):
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=False)

        connected_instance.gen.prepareSequence.assert_called_once_with(1, 2, 5.0, mocker.ANY)
        connected_instance.gen.startSequence.assert_called_once()
        connected_instance.listener.wait_sequence.assert_called_once_with(0.5)

    def test_debug_info_true_sets_measure_channels_flag_for_long_pulse(self, connected_instance):
        """debug_info=True (the default) computes extra exec_flags based on
        pulse_dur, mirroring TestWaitForTrigger's identical coverage of
        this same logic. execute_sequence has no trigger_option flag
        addition, so no extra flag needs to be added to `expected` here."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=5.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureChannels)
        assert int(exec_flags) == int(expected)

    def test_debug_info_true_sets_measure_boards_flag_for_medium_pulse(self, connected_instance):
        """Same as above, one threshold down: pulse_dur between the
        MeasureBoards (0.035 ms) and MeasureChannels (4.570 ms) defaults."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=1.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureBoards)
        assert int(exec_flags) == int(expected)

    def test_debug_info_true_sets_measure_timings_flag_for_short_pulse(self, connected_instance):
        """Same as above, lowest threshold: pulse_dur between the
        MeasureTimings (0.001 ms) and MeasureBoards (0.035 ms) defaults."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.01, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureTimings)
        assert int(exec_flags) == int(expected)

    def test_sends_sequence_first_when_not_yet_sent(self, mocker, connected_instance):
        mock_send = mocker.patch.object(connected_instance, 'send_sequence')

        def fake_send(*args, **kwargs):
            connected_instance.sent_seqs[99] = {
                'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                'total_sequence_duration_ms': 10.0}
        mock_send.side_effect = fake_send

        fake_sequence = SimpleNamespace(seq_num=99)

        connected_instance.execute_sequence(fake_sequence, debug_info=False)

        mock_send.assert_called_once()
        connected_instance.gen.startSequence.assert_called_once()

    def test_reconnects_sends_and_executes_when_not_connected(self, mocker, tmp_path):
        """Mirrors TestSendSequence's reconnect test -- execute_sequence
        has the identical 'not connected -> connect(), then retry' shape.

        Regression test: the retry call used to not forward debug_info, so
        it always reconnected-and-retried with the True default. fake_sequence
        deliberately has no pulse_dur/pulse_ramp_dur/pulse_ramp_shape: if
        debug_info ever silently reverts to True again, this test fails with
        an AttributeError instead of passing (see TestWaitForTrigger's
        identical regression test for how this bug was originally found)."""
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = False

        def fake_connect(connect_info):
            instance.connected = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_sequence(*args, **kwargs):
            instance.sent_seqs[1] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                     'total_sequence_duration_ms': 10.0}
        mock_send = mocker.patch.object(instance, 'send_sequence', side_effect=fake_send_sequence)

        fake_sequence = SimpleNamespace(
            seq_num=1, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'))

        instance.execute_sequence(fake_sequence, debug_info=False)

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        mock_send.assert_called_once()
        instance.gen.startSequence.assert_called_once()

    def test_exits_on_exception_during_execution(self, connected_instance):
        """The broad 'except Exception: sys.exit' wrapper around the
        prepare/start/wait calls -- any hardware-layer failure should
        surface as a SystemExit, not propagate raw."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        connected_instance.gen.prepareSequence.side_effect = RuntimeError('hardware fault')
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        with pytest.raises(SystemExit):
            connected_instance.execute_sequence(fake_sequence, debug_info=False)

    def test_exits_when_listener_reports_sequence_execution_error(self, connected_instance):
        """GitHub issue #112: unifus.FUSListener's onSequenceResult callback used to only log
        the error (see igt/utils.py's ExecListener) -- execute_sequence() itself never noticed,
        so the program silently continued as if ultrasound had actually been emitted.

        unifus.FUSListener's own docstring states exceptions raised inside its callbacks are
        not propagated to Python, so sys.exit() cannot live inside onSequenceResult itself --
        it has to be raised here, in execute_sequence(), after wait_sequence() returns on the
        calling thread. ExecListener.onSequenceResult() stores the failure on
        self.exec_error_code (a plain attribute set, unaffected by that restriction); this
        checks that execute_sequence() then acts on it."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        connected_instance.listener.exec_error_code = 2863311530
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        with pytest.raises(SystemExit):
            connected_instance.execute_sequence(fake_sequence, debug_info=False)

    def test_does_not_exit_when_listener_reports_no_error(self, connected_instance):
        """Mirrors the test above: a successful execution (exec_error_code left at None by
        ExecListener.onSequenceResult()) must not raise."""
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                            'total_sequence_duration_ms': 500.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=False)  # must not raise

        connected_instance.listener.wait_sequence.assert_called_once()


# ---------------------------------------------------------------------------
# wait_for_trigger
# ---------------------------------------------------------------------------

class TestWaitForTrigger:

    def test_sequence_trigger_prepares_with_n_triggers_and_zero_delay(self, mocker,
                                                                      connected_instance,
                                                                      patch_config):
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerSequence', n_triggers=3)

        connected_instance.wait_for_trigger(fake_sequence, debug_info=False)

        connected_instance.gen.prepareSequence.assert_called_once_with(1, 3, 0, mocker.ANY)
        connected_instance.gen.startSequence.assert_called_once()

    def test_debug_info_true_sets_measure_channels_flag_for_long_pulse(self, connected_instance,
                                                                       patch_config):
        """debug_info=True (the default) computes extra exec_flags based on
        pulse_dur -- a separate code path from the reconnect-retry
        forwarding logic above, so it needs its own direct coverage.
        pulse_dur above the MeasureChannels threshold (default 4.570 ms)
        sets that flag. Note: MeasureChannels/MeasureBoards/MeasureTimings
        are not independent bits (3/2/1), so the resulting flags are
        compared for exact equality rather than checked with '&'."""
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=5.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerSequence', n_triggers=3)

        connected_instance.wait_for_trigger(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureChannels)
        assert int(exec_flags) == int(expected)

    def test_debug_info_true_sets_measure_boards_flag_for_medium_pulse(self, connected_instance,
                                                                       patch_config):
        """Same as above, one threshold down: pulse_dur between the
        MeasureBoards (0.035 ms) and MeasureChannels (4.570 ms) defaults."""
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=1.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerSequence', n_triggers=3)

        connected_instance.wait_for_trigger(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureBoards)
        assert int(exec_flags) == int(expected)

    def test_debug_info_true_sets_measure_timings_flag_for_short_pulse(self, connected_instance,
                                                                       patch_config):
        """Same as above, lowest threshold: pulse_dur between the
        MeasureTimings (0.001 ms) and MeasureBoards (0.035 ms) defaults."""
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_dur=0.01, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerSequence', n_triggers=3)

        connected_instance.wait_for_trigger(fake_sequence, debug_info=True)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureTimings)
        assert int(exec_flags) == int(expected)

    def test_ptr_trigger_prepares_with_stored_repetition_and_delay(self, mocker,
                                                                   connected_instance,
                                                                   patch_config):
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerOnePulseTrainRepetition',
                                        n_triggers=0)

        connected_instance.wait_for_trigger(fake_sequence, debug_info=False)

        connected_instance.gen.prepareSequence.assert_called_once_with(1, 2, 5.0, mocker.ANY)

    def test_unknown_trigger_option_exits(self, connected_instance, patch_config):
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_sequence = SimpleNamespace(seq_num=1, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='Bogus',
                                        get_trigger_options=lambda: [])

        with pytest.raises(SystemExit):
            connected_instance.wait_for_trigger(fake_sequence, debug_info=False)

    def test_sends_sequence_first_when_not_yet_sent(self, mocker, connected_instance):
        mock_send = mocker.patch.object(connected_instance, 'send_sequence')

        def fake_send(*args, **kwargs):
            connected_instance.sent_seqs[42] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0}
        mock_send.side_effect = fake_send

        fake_sequence = SimpleNamespace(seq_num=42, trigger_option='None', n_triggers=0)

        with pytest.raises(SystemExit):
            # trigger_option 'None' does not match the real config's
            # Option.seq/Option.ptr -> the recursive wait_for_trigger call
            # (made with real, unmocked send_sequence-state) exits; we only
            # care that send_sequence was invoked first, i.e. before that.
            connected_instance.wait_for_trigger(fake_sequence, debug_info=False)

        mock_send.assert_called_once()

    def test_reconnects_sends_and_waits_when_not_connected(self, mocker, tmp_path, patch_config):
        """
        Mirrors execute_sequence's reconnect test -- wait_for_trigger has
        the identical 'not connected -> connect(), then retry' shape.

        Regression test: the retry call in this branch used to be
        `self.wait_for_trigger(seq1, seq2, seq3, seq4, duration_ms)` --
        debug_info was NOT forwarded, so the retry always used debug_info's
        default (True) regardless of what the original caller passed. This
        was discovered because passing debug_info=False here (as every
        other test in this class does, with a minimal fake_sequence) still
        required a full `pulse_dur` attribute below -- the retry's
        debug_info=True path read it even though the caller asked for
        debug_info=False. Fixed by forwarding debug_info on the retry call.
        fake_sequence deliberately has no pulse_dur/pulse_ramp_dur/
        pulse_ramp_shape: if debug_info ever silently reverts to True again,
        this test fails with an AttributeError instead of passing, same as
        how the bug was originally found. Same bug shape existed in
        execute_sequence's identical reconnect branch, fixed there too.
        """
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = False

        def fake_connect(connect_info):
            instance.connected = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_sequence(*args, **kwargs):
            instance.sent_seqs[1] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}
        mock_send = mocker.patch.object(instance, 'send_sequence', side_effect=fake_send_sequence)

        fake_sequence = SimpleNamespace(
            seq_num=1, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            trigger_option='TriggerSequence', n_triggers=3)

        instance.wait_for_trigger(fake_sequence, debug_info=False)

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        mock_send.assert_called_once()
        instance.gen.startSequence.assert_called_once()

    def test_exits_on_exception_during_trigger_wait(self, connected_instance, patch_config):
        """The broad 'except Exception: sys.exit' wrapper around the
        prepare/start calls -- any hardware-layer failure should surface
        as a SystemExit, not propagate raw."""
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        connected_instance.sent_seqs = {1: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        connected_instance.gen.prepareSequence.side_effect = RuntimeError('hardware fault')
        fake_sequence = SimpleNamespace(seq_num=1, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='TriggerSequence', n_triggers=3)

        with pytest.raises(SystemExit):
            connected_instance.wait_for_trigger(fake_sequence, debug_info=False)


# ---------------------------------------------------------------------------
# wait_for_trigger_result
# ---------------------------------------------------------------------------

class TestWaitForTriggerResult:
    """GitHub issue #112: unlike execute_sequence(), wait_for_trigger() only arms the sequence
    to fire on the external trigger and returns immediately -- it never waits for or observes
    the actual (eventual, externally-triggered) execution result. wait_for_trigger_result() is
    the method a caller invokes separately, once the external trigger is expected to have
    fired, to block until completion and check the listener's exec_error_code."""

    def test_exits_when_listener_reports_sequence_execution_error(self, connected_instance):
        connected_instance.listener.exec_error_code = 2863311530

        with pytest.raises(SystemExit):
            connected_instance.wait_for_trigger_result()

        connected_instance.listener.wait_sequence.assert_called_once_with(5.0)

    def test_does_not_exit_when_listener_reports_no_error(self, connected_instance):
        connected_instance.wait_for_trigger_result(timeout_s=10.0)  # must not raise

        connected_instance.listener.wait_sequence.assert_called_once_with(10.0)


# ---------------------------------------------------------------------------
# has_execution_error
# ---------------------------------------------------------------------------

class TestHasExecutionError:
    """Non-blocking counterpart to wait_for_trigger_result(): a plain getter over
    self.listener.exec_error_code, meant to be polled repeatedly by the caller's own code for
    real-time reaction while waiting for an external trigger, instead of only finding out once
    a blocking wait_for_trigger_result() call is made."""

    def test_returns_error_code_when_listener_reports_an_error(self, connected_instance):
        connected_instance.listener.exec_error_code = 2863311530

        assert connected_instance.has_execution_error() == 2863311530

    def test_returns_none_when_listener_reports_no_error(self, connected_instance):
        assert connected_instance.has_execution_error() is None

    def test_does_not_block_or_exit(self, connected_instance):
        """Unlike wait_for_trigger_result(), this must never call wait_sequence() or raise --
        it is a pure, immediate getter."""
        connected_instance.listener.exec_error_code = 2863311530

        connected_instance.has_execution_error()  # must not raise

        connected_instance.listener.wait_sequence.assert_not_called()


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------

class TestDisconnect:

    def test_stops_sequence_and_marks_disconnected(self, mocker, connected_instance):
        mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        connected_instance.fus.isConnected.return_value = False

        connected_instance.disconnect()

        connected_instance.gen.stopSequence.assert_called_once()
        connected_instance.fus.clearListeners.assert_called_once()
        connected_instance.fus.disconnect.assert_called_once()
        assert connected_instance.connected is False

    def test_marks_still_connected_when_fus_still_reports_connected(self, mocker,
                                                                    connected_instance):
        mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        connected_instance.fus.isConnected.return_value = True

        connected_instance.disconnect()

        assert connected_instance.connected is True

    def test_noop_when_never_connected(self, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        instance.disconnect()  # gen and fus both None; must not raise
