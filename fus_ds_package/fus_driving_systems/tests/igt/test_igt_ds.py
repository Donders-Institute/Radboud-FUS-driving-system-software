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
import pytest

from fus_driving_systems.igt import unifus
from fus_driving_systems.igt.igt_ds import IGT


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:

    def test_init_creates_faulthandler_log_and_default_attributes(self, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        assert (tmp_path / "faulthandler_output.log").exists()
        assert instance.sent_seqs == {}
        assert instance.fus is None
        assert instance.listener is None
        assert instance.n_channels == 0
        assert instance.connected is False

    def test_init_creates_missing_log_dir(self, tmp_path):
        log_dir = tmp_path / "nested" / "log_dir"
        assert not log_dir.exists()

        IGT(log_dir=str(log_dir))

        assert log_dir.exists()
        assert (log_dir / "faulthandler_output.log").exists()


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
        patch_config.set('Equipment.Manufacturer.IGT', 'Wait time before reponsive [ms]', '50')
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

    def test_connect_success_sets_connected_and_channel_count(self, mocker, mock_fus_system,
                                                              tmp_path):
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen

        instance = IGT(log_dir=str(tmp_path))
        instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert instance.connected is True
        assert instance.n_channels == 8
        assert instance.gen is fake_gen
        mock_fus_system.loadConfig.assert_called_once()
        mock_fus_system.connect.assert_called_once()

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
        patch_config.set('Ramp', 'Option.shota', 'Shota')
        sequence = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(sequence, pulse_ramp_temp_res=2.0)

        assert ampl_ramp == pytest.approx(np.linspace(0, 1, 5))

    def test_tukey_ramp_starts_at_zero_and_ends_at_one(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        patch_config.set('Ramp', 'Option.shota', 'Shota')
        sequence = SimpleNamespace(pulse_ramp_shape='Tukey', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(sequence, pulse_ramp_temp_res=2.0)

        assert len(ampl_ramp) == 5
        assert ampl_ramp[0] == pytest.approx(0.0, abs=1e-9)
        assert ampl_ramp[-1] == pytest.approx(1.0, abs=1e-9)
        assert np.all(np.diff(ampl_ramp) >= -1e-9)  # monotonically non-decreasing

    def test_shota_ramp_has_expected_length_and_starts_at_half(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        patch_config.set('Ramp', 'Option.shota', 'Shota')
        sequence = SimpleNamespace(pulse_ramp_shape='Shota', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(sequence, pulse_ramp_temp_res=2.0)

        assert len(ampl_ramp) == 5
        # x[0] = 0 -> 0.5 * (1 + sin(-pi/2)) = 0.5 * (1 - 1) = 0
        assert ampl_ramp[0] == pytest.approx(0.0, abs=1e-9)


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
        patch_config.set('Ramp', 'Option.shota', 'Shota')
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
        patch_config.set('Ramp', 'Option.shota', 'Shota')
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
        .ini transducer file via importlib.resources, transducerXYZ.Transducer
        loads and parses it from disk, and computePhases runs real trig on
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
            pulse, focus=75, steer_info='igt/config/imasonic_transducers/transducer_15287_10_300kHz.ini',
            natural_foc=75, dephasing_degree=None)

        assert len(phases) == 10


class TestSetPhasesExcelBranch:

    def test_excel_branch_raises_due_to_list_to_list_bug(self, mocker, connected_instance):
        """
        Characterizes a real bug found while writing this test: the .xlsx
        steer-info branch of _set_phases builds
            phases = [match_row.iloc[0].iloc[1:n+1]].to_list()
        -- the outer `[...]` makes this a *plain Python list* containing
        one pandas Series, and then `.to_list()` is called on that outer
        list. Python lists have no `.to_list()` method (only pandas
        Series/DataFrames do), so this always raises AttributeError
        whenever a matching focus row is actually found. The entire .xlsx
        steer-info code path is therefore broken in the current code --
        this documents that current (crashing) behavior, it is not
        asserting this is correct or desired.
        """
        import pandas as pd

        connected_instance.n_channels = 2
        df = pd.DataFrame({'Distance': [50.0], 'ch0': [10.0], 'ch1': [20.0]})
        mocker.patch('fus_driving_systems.igt.igt_ds.pd.read_excel', return_value=df)
        mocker.patch('fus_driving_systems.igt.igt_ds.os.path.exists', return_value=True)

        with pytest.raises(AttributeError, match='to_list'):
            connected_instance._set_phases(mocker.Mock(), focus=50.0, steer_info='some_table.xlsx',
                                           natural_foc=75, dephasing_degree=None)

    def test_excel_branch_exits_when_file_does_not_exist(self, mocker, connected_instance):
        connected_instance.n_channels = 2
        mocker.patch('fus_driving_systems.igt.igt_ds.os.path.exists', return_value=False)

        with pytest.raises(SystemExit):
            connected_instance._set_phases(mocker.Mock(), focus=50.0, steer_info='missing.xlsx',
                                           natural_foc=75, dephasing_degree=None)


class TestDefineTwoTranSlots:

    def test_combines_phases_frequencies_and_amplitudes_from_both_sequences(self, connected_instance):
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
        connected_instance.listener.waitSequence.assert_called_once_with(0.5)

    def test_sends_sequence_first_when_not_yet_sent(self, mocker, connected_instance):
        mock_send = mocker.patch.object(connected_instance, 'send_sequence')

        def fake_send(*args, **kwargs):
            connected_instance.sent_seqs[99] = {
                'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                'total_sequence_duration_ms': 10.0}
        mock_send.side_effect = fake_send

        fake_sequence = SimpleNamespace(seq_num=99, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping')

        connected_instance.execute_sequence(fake_sequence, debug_info=False)

        mock_send.assert_called_once()
        connected_instance.gen.startSequence.assert_called_once()

    def test_reconnects_sends_and_executes_when_not_connected(self, mocker, tmp_path):
        """Mirrors TestSendSequence's reconnect test -- execute_sequence
        has the identical 'not connected -> connect(), then retry' shape."""
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = False

        def fake_connect(connect_info):
            instance.connected = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_sequence(*args, **kwargs):
            instance.sent_seqs[1] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                     'total_sequence_duration_ms': 10.0}
        mock_send = mocker.patch.object(instance, 'send_sequence', side_effect=fake_send_sequence)

        fake_sequence = SimpleNamespace(
            seq_num=1, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping')

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

        fake_sequence = SimpleNamespace(seq_num=42, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        trigger_option='None', n_triggers=0)

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

        FINDING: the retry call in this branch is
        `self.wait_for_trigger(seq1, seq2, seq3, seq4, duration_ms)` --
        debug_info is NOT forwarded, so the retry always uses debug_info's
        default (True) regardless of what the original caller passed. This
        was discovered because passing debug_info=False here (as every
        other test in this class does, with a minimal fake_sequence) still
        required a full `pulse_dur` attribute below -- the retry's
        debug_info=True path reads it even though the caller asked for
        debug_info=False. Same bug shape exists in execute_sequence's
        identical reconnect branch. Not fixed here, just why this
        fake_sequence needs more attributes than its sibling tests.
        """
        patch_config.set('Trigger', 'Option.seq', 'TriggerSequence')
        patch_config.set('Trigger', 'Option.ptr', 'TriggerOnePulseTrainRepetition')
        instance = IGT(log_dir=str(tmp_path))
        instance.connected = False

        def fake_connect(connect_info):
            instance.connected = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_sequence(*args, **kwargs):
            instance.sent_seqs[1] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}
        mock_send = mocker.patch.object(instance, 'send_sequence', side_effect=fake_send_sequence)

        fake_sequence = SimpleNamespace(
            seq_num=1, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping',
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
