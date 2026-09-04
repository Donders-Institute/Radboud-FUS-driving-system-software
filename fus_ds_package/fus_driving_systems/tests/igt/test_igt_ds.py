# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.igt.igt_ds.IGT.

See tests/igt/conftest.py's module docstring for why these tests use the
real unifus native extension for enums/Pulse/sequenceDurationMs, only
patching unifus.FUSSystem (connect()'s sole hardware-touching seam) or the
specific instance (self.gen/self.fus/self.listener, via connected_instance)
downstream of a connection.

Phase 3 note: send_protocol()/wait_for_trigger()/execute_protocol() now take a
`protocols` argument -- a single TUSProtocol, or a list of TUSProtocol objects to
interleave -- rather than positional protocol1/protocol2/protocol3/protocol4. Only a real
fus_driving_systems.tus_protocol.TUSProtocol instance auto-wraps into a single-element list
(isinstance check); the SimpleNamespace stand-ins used throughout this file are not
TUSProtocol instances, so tests must pass them already wrapped in a list. Every protocol
(whether real or faked) must also carry `.slots` (non-empty) and `.driving_sys.available_ch`
matching the slots' combined element count -- send_protocol()'s new _assert_ready_to_send()
gate checks this before anything else.
"""
import math
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from fus_driving_systems.config import logging_config
from fus_driving_systems.exceptions import (FDSConfigError, FDSHardwareError, FDSInternalError,
                                            FDSSafetyError, FDSValidationError)
from fus_driving_systems.igt import transducer_xyz, unifus
from fus_driving_systems.igt.igt_ds import IGT


_UNSET = object()


def _slot(elements=1, ampl=_UNSET, serial='TRAN-A', **overrides):
    """A minimal stand-in for a TransducerSlot, for tests that only need enough shape to
    satisfy _assert_ready_to_send()/_define_pulse_group() without any real power/focus
    calculation. ampl defaults to [50.0] when not given -- pass ampl=None explicitly to
    exercise the "amplitude not set" case. serial defaults to 'TRAN-A' -- validate_protocol()'s
    "amplitude is None" error names the transducer it's about, so tests checking that need a
    distinguishable serial per slot. intensity_summary defaults to a fixed, serial-identifying
    string -- see TransducerSlot.intensity_summary(), used by _log_intensity_summary().
    oper_freq/dephasing_degree/focus_wrt_mid_bowl are minimal, fixed defaults -- see
    IGT._build_slot_fingerprints(), used by _assert_not_reconfigured_since_send(). volt defaults
    to None (no active calibration) -- see IGT._configure_voltage_feedback(), which then drops
    this slot from voltage feedback entirely rather than needing a real expected value here."""
    values = dict(ampl=[50.0] if ampl is _UNSET else ampl,
                  transducer=SimpleNamespace(elements=elements, serial=serial),
                  intensity_summary=lambda: f'{serial}: fake intensity summary',
                  oper_freq=500, dephasing_degree=None, focus_wrt_mid_bowl=50.0, volt=None)
    values.update(overrides)
    return SimpleNamespace(**values)


def _ready(*slots):
    """Returns the two kwargs (slots=..., driving_sys=...) every protocol needs to pass
    send_protocol()'s _assert_ready_to_send() gate -- available_ch set to match the given
    slots' combined element count exactly. max_buffers/serial are also needed now that
    buffer_num is validated against driving_sys (see _assert_valid_buffer_num()) rather than
    being a TUSProtocol attribute -- 2 is plenty for tests that use buffer_num 0 or 1."""
    total = sum(s.transducer.elements for s in slots)
    return {'slots': list(slots),
            'driving_sys': SimpleNamespace(available_ch=total, max_buffers=2,
                                           serial='FAKE-DS')}


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:

    def test_init_sets_default_attributes(self, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        assert instance.sent_protocols == {}
        assert instance.fus is None
        assert instance.listener is None
        assert instance.n_channels == 0
        assert instance.is_connected() is False

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
# is_protocol_sent() / register_sent_protocol()
# ---------------------------------------------------------------------------

class TestIsProtocolSent:
    """Note: IGT.is_protocol_sent(buffer_num) takes a required buffer_num arg,
    shadowing ControlDrivingSystem.is_protocol_sent() (no args) with an
    incompatible signature -- not a live bug (igt_ds.py always calls its
    own override with buffer_num; SonicConcepts calls the base no-arg version
    on its own instances), but worth knowing if this is ever called
    polymorphically without knowing the concrete driving-system type."""

    def test_returns_true_when_buffer_num_registered(self, igt_instance):
        igt_instance.sent_protocols[0] = {'pulse_train_seq': []}

        assert igt_instance.is_protocol_sent(0) is True

    def test_returns_false_when_buffer_num_not_registered(self, igt_instance):
        assert igt_instance.is_protocol_sent(0) is False


class TestRegisterSentProtocol:

    def test_stores_protocol_details_and_total_duration(self, igt_instance, mocker, patch_config):
        patch_config.set('Equipment.Manufacturer.IGT', 'Wait time before responsive [ms]', '50')
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=200.0)

        fake_protocols = [SimpleNamespace(buffer_num=0, slots=[_slot(serial='TRAN-A')])]
        igt_instance.register_sent_protocol(0, fake_protocols, pulse_train_seq=['pulse'],
                                            n_pulse_train_rep=3, pulse_train_delay=5.0,
                                            phases=[10.0, 20.0])

        stored = igt_instance.sent_protocols[0]
        assert stored['intensity_lines'] == ['  Buffer 0, slot 0: TRAN-A: fake intensity summary']
        assert stored['protocol_fingerprints'] == igt_instance._build_protocol_fingerprints(
            fake_protocols)
        assert stored['pulse_train_seq'] == ['pulse']
        assert stored['n_pulse_train_rep'] == 3
        assert stored['pulse_train_delay'] == 5.0
        assert stored['phases'] == [10.0, 20.0]
        assert stored['total_protocol_duration_ms'] == pytest.approx(250.0)  # 200 + 50

    def test_intensity_lines_are_a_frozen_snapshot_not_a_live_reference(self, igt_instance,
                                                                        mocker):
        """TUSProtocol/TransducerSlot are ordinary mutable objects -- if a caller reconfigures a
        slot after send_protocol() but before execute_protocol()/wait_for_trigger(), without
        resending, the driving system's buffer still holds whatever _define_pulse_group() baked
        in at send time (see _build_intensity_lines()'s own docstring). The confirmation log
        must therefore keep describing that original configuration, not whatever the live
        objects have since been mutated to -- proven here by mutating the slot's own
        intensity_summary() return value after registering, and confirming the stored lines
        don't follow it."""
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=200.0)
        mutable_slot = SimpleNamespace(intensity_summary=lambda: mutable_slot.current_summary,
                                       transducer=SimpleNamespace(serial='TRAN-A'),
                                       oper_freq=500, dephasing_degree=None,
                                       focus_wrt_mid_bowl=40.0, ampl=[30.0])
        mutable_slot.current_summary = 'TRAN-A: 40.00 mm, 0.30 MPa'
        fake_protocols = [SimpleNamespace(buffer_num=0, slots=[mutable_slot])]

        igt_instance.register_sent_protocol(0, fake_protocols, pulse_train_seq=['pulse'],
                                            n_pulse_train_rep=1, pulse_train_delay=0.0)

        # Reconfigured after sending, without resending -- e.g. slot.configure(...) called again.
        mutable_slot.current_summary = 'TRAN-A: 60.00 mm, 0.80 MPa'

        assert igt_instance.sent_protocols[0]['intensity_lines'] == [
            '  Buffer 0, slot 0: TRAN-A: 40.00 mm, 0.30 MPa']


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

    def test_connect_names_native_log_after_the_session_filename_by_default(
            self, mocker, mock_fus_system, tmp_path):
        """When log_name isn't given, the native IGT log is named consistently with the main
        FDS log by default (get_session_log_filename()) rather than a generic,
        session-independent config default -- callers no longer need to pass the same filename
        twice."""
        mocker.patch("fus_driving_systems.igt.igt_ds.get_session_log_filename",
                     return_value='standalone_plain')
        set_log_path_mock = mocker.patch("fus_driving_systems.igt.igt_ds.unifus.setLogPath")
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert set_log_path_mock.call_args[0][1] == 'log_igt_standalone_plain'

    def test_connect_falls_back_to_config_default_when_no_session_filename_is_tracked(
            self, mocker, mock_fus_system, tmp_path):
        """No initialize_logger() call happened in this process (e.g. a host application using
        sync_logger() instead) -- get_session_log_filename() returns None, so this falls back to
        the config-driven default rather than crashing on a None + str concatenation."""
        mocker.patch("fus_driving_systems.igt.igt_ds.get_session_log_filename",
                     return_value=None)
        set_log_path_mock = mocker.patch("fus_driving_systems.igt.igt_ds.unifus.setLogPath")
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        instance = IGT(log_dir=str(tmp_path))

        instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert set_log_path_mock.call_args[0][1] == 'log_igt_standalone_igt'

    def test_connect_success_sets_connected_and_channel_count(self, mocker, mock_fus_system,
                                                              tmp_path):
        mock_fus_system.isConnected.return_value = True
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen

        instance = IGT(log_dir=str(tmp_path))
        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        assert instance.is_connected() is True
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

        with pytest.raises(FDSHardwareError):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        # once for the attempt==0 defensive disconnect, once for the actual retry
        assert sleep_mock.call_args_list.count(mocker.call(5.0)) == 2

    def test_connect_raises_immediately_when_fus_system_construction_fails(self, mocker, tmp_path):
        mocker.patch("fus_driving_systems.igt.igt_ds.unifus.FUSSystem",
                     side_effect=RuntimeError("boom"))
        instance = IGT(log_dir=str(tmp_path))

        with pytest.raises(FDSHardwareError):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

    def test_connect_retries_then_raises_when_never_reports_connected(
            self, mocker, mock_fus_system, tmp_path, patch_config):
        patch_config.set('General', 'Maximum reconnection attempts', '1')
        mock_fus_system.isConnected.return_value = False
        instance = IGT(log_dir=str(tmp_path))
        mocker.patch.object(instance, 'disconnect')  # not under test here

        with pytest.raises(FDSHardwareError):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert instance.disconnect.call_count == 1  # exactly one retry attempted

    def test_connect_surfaces_config_error_from_a_retry_attempt_as_such(
            self, mocker, mock_fus_system, tmp_path, patch_config):
        """Regression test: the recursive retry call used to sit inside the same try/except
        that wraps the post-connection-check block -- a retry attempt whose own loadConfig()
        fails with FDSConfigError would fall through that block's broad except and get
        mislabeled as FDSHardwareError instead. loadConfig() succeeds on the first attempt (so
        the retry is actually reached) and fails on the second."""
        patch_config.set('General', 'Maximum reconnection attempts', '1')
        mock_fus_system.isConnected.return_value = False
        mock_fus_system.loadConfig.side_effect = [None, RuntimeError('config boom')]
        instance = IGT(log_dir=str(tmp_path))
        mocker.patch.object(instance, 'disconnect')  # not under test here

        with pytest.raises(FDSConfigError):
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

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

        # Not also asserting is_connected() here: isConnected()'s side_effect list is exhausted
        # by the two attempts above (fails once, then succeeds), and calling it a third time
        # would raise -- result is True already proves the retry-then-succeed behavior.
        assert result is True

    def test_connect_skips_reconnection_when_already_connected(self, mocker, mock_fus_system,
                                                               tmp_path):
        """GitHub issues #103/#126: calling connect() while already connected used to always
        tear down and recreate the native unifus.FUSSystem() and re-register a listener on an
        already live connection, a plausible source of instability. It should now be a no-op
        that just confirms the existing connection."""
        instance = IGT(log_dir=str(tmp_path))
        instance.fus = mock_fus_system
        mock_fus_system.isConnected.return_value = True

        result = instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        assert result is True
        mock_fus_system.loadConfig.assert_not_called()
        mock_fus_system.registerListener.assert_not_called()
        mock_fus_system.connect.assert_not_called()

    def test_connect_does_not_skip_when_fus_exists_but_reports_disconnected(
            self, mocker, mock_fus_system, tmp_path):
        """GitHub issue #79: is_connected() queries the live SDK, not a cached flag -- a fus
        object left over from a previous, now-broken connection (e.g. a cable break) must not
        cause connect() to take the 'already connected, skip' shortcut just because fus exists,
        unlike test_connect_skips_reconnection_when_already_connected above."""
        instance = IGT(log_dir=str(tmp_path))
        instance.fus = mock_fus_system
        mock_fus_system.isConnected.return_value = False
        fake_gen = mocker.Mock()
        fake_gen.getParam.return_value = 8
        mock_fus_system.gen.return_value = fake_gen
        mocker.patch.object(instance, 'disconnect')  # not under test here

        with pytest.raises(FDSHardwareError):
            # isConnected() is stubbed to always return False, so every reconnection attempt
            # fails too -- the point of this test is only that it actually *attempts* to
            # reconnect (loadConfig/connect get called) rather than skipping via the stale flag.
            instance.connect('igt/config/gen_test.json', log_dir=str(tmp_path))

        mock_fus_system.loadConfig.assert_called()
        mock_fus_system.connect.assert_called()


class TestIsConnected:

    def test_returns_false_when_fus_is_none(self, igt_instance):
        """With no fus object, there is nothing to be connected to."""
        assert igt_instance.fus is None

        assert igt_instance.is_connected() is False

    def test_returns_live_fus_status_when_fus_exists(self, mocker, igt_instance):
        """GitHub issue #79: is_connected() queries the live SDK directly -- IGT never keeps a
        separate cached flag in sync with it at all."""
        igt_instance.fus = mocker.Mock()
        igt_instance.fus.isConnected.return_value = False

        assert igt_instance.is_connected() is False

        igt_instance.fus.isConnected.return_value = True

        assert igt_instance.is_connected() is True


# ---------------------------------------------------------------------------
# validate_protocol
# ---------------------------------------------------------------------------

def _valid_protocol(**overrides):
    values = dict(
        pulse_dur=1.0,
        pulse_rep_int=2.0,
        pulse_train_dur=20.0,
        pulse_train_rep_int=20.0,
        pulse_train_rep_dur=20.0,
        pulse_ramp_dur=0.0,
        pulse_ramp_shape='Rectangular - no ramping',
        slots=[_slot(ampl=[50.0])],
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class TestValidateProtocol:

    def test_valid_protocol_has_no_errors(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')

        errors = igt_instance.validate_protocol(_valid_protocol())

        assert errors == []

    def test_pulse_duration_below_minimum_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Min. pulse duration [ms]', '0.5')

        errors = igt_instance.validate_protocol(_valid_protocol(pulse_dur=0.1,
                                                                pulse_rep_int=1.0))

        assert any('Pulse duration' in e for e in errors)

    def test_pulse_rep_int_below_minimum_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Min. pulse rep. interval [ms]', '1.0')

        errors = igt_instance.validate_protocol(_valid_protocol(pulse_dur=0.05,
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

        errors = igt_instance.validate_protocol(_valid_protocol(
            pulse_dur=1.0, pulse_rep_int=1.0, pulse_ramp_dur=0.6, pulse_ramp_shape='Linear'))

        assert any('ramping' in e for e in errors)

    def test_amplitude_none_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')

        errors = igt_instance.validate_protocol(_valid_protocol(slots=[_slot(ampl=None)]))

        assert any('Amplitude is None' in e for e in errors)

    def test_amplitude_none_is_flagged_for_any_slot(self, igt_instance, patch_config):
        """Every slot is checked, not just the first -- a multi-transducer protocol with a
        problem on its second slot must not go unnoticed, and the message must identify which
        slot (index and transducer serial) so a multi-transducer protocol's error is actionable
        rather than just "some slot, somewhere". The index is 0-based (matching protocol.slots'
        own indexing), so the message spells that out explicitly -- otherwise "slot 1" could
        read as "the first slot" to someone not thinking in 0-based terms, when it actually means
        the second one."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')

        errors = igt_instance.validate_protocol(_valid_protocol(
            slots=[_slot(serial='TRAN-A', ampl=[50.0]), _slot(serial='TRAN-B', ampl=None)]))

        assert any('slot 1 (counting from 0' in e and 'TRAN-B' in e for e in errors)
        assert not any('TRAN-A' in e for e in errors)

    def test_raises_when_min_pulse_duration_config_key_missing(self, igt_instance, patch_config):
        """raise_on_missing=True: a typo'd or deleted hardware-limit key must never silently
        fall back to the hardcoded placeholder instead of the real configured limit -- the
        other hardware-limit keys in this method (Min. pulse rep. interval, Min. time in
        between ramping, Max. pulses in pulse train) were converted identically."""
        from fus_driving_systems.config.config import config_info

        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Min. pulse duration [ms]', '0.5')
        del config_info['Equipment.Manufacturer.IGT']['Min. pulse duration [ms]']

        with pytest.raises(FDSConfigError):
            igt_instance.validate_protocol(_valid_protocol())

    def test_too_many_pulses_in_pulse_train_is_flagged(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. pulses in pulse train', '4')

        errors = igt_instance.validate_protocol(_valid_protocol(
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
        protocol = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(protocol, pulse_ramp_temp_res=2.0)

        assert ampl_ramp == pytest.approx(np.linspace(0, 1, 5))

    def test_tukey_ramp_starts_at_zero_and_ends_at_one(self, igt_instance, patch_config):
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        protocol = SimpleNamespace(pulse_ramp_shape='Tukey', pulse_ramp_dur=10.0)

        ampl_ramp = igt_instance._get_ramping_amplitude(protocol, pulse_ramp_temp_res=2.0)

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
        protocol = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        connected_instance._apply_ramping(protocol)

        connected_instance.gen.setPulseModulation.assert_called_once()
        ramp_up, up_res, ramp_down, down_res = \
            connected_instance.gen.setPulseModulation.call_args[0]
        assert up_res == pytest.approx(2.0)
        assert down_res == pytest.approx(2.0)
        assert ramp_down == [0, 25, 50, 75, 100]  # linspace(0,1,5) * 100, int()
        assert ramp_up == list(reversed(ramp_down))  # "ramp up descends" per the source comment

    def test_raises_when_max_ramping_steps_config_key_missing(self, connected_instance,
                                                              patch_config):
        """raise_on_missing=True: a typo'd or deleted hardware-limit key must never silently
        fall back to the hardcoded placeholder instead of the real configured limit -- the
        sibling 'Min. temporal ramping resolution [ms]' key was converted identically."""
        from fus_driving_systems.config.config import config_info

        patch_config.set('Equipment.Manufacturer.IGT', 'Min. temporal ramping resolution [ms]',
                         '2')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. amount of ramping steps', '1023')
        del config_info['Equipment.Manufacturer.IGT']['Max. amount of ramping steps']
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        protocol = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        with pytest.raises(FDSConfigError):
            connected_instance._apply_ramping(protocol)

    def test_clamps_temporal_resolution_when_step_count_exceeds_max(self, connected_instance,
                                                                    patch_config):
        patch_config.set('Equipment.Manufacturer.IGT',
                         'Min. temporal ramping resolution [ms]', '0.1')
        patch_config.set('Equipment.Manufacturer.IGT', 'Max. amount of ramping steps', '10')
        patch_config.set('Ramp', 'Option.lin', 'Linear')
        patch_config.set('Ramp', 'Option.tuk', 'Tukey')
        # ramp_n_steps = pulse_ramp_dur / min_res = 10 / 0.1 = 100 > max_steps (10)
        # -> min_ramp_temp_res gets recomputed as pulse_ramp_dur / max_steps = 1.0
        protocol = SimpleNamespace(pulse_ramp_shape='Linear', pulse_ramp_dur=10.0)

        connected_instance._apply_ramping(protocol)

        _, up_res, _, down_res = connected_instance.gen.setPulseModulation.call_args[0]
        assert up_res == pytest.approx(1.0)
        assert down_res == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _define_pulse_train
# ---------------------------------------------------------------------------

class TestDefinePulseTrain:

    def test_builds_pulse_train_list_and_computes_delay(self, igt_instance):
        pulse = object()
        protocol = SimpleNamespace(pulse_train_dur=10.0, pulse_rep_int=2.0,
                                   pulse_train_rep_int=15.0)

        pulse_train_seq, pulse_train_delay = igt_instance._define_pulse_train(protocol, pulse)

        assert pulse_train_seq == [pulse] * 5
        assert pulse_train_delay == pytest.approx(5.0)

    def test_floors_partial_pulses(self, igt_instance):
        pulse = object()
        protocol = SimpleNamespace(pulse_train_dur=9.0, pulse_rep_int=2.0,
                                   pulse_train_rep_int=9.0)

        pulse_train_seq, pulse_train_delay = igt_instance._define_pulse_train(protocol, pulse)

        assert len(pulse_train_seq) == math.floor(9.0 / 2.0)  # 4, not 4.5
        assert pulse_train_delay == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _define_pulse_group (real unifus.Pulse, no unifus mocking)
# ---------------------------------------------------------------------------

class TestDefinePulseGroupSingleSlot:
    """N=1 slot goes through the identical fully-expanded-per-element construction as N>=2 --
    see TestDefinePulseGroupMultiSlot."""

    def test_uses_override_phases_when_dephasing_matches_element_count(self, connected_instance):
        connected_instance.n_channels = 2
        fake_transducer = SimpleNamespace(elements=2, steer_info='dummy.ini')
        slot = SimpleNamespace(oper_freq=250, ampl=[50, 60], dephasing_degree=[10.0, 20.0],
                               transducer=fake_transducer, focus_wrt_mid_bowl=50)
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot])

        pulse, phases = connected_instance._define_pulse_group(protocol)

        assert phases == [10.0, 20.0]
        assert pulse.frequencyCount() == 2
        assert pulse.frequency(0) == 250_000
        assert pulse.frequency(1) == 250_000
        assert pulse.amplitude(0) == 50
        assert pulse.amplitude(1) == 60
        assert pulse.phase(0) == pytest.approx(10.0)
        assert pulse.phase(1) == pytest.approx(20.0)
        assert pulse.duration() == pytest.approx(1.0)
        assert pulse.delay() == pytest.approx(1.0)  # round(2.0 - 1.0, 1)

    def test_expands_length_1_amplitude_to_every_channel_rather_than_leaving_it_uniform(
            self, connected_instance):
        """A single slot's length-1 ampl is expanded to its transducer's own element count,
        same as any other slot regardless of how many are in the protocol."""
        connected_instance.n_channels = 10
        fake_transducer = SimpleNamespace(elements=10, steer_info='dummy.ini')
        slot = SimpleNamespace(oper_freq=250, ampl=[50], dephasing_degree=[0.0] * 10,
                               transducer=fake_transducer, focus_wrt_mid_bowl=50)
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot])

        pulse, _ = connected_instance._define_pulse_group(protocol)

        assert pulse.amplitudeCount() == 10
        assert pulse.frequencyCount() == 10
        for i in range(10):
            assert pulse.amplitude(i) == 50
            assert pulse.frequency(i) == 250_000

    def test_raises_when_amplitude_is_none(self, connected_instance):
        connected_instance.n_channels = 2
        slot = SimpleNamespace(oper_freq=250, ampl=None, dephasing_degree=None,
                               transducer=SimpleNamespace(elements=2))
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot])

        with pytest.raises(FDSInternalError):
            connected_instance._define_pulse_group(protocol)

    def test_wraps_native_pulse_construction_failure_as_hardware_error(
            self, mocker, connected_instance):
        """Regression test: this method used to have no exception handling at all around its
        unifus.Pulse construction/setup -- a native SDK failure here would previously propagate
        raw instead of surfacing as a catchable FDSHardwareError, unlike every other unifus
        touchpoint in this class."""
        connected_instance.n_channels = 2
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.Pulse',
                     side_effect=RuntimeError('native pulse construction failed'))
        slot = SimpleNamespace(oper_freq=250, ampl=[50, 60], dephasing_degree=[10.0, 20.0],
                               transducer=SimpleNamespace(elements=2))
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot])

        with pytest.raises(FDSHardwareError):
            connected_instance._define_pulse_group(protocol)

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
        )
        slot = SimpleNamespace(oper_freq=300, ampl=[50] * 10, dephasing_degree=None,
                               transducer=fake_transducer, focus_wrt_mid_bowl=75,
                               focus_offset_x=0.0, focus_offset_y=0.0)
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot])

        pulse, phases = connected_instance._define_pulse_group(protocol)

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
        TestDefinePulseGroupSingleSlot already exercises this same path end-to-end via
        _define_pulse_group -- this test isolates _set_phases itself, calling it
        directly the same way TestSetPhasesExcelBranch does for the other
        branch, with a real unifus.Pulse built the same way _define_pulse_group
        builds one.)
        """
        connected_instance.n_channels = 10
        pulse = unifus.Pulse(connected_instance.n_channels, 1, 1)
        pulse.setFrequencies([300_000])

        phases = connected_instance._set_phases(
            pulse, focus_wrt_mid_bowl=75,
            steer_info='igt/config/imasonic_transducers/transducer_15287_10_300kHz.ini',
            dephasing_degree=None)

        assert len(phases) == 10

    def test_ini_branch_reads_focal_length_from_the_loaded_ini_file(
            self, mocker, connected_instance):
        """Regression proof for the natural-focus/focalLength consolidation: _set_phases() no
        longer takes a natural_foc parameter -- aim_wrt_natural_focus must come from
        trans.focalLength, populated by Transducer.load() from the .ini file itself. Proven by
        mocking load() to set two different focalLength values (rather than asserting one exact
        phase, which would just as easily pass if the value were silently ignored/hardcoded) and
        confirming the computed phases differ accordingly."""
        connected_instance.n_channels = 1

        def make_fake_load(focal_length):
            def fake_load(self, filename):
                self.focalLength = focal_length
                self.elements = [(0.0, 0.0, 0.05)]
                return True
            return fake_load

        pulse = unifus.Pulse(1, 1, 1)
        pulse.setFrequencies([300_000])

        mocker.patch.object(transducer_xyz.Transducer, 'load', make_fake_load(75.0))
        phases_a = connected_instance._set_phases(
            pulse, focus_wrt_mid_bowl=40, steer_info='fake.ini', dephasing_degree=None)

        mocker.patch.object(transducer_xyz.Transducer, 'load', make_fake_load(100.0))
        phases_b = connected_instance._set_phases(
            pulse, focus_wrt_mid_bowl=40, steer_info='fake.ini', dephasing_degree=None)

        assert phases_a != phases_b


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

        phases = connected_instance._set_phases(mocker.Mock(), focus_wrt_mid_bowl=50.0,
                                                steer_info='some_table.xlsx',
                                                dephasing_degree=None)

        assert phases == [10.0, 20.0]

    def test_excel_branch_raises_when_file_does_not_exist(self, mocker, connected_instance):
        connected_instance.n_channels = 2
        mocker.patch('fus_driving_systems.igt.igt_ds.os.path.exists', return_value=False)

        with pytest.raises(FDSConfigError):
            connected_instance._set_phases(mocker.Mock(), focus_wrt_mid_bowl=50.0,
                                           steer_info='missing.xlsx', dephasing_degree=None)

    def test_raises_when_steer_info_is_neither_ini_nor_xlsx(self, mocker, connected_instance):
        """DUMMY/CITRUS transducers configure an empty 'Steer information'
        string (they're never used with an IGT driving system either), so
        an unrecognized extension should be rejected rather than silently
        misbehaving."""
        connected_instance.n_channels = 2

        with pytest.raises(FDSConfigError):
            connected_instance._set_phases(mocker.Mock(), focus_wrt_mid_bowl=50.0, steer_info='',
                                           dephasing_degree=None)

    def test_raises_when_more_than_one_dephasing_entry_given(self, mocker, connected_instance):
        """Checked up front in _set_phases(), before either steer path does any real work (see
        its own comment there) -- no excel file needs mocking here, since one is never read."""
        connected_instance.n_channels = 2

        with pytest.raises(FDSValidationError):
            connected_instance._set_phases(mocker.Mock(), focus_wrt_mid_bowl=50.0,
                                           steer_info='some_table.xlsx',
                                           dephasing_degree=[10.0, 20.0])


class TestDefinePulseGroupMultiSlot:
    """N=2 slots: each slot's amplitude/frequency array must be fully expanded to its own
    element count before concatenating -- the same construction TestDefinePulseGroupSingleSlot's
    N=1 case above now also goes through."""

    def test_combines_phases_frequencies_and_amplitudes_from_both_slots(self, connected_instance):
        connected_instance.n_channels = 4
        tran1 = SimpleNamespace(elements=2)
        tran2 = SimpleNamespace(elements=2)
        slot1 = SimpleNamespace(oper_freq=250, ampl=[50], dephasing_degree=[1.0, 2.0],
                                transducer=tran1, focus_wrt_mid_bowl=50)
        slot2 = SimpleNamespace(oper_freq=300, ampl=[60, 70], dephasing_degree=[3.0, 4.0],
                                transducer=tran2, focus_wrt_mid_bowl=50)
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=[slot1, slot2])

        pulse, phases = connected_instance._define_pulse_group(protocol)

        assert phases == [1.0, 2.0, 3.0, 4.0]
        assert [pulse.amplitude(i) for i in range(4)] == [50, 50, 60, 70]
        assert pulse.frequency(0) == 250_000
        assert pulse.frequency(2) == 300_000
        # Fully expanded per element, same construction TestDefinePulseGroupSingleSlot's N=1
        # case now also goes through.
        assert pulse.frequencyCount() == 4
        assert pulse.amplitudeCount() == 4

    def test_three_slots_concatenates_all_three_without_any_hardcoded_pair_assumption(
            self, connected_instance):
        """N is never hardcoded to 2 -- a 3rd slot falls out of the same loop for free."""
        connected_instance.n_channels = 3
        slots = [
            SimpleNamespace(oper_freq=100, ampl=[10], dephasing_degree=[5.0],
                            transducer=SimpleNamespace(elements=1), focus_wrt_mid_bowl=50),
            SimpleNamespace(oper_freq=200, ampl=[20], dephasing_degree=[7.0],
                            transducer=SimpleNamespace(elements=1), focus_wrt_mid_bowl=50),
            SimpleNamespace(oper_freq=300, ampl=[30], dephasing_degree=[9.0],
                            transducer=SimpleNamespace(elements=1), focus_wrt_mid_bowl=50),
        ]
        protocol = SimpleNamespace(pulse_dur=1.0, pulse_rep_int=2.0, slots=slots)

        pulse, phases = connected_instance._define_pulse_group(protocol)

        assert [pulse.amplitude(i) for i in range(3)] == [10, 20, 30]
        assert [pulse.frequency(i) for i in range(3)] == [100_000, 200_000, 300_000]
        assert phases == [5.0, 7.0, 9.0]


# ---------------------------------------------------------------------------
# send_protocol
# ---------------------------------------------------------------------------

class TestSendProtocol:

    def test_defines_pulse_registers_and_sends_when_connected(self, mocker, connected_instance,
                                                              patch_config):
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            return_value=(fake_pulse, [1.0, 2.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse, fake_pulse], 5.0))
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_protocol = SimpleNamespace(
            buffer_num=0, pulse_train_rep_dur=20, pulse_train_rep_int=10,
            pulse_ramp_shape='Rectangular - no ramping', **_ready(_slot()))

        connected_instance.send_protocol([fake_protocol])

        connected_instance.gen.sendSequence.assert_called_once_with(0, [fake_pulse, fake_pulse])
        assert connected_instance.is_protocol_sent(0) is True

    def test_wraps_send_sequence_failure_as_hardware_error(
            self, mocker, connected_instance, patch_config):
        """Regression test: everything from ramping through gen.sendSequence()/
        register_sent_protocol() used to have no exception handling at all -- a native SDK
        failure here would previously propagate raw instead of surfacing as a catchable
        FDSHardwareError."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            return_value=(fake_pulse, [1.0, 2.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse, fake_pulse], 5.0))
        connected_instance.gen.sendSequence.side_effect = RuntimeError('native send failed')

        fake_protocol = SimpleNamespace(
            buffer_num=0, pulse_train_rep_dur=20, pulse_train_rep_int=10,
            pulse_ramp_shape='Rectangular - no ramping', **_ready(_slot()))

        with pytest.raises(FDSHardwareError):
            connected_instance.send_protocol([fake_protocol])

    def test_accepts_a_single_protocol_without_a_list(self, mocker, connected_instance,
                                                      patch_config):
        """A bare TUSProtocol (checked via isinstance, so this only kicks in for the real class --
        SimpleNamespace stand-ins elsewhere in this file always need an explicit list) is
        auto-wrapped into a single-element list -- convenience for the overwhelmingly common
        single-protocol case. Built via __new__ (bypassing __init__'s config-driven defaults),
        same pattern as test_tus_protocol_class.py's _bare_protocol()."""
        from fus_driving_systems.tus_protocol import TUSProtocol

        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            return_value=(fake_pulse, [1.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse], 5.0))
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        real_protocol = TUSProtocol.__new__(TUSProtocol)
        # buffer_num/trigger_option/n_triggers are no longer TUSProtocol attributes -- buffer_num
        # is passed straight to send_protocol() below instead (see igt_ds.py's docstring for why).
        real_protocol._timing_param = {
            'pulse_dur': 1.0,
            'pulse_rep_int': 2.0,
            'pulse_ramp_shape': 'Rectangular - no ramping',
            'pulse_ramp_dur': 0.0,
            'pulse_train_dur': 20.0,
            'pulse_train_rep_int': 10,
            'pulse_train_rep_dur': 20,
        }
        ready = _ready(_slot())
        real_protocol._slots = ready['slots']
        real_protocol._driving_sys = ready['driving_sys']

        connected_instance.send_protocol(real_protocol, buffer_num=1)  # NOT wrapped in a list

        connected_instance.gen.sendSequence.assert_called_once_with(1, [fake_pulse])

    def test_raises_when_no_slots_configured(self, connected_instance):
        """A protocol that never had add_slot() called on it must be rejected with a clear
        message, not fail confusingly deep inside pulse construction."""
        fake_protocol = SimpleNamespace(
            buffer_num=0, slots=[],
            driving_sys=SimpleNamespace(available_ch=1, max_buffers=2))

        with pytest.raises(FDSValidationError, match='add_slot'):
            connected_instance.send_protocol([fake_protocol])

    def test_raises_when_slot_elements_do_not_match_available_channels(self, connected_instance):
        fake_protocol = SimpleNamespace(
            buffer_num=0, slots=[_slot(elements=2)],
            driving_sys=SimpleNamespace(available_ch=10, max_buffers=2))

        with pytest.raises(FDSValidationError):
            connected_instance.send_protocol([fake_protocol])

    def test_raises_when_validation_produces_errors(self, mocker, connected_instance):
        mocker.patch.object(connected_instance, 'validate_protocol',
                            return_value=['something is wrong'])
        fake_protocol = SimpleNamespace(buffer_num=0, **_ready(_slot()))

        with pytest.raises(FDSValidationError):
            connected_instance.send_protocol([fake_protocol])

    def test_reconnects_and_retries_when_not_connected(self, mocker, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        def fake_connect(connect_info):
            instance.fus = mocker.Mock()
            instance.fus.isConnected.return_value = True
            instance.gen = mocker.Mock()
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)
        mocker.patch.object(instance, 'validate_protocol', return_value=[])
        mocker.patch.object(instance, '_define_pulse_group', return_value=(mocker.Mock(), [1.0]))
        mocker.patch.object(instance, '_define_pulse_train',
                            return_value=([mocker.Mock()], 5.0))
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_protocol = SimpleNamespace(
            buffer_num=0,
            driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json', available_ch=1,
                                        max_buffers=2),
            slots=[_slot()], pulse_train_rep_dur=20, pulse_train_rep_int=10,
            pulse_ramp_shape='Rectangular - no ramping')

        instance.send_protocol([fake_protocol])

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        assert instance.is_protocol_sent(0) is True

    def test_interleaves_two_protocols_with_combined_pulse_train(self, mocker, connected_instance,
                                                                 patch_config):
        """More than one protocol means they're interleaved: n_pulse_train_rep is computed from
        total_alternating_duration_ms and the sum of both protocols' pulse_rep_int -- the time
        slot each
        protocol's own single pulse (pulse_dur active, then its own trailing delay) occupies in
        one round of the alternating group, not pulse_train_dur (which would describe a
        repeated train this pulse never fires here) or either one's own pulse_train_rep_dur/int.
        pulse_train_dur is deliberately set to something very different from pulse_rep_int on
        both protocols below, so this test would fail loudly if the wrong one were summed
        instead. _define_pulse_group is called once per protocol."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        fake_pulse1, fake_pulse2 = mocker.Mock(), mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            side_effect=[(fake_pulse1, [1.0]), (fake_pulse2, [2.0])])
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        # send_protocol() requires every interleaved protocol to target the same buffer (see
        # test_exits_when_interleaved_protocols_target_different_buffers below) -- both use
        # buffer_num=0 here, matching this file's usual convention of using 0 unless a test is
        # specifically about buffer selection.
        protocol1 = SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))
        protocol2 = SimpleNamespace(buffer_num=0, pulse_rep_int=15, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))

        connected_instance.send_protocol([protocol1, protocol2], total_alternating_duration_ms=100)

        # n_pulse_train_rep = floor(total_alternating_duration_ms / (protocol1.pulse_rep_int +
        #                                                            protocol2.pulse_rep_int))
        #                    = floor(100/25) = 4
        connected_instance.gen.sendSequence.assert_called_once_with(0, [fake_pulse1, fake_pulse2])
        stored = connected_instance.sent_protocols[0]
        assert stored['n_pulse_train_rep'] == 4
        assert stored['pulse_train_delay'] == 0
        assert stored['phases'] == [[1.0], [2.0]]

    def test_interleaves_three_protocols_without_any_hardcoded_pair_assumption(
            self, mocker, connected_instance, patch_config):
        """N is never hardcoded to 2 for interleaving either -- a 3rd protocol falls out of the
        same loop for free."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        pulses = [mocker.Mock(), mocker.Mock(), mocker.Mock()]
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            side_effect=[(p, [float(i)]) for i, p in enumerate(pulses)])
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        # Every interleaved protocol must target the same buffer -- see the two-protocol test
        # above.
        protocols = [
            SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                            pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                            **_ready(_slot())),
            SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                            pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                            **_ready(_slot())),
            SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                            pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                            **_ready(_slot())),
        ]

        connected_instance.send_protocol(protocols, total_alternating_duration_ms=90)

        connected_instance.gen.sendSequence.assert_called_once_with(0, pulses)
        # n_pulse_train_rep = floor(90 / (10+10+10)) = 3
        assert connected_instance.sent_protocols[0]['n_pulse_train_rep'] == 3

    def test_raises_when_interleaved_protocols_have_different_ramping(
            self, mocker, connected_instance, patch_config):
        """Only protocol0's pulse_ramp_shape/pulse_ramp_dur are ever actually applied to the
        generator once interleaving is under way (see this method's own docstring), but a caller
        giving different ramp settings across the group almost certainly expected every
        protocol's own ramping to take effect -- reject it explicitly, mirroring the buffer_num
        mismatch check above."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        protocol1 = SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))
        protocol2 = SimpleNamespace(buffer_num=0, pulse_rep_int=15, pulse_train_dur=999,
                                    pulse_ramp_shape='Tukey', pulse_ramp_dur=5,
                                    **_ready(_slot()))

        with pytest.raises(FDSValidationError):
            connected_instance.send_protocol([protocol1, protocol2],
                                             total_alternating_duration_ms=100)

    def test_raises_when_total_alternating_duration_ms_omitted_for_interleaved_protocols(
            self, mocker, connected_instance, patch_config):
        """Unlike a single protocol (which gets its own repetition count from its own
        pulse_train_rep_dur/pulse_train_rep_int), the interleaved group as a whole has no
        fallback for how long to keep alternating -- omitting it (leaving the default None) must
        not silently compute 0 repetitions."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        protocol1 = SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))
        protocol2 = SimpleNamespace(buffer_num=0, pulse_rep_int=15, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))

        with pytest.raises(FDSValidationError):
            connected_instance.send_protocol([protocol1, protocol2])

    def test_raises_when_total_alternating_duration_ms_is_negative_for_interleaved_protocols(
            self, mocker, connected_instance, patch_config):
        """A negative value is just as meaningless as omitting it (leaving None) or passing 0 --
        none of them describe a real span of time to keep alternating for -- so it must be
        rejected the same way, not silently accepted because it happens to be truthy."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        protocol1 = SimpleNamespace(buffer_num=0, pulse_rep_int=10, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))
        protocol2 = SimpleNamespace(buffer_num=0, pulse_rep_int=15, pulse_train_dur=999,
                                    pulse_ramp_shape='Rectangular - no ramping', pulse_ramp_dur=0,
                                    **_ready(_slot()))

        with pytest.raises(FDSValidationError):
            connected_instance.send_protocol([protocol1, protocol2],
                                             total_alternating_duration_ms=-100)

    def test_applies_ramping_when_ramp_shape_is_not_rectangular(self, mocker, connected_instance,
                                                                patch_config):
        """Only the rectangular/no-ramping branch was exercised elsewhere
        (via gen.setPulseModulation/setPulseRamp); this confirms
        send_protocol actually routes to _apply_ramping (already tested in
        isolation above) for any other ramp shape."""
        patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
        mocker.patch.object(connected_instance, 'validate_protocol', return_value=[])
        fake_pulse = mocker.Mock()
        mocker.patch.object(connected_instance, '_define_pulse_group',
                            return_value=(fake_pulse, [1.0]))
        mocker.patch.object(connected_instance, '_define_pulse_train',
                            return_value=([fake_pulse], 5.0))
        mock_apply_ramping = mocker.patch.object(connected_instance, '_apply_ramping')
        mocker.patch('fus_driving_systems.igt.igt_ds.unifus.sequenceDurationMs',
                     return_value=100.0)

        fake_protocol = SimpleNamespace(buffer_num=0, pulse_train_rep_dur=20,
                                        pulse_train_rep_int=10, pulse_ramp_shape='Linear',
                                        **_ready(_slot()))

        connected_instance.send_protocol([fake_protocol])

        mock_apply_ramping.assert_called_once_with(fake_protocol)
        connected_instance.gen.setPulseModulation.assert_not_called()


# ---------------------------------------------------------------------------
# execute_protocol
# ---------------------------------------------------------------------------

class TestExecuteProtocol:

    def test_raises_when_total_alternating_duration_ms_omitted_for_interleaved_protocols(
            self, connected_instance):
        """Unlike a single protocol (which gets its own repetition count from its own
        pulse_train_rep_dur/pulse_train_rep_int), the interleaved group as a whole has no
        fallback for how long to keep alternating -- omitting it (leaving the default None) must
        not silently proceed."""
        fake_protocol1 = SimpleNamespace(buffer_num=0)
        fake_protocol2 = SimpleNamespace(buffer_num=0)

        with pytest.raises(FDSValidationError):
            connected_instance.execute_protocol([fake_protocol1, fake_protocol2])

    def test_starts_protocol_and_waits_when_already_sent(self, mocker, connected_instance):
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        connected_instance.gen.prepareSequence.assert_called_once_with(0, 2, 5.0, mocker.ANY)
        connected_instance.gen.startSequence.assert_called_once()
        connected_instance.listener.wait_protocol.assert_called_once_with(0.5)

    def test_logs_the_actual_configured_max_pressure_not_a_stale_default(
            self, connected_instance, caplog, patch_config):
        """The pre-execution debug log and _enforce_max_pressure() must read the exact same
        config value via get_max_pressure() -- they used to read the same key with two
        different fallback defaults ('Not found' here vs. 1.4 in transducer_slot.py), which
        could silently disagree if the config key were ever missing."""
        patch_config.set('Power', 'Maximum pressure allowed in free water [MPa]', '0.75')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        with caplog.at_level('DEBUG'):
            connected_instance.execute_protocol([fake_protocol])

        assert 'Maximum allowed pressure is: 0.75 MPa' in caplog.text

    def test_raises_when_wait_protocol_times_out_without_a_result(self, connected_instance):
        """GitHub #78: wait_protocol() returns False specifically on timeout (see its own
        docstring) -- distinct from exec_error_code, which is only ever set once
        onSequenceResult() actually fires. Without checking this return value, the method would
        fall straight through to logging "executed successfully" on a protocol that never
        actually fired."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])
        connected_instance.listener.wait_protocol.return_value = False
        connected_instance.listener.exec_error_code = None

        with pytest.raises(FDSHardwareError):
            connected_instance.execute_protocol([fake_protocol])

    def test_sets_measure_channels_flag_for_long_pulse(self, connected_instance):
        """Extra exec_flags are always computed based on pulse_dur, mirroring
        TestWaitForTrigger's identical coverage of this same logic. execute_protocol has no
        trigger_option flag addition, so no extra flag needs to be added to `expected` here."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=5.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureChannels)
        assert int(exec_flags) == int(expected)

    def test_measure_flag_uses_shortest_pulse_dur_across_an_interleaved_group(
            self, connected_instance):
        """MeasureChannels/MeasureBoards/MeasureTimings is 'the most detailed mode the pulse can
        support' -- a strict superset hierarchy, not independent bits (see the test above).
        When interleaving, the flag must be conservative enough for every protocol's own pulse,
        not just the first one's -- fake_protocol1's pulse_dur (5.0) alone would qualify for
        MeasureChannels, but fake_protocol2's (0.01) only supports MeasureTimings, so the group
        as a whole must not exceed what the shortest pulse can handle."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol1 = SimpleNamespace(buffer_num=0, pulse_dur=5.0, pulse_ramp_dur=0,
                                         pulse_ramp_shape='Rectangular - no ramping', slots=[])
        fake_protocol2 = SimpleNamespace(buffer_num=0, pulse_dur=0.01, slots=[])

        connected_instance.execute_protocol([fake_protocol1, fake_protocol2],
                                            total_alternating_duration_ms=100)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureTimings)
        assert int(exec_flags) == int(expected)

    def test_sets_measure_boards_flag_for_medium_pulse(self, connected_instance):
        """Same as above, one threshold down: pulse_dur between the
        MeasureBoards (0.035 ms) and MeasureChannels (4.570 ms) defaults."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=1.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureBoards)
        assert int(exec_flags) == int(expected)

    def test_sets_measure_timings_flag_for_short_pulse(self, connected_instance):
        """Same as above, lowest threshold: pulse_dur between the
        MeasureTimings (0.001 ms) and MeasureBoards (0.035 ms) defaults."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.01, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.MeasureTimings)
        assert int(exec_flags) == int(expected)

    def test_raises_when_never_sent_regardless_of_connection_state(self, mocker, tmp_path):
        """A protocol that was never sent is a caller mistake either way -- is_protocol_sent()
        is checked before is_connected() (see the source), so neither the 'already connected'
        happy path nor the 'not connected' reconnect-and-resend path is ever reached."""
        instance = IGT(log_dir=str(tmp_path))
        mock_connect = mocker.patch.object(instance, 'connect')
        mock_send = mocker.patch.object(instance, 'send_protocol')

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'))

        with pytest.raises(FDSValidationError):
            instance.execute_protocol([fake_protocol])

        mock_connect.assert_not_called()
        mock_send.assert_not_called()

    def test_reconnects_sends_and_executes_when_not_connected(self, mocker, tmp_path):
        """Mirrors TestSendProtocol's reconnect test -- execute_protocol
        has the identical 'not connected -> connect(), then retry' shape.

        This reconnect-and-resend path is only reached once a protocol is already known to
        have been sent (buffer 0 pre-populated in sent_protocols below) -- it recovers a
        dropped connection after a real send, it doesn't fill in for a caller who never sent
        anything at all (see test_raises_when_never_sent_regardless_of_connection_state for
        that case, which must not reconnect or send)."""
        instance = IGT(log_dir=str(tmp_path))
        instance.sent_protocols[0] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                      'total_protocol_duration_ms': 10.0}

        def fake_connect(connect_info):
            instance.fus = mocker.Mock()
            instance.fus.isConnected.return_value = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_protocol(*args, **kwargs):
            instance.sent_protocols[0] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                          'total_protocol_duration_ms': 10.0}
        mock_send = mocker.patch.object(instance, 'send_protocol', side_effect=fake_send_protocol)

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping',
            slots=[])

        instance.execute_protocol([fake_protocol])

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        mock_send.assert_called_once()
        instance.gen.startSequence.assert_called_once()

    def test_reconnect_resends_with_this_calls_own_duration(self, mocker, tmp_path):
        """The reconnect-and-resend path passes total_alternating_duration_ms straight through,
        unmodified -- safe because _assert_ready_to_run() (specifically
        _assert_duration_matches_sent()) already guarantees it matches what this buffer was
        actually sent with whenever that distinction matters (interleaving); for a single
        protocol like this one, the value is never used for anything physical either way, so it
        being un-reconciled here is harmless by construction, not merely untested."""
        instance = IGT(log_dir=str(tmp_path))
        instance.sent_protocols[0] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                      'total_protocol_duration_ms': 10.0}

        def fake_connect(connect_info):
            instance.fus = mocker.Mock()
            instance.fus.isConnected.return_value = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_protocol(*args, **kwargs):
            instance.sent_protocols[0] = {'n_pulse_train_rep': 1, 'pulse_train_delay': 0.0,
                                          'total_protocol_duration_ms': 10.0}
        mock_send = mocker.patch.object(instance, 'send_protocol', side_effect=fake_send_protocol)

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping',
            slots=[])

        instance.execute_protocol([fake_protocol], total_alternating_duration_ms=5000)

        mock_send.assert_called_once_with([fake_protocol], 5000, 0)

    def test_raises_on_exception_during_execution(self, connected_instance):
        """The broad 'except Exception: raise FDSHardwareError' wrapper around the
        prepare/start/wait calls -- any hardware-layer failure should
        surface as an FDSHardwareError, not propagate raw."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        connected_instance.gen.prepareSequence.side_effect = RuntimeError('hardware fault')
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        with pytest.raises(FDSHardwareError):
            connected_instance.execute_protocol([fake_protocol])

    def test_raises_when_listener_reports_protocol_execution_error(self, connected_instance):
        """GitHub issue #112: unifus.FUSListener's onSequenceResult callback used to only log
        the error (see igt/utils.py's ExecListener) -- execute_protocol() itself never noticed,
        so the program silently continued as if ultrasound had actually been emitted.

        unifus.FUSListener's own docstring states exceptions raised inside its callbacks are
        not propagated to Python, so the exception cannot be raised inside onSequenceResult
        itself -- it has to be raised here, in execute_protocol(), after wait_protocol() returns
        on the calling thread. ExecListener.onSequenceResult() stores the failure on
        self.exec_error_code (a plain attribute set, unaffected by that restriction); this
        checks that execute_protocol() then acts on it."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        connected_instance.listener.exec_error_code = 2863311530
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        with pytest.raises(FDSHardwareError):
            connected_instance.execute_protocol([fake_protocol])

    def test_does_not_raise_when_listener_reports_no_error(self, connected_instance):
        """Mirrors the test above: a successful execution (exec_error_code left at None by
        ExecListener.onSequenceResult()) must not raise."""
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])  # must not raise

        connected_instance.listener.wait_protocol.assert_called_once()

    def test_logs_intensity_summary_before_and_after_execution(self, connected_instance, caplog):
        """GitHub #125/#122: a researcher should see what's about to run before the (possibly
        blocking) wait, and get the same confirmation once execution is actually confirmed
        successful."""
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        slots=[_slot(serial='TRAN-A')])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
            'total_protocol_duration_ms': 500.0,
            'intensity_lines': connected_instance._build_intensity_lines([fake_protocol], 0)}}

        with caplog.at_level('INFO'):
            connected_instance.execute_protocol([fake_protocol])

        assert 'About to execute:' in caplog.text
        assert 'Protocol executed successfully:' in caplog.text
        assert caplog.text.count('TRAN-A: fake intensity summary') == 2

    def test_raises_when_given_protocol_does_not_match_sent(self, connected_instance):
        """is_protocol_sent(buffer_num) alone only proves *something* was sent to this buffer,
        not that these specific protocol objects are it -- without _assert_matches_sent(), this
        would silently compute exec_flags/pulse_dur thresholds from a protocol that has nothing
        to do with what's physically on the buffer (GitHub #122/#125). Uses two differently
        -labeled fake slots so a mismatch is unambiguous."""
        sent_protocol = SimpleNamespace(buffer_num=0, slots=[_slot(serial='SENT-TRAN')])
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'total_protocol_duration_ms': 500.0,
                                                 'source_protocols': [sent_protocol],
                                                 'intensity_lines': []}}
        given_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                         pulse_ramp_shape='Rectangular - no ramping',
                                         slots=[_slot(serial='GIVEN-TRAN')])

        with pytest.raises(FDSValidationError):
            connected_instance.execute_protocol([given_protocol])

        connected_instance.gen.prepareSequence.assert_not_called()

    def test_raises_when_slot_reconfigured_after_send_without_resending(self, connected_instance):
        """A researcher who calls slot.configure() again after send_protocol() but forgets to
        resend must not have their new value silently ignored (GitHub #122/#125) -- the driving
        system would still fire whatever was baked in at send time. This must actually block
        execution, not just log the discrepancy: log messages alone aren't a reliable enough
        safeguard against a value a researcher doesn't carefully re-check."""
        mutable_slot = SimpleNamespace(intensity_summary=lambda: mutable_slot.current_summary,
                                       transducer=SimpleNamespace(serial='TRAN-A'),
                                       oper_freq=500, dephasing_degree=None,
                                       focus_wrt_mid_bowl=40.0, ampl=[30.0])
        mutable_slot.current_summary = 'TRAN-A: 0.30 MPa'
        protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                   pulse_ramp_shape='Rectangular - no ramping',
                                   slots=[mutable_slot])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0, 'total_protocol_duration_ms': 500.0,
            'source_protocols': [protocol],
            'intensity_lines': connected_instance._build_intensity_lines([protocol], 0),
            'protocol_fingerprints': connected_instance._build_protocol_fingerprints([protocol])}}

        # Reconfigured after sending, without resending -- e.g. slot.configure(...) called again.
        mutable_slot.current_summary = 'TRAN-A: 0.80 MPa'
        mutable_slot.ampl = [80.0]

        with pytest.raises(FDSSafetyError):
            connected_instance.execute_protocol([protocol])

        connected_instance.gen.prepareSequence.assert_not_called()

    def test_raises_when_given_duration_does_not_match_sent_when_interleaving(
            self, connected_instance):
        """total_alternating_duration_ms is never actually read by execute_protocol()/
        wait_for_trigger() for anything physical -- passing a different value here than what
        this buffer was actually sent with must not look like it's silently being honored
        (GitHub #122/#125): it never was, either way, so a mismatch should be a clear error
        instead."""
        protocol1 = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                    pulse_ramp_shape='Rectangular - no ramping',
                                    slots=[_slot(serial='TRAN-A')])
        protocol2 = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                    pulse_ramp_shape='Rectangular - no ramping',
                                    slots=[_slot(serial='TRAN-B')])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0, 'total_protocol_duration_ms': 500.0,
            'total_alternating_duration_ms': 1000,
            'source_protocols': [protocol1, protocol2],
            'intensity_lines': connected_instance._build_intensity_lines(
                [protocol1, protocol2], 0),
            'protocol_fingerprints': connected_instance._build_protocol_fingerprints(
                [protocol1, protocol2])}}

        with pytest.raises(FDSValidationError):
            connected_instance.execute_protocol([protocol1, protocol2],
                                                total_alternating_duration_ms=5000)

        connected_instance.gen.prepareSequence.assert_not_called()

    def test_raises_when_oper_freq_changed_without_touching_focus_or_power(
            self, connected_instance):
        """oper_freq/dephasing_degree have their own public setters, independent of configure()
        -- changing either directly (without touching chosen focus/power at all) still changes
        what _define_pulse_group() actually builds, so it must be caught too, not just a focus/
        power drift (GitHub #122/#125)."""
        slot = SimpleNamespace(intensity_summary=lambda: 'TRAN-A: unchanged',
                               transducer=SimpleNamespace(serial='TRAN-A'),
                               oper_freq=500, dephasing_degree=None,
                               focus_wrt_mid_bowl=40.0, ampl=[30.0])
        protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                   pulse_ramp_shape='Rectangular - no ramping', slots=[slot])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0, 'total_protocol_duration_ms': 500.0,
            'source_protocols': [protocol],
            'intensity_lines': connected_instance._build_intensity_lines([protocol], 0),
            'protocol_fingerprints': connected_instance._build_protocol_fingerprints([protocol])}}

        # slot.oper_freq = ... called directly, without configure() -- intensity_summary() (and
        # therefore intensity_lines) would stay unaware of this, since it never reads oper_freq.
        slot.oper_freq = 750

        with pytest.raises(FDSSafetyError):
            connected_instance.execute_protocol([protocol])

        connected_instance.gen.prepareSequence.assert_not_called()

    def test_raises_when_timing_reconfigured_without_touching_any_slot(self, connected_instance):
        """protocol.configure_timing() has its own effect on what gets baked into the buffer at
        send time (pulse_dur/pulse_rep_int/pulse_train_dur/pulse_train_rep_int/
        pulse_train_rep_dur/ramping) -- calling it again after send_protocol(), without
        resending, must be caught too, even when not a single slot was touched (GitHub
        #122/#125): execute_protocol()/wait_for_trigger() only ever read n_pulse_train_rep/
        pulse_train_delay/pulse_train_seq back from what was sent, never these fields live."""
        slot = SimpleNamespace(intensity_summary=lambda: 'TRAN-A: unchanged',
                               transducer=SimpleNamespace(serial='TRAN-A'),
                               oper_freq=500, dephasing_degree=None,
                               focus_wrt_mid_bowl=40.0, ampl=[30.0])
        protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_rep_int=1.0,
                                   pulse_train_dur=10.0, pulse_train_rep_int=20.0,
                                   pulse_train_rep_dur=100.0, pulse_ramp_dur=0,
                                   pulse_ramp_shape='Rectangular - no ramping', slots=[slot])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0, 'total_protocol_duration_ms': 500.0,
            'source_protocols': [protocol],
            'intensity_lines': connected_instance._build_intensity_lines([protocol], 0),
            'protocol_fingerprints': connected_instance._build_protocol_fingerprints([protocol])}}

        # protocol.configure_timing(...) called again, without resending -- no slot is touched at
        # all, only the protocol's own pulse_dur.
        protocol.pulse_dur = 2.0

        with pytest.raises(FDSSafetyError):
            connected_instance.execute_protocol([protocol])

        connected_instance.gen.prepareSequence.assert_not_called()


# ---------------------------------------------------------------------------
# _configure_voltage_feedback
# ---------------------------------------------------------------------------

class TestConfigureVoltageFeedback:
    """IGT._configure_voltage_feedback() (GitHub #137) -- called by both execute_protocol() and
    wait_for_trigger() right before startSequence(), building the VoltageFeedbackDispatcher
    (one VoltageFeedbackTracker per protocol) attached to self.listener.voltage_feedback. Only
    exercised via execute_protocol() here, mirroring how TestExecuteProtocol above already
    covers _compute_exec_flags() the same way -- VoltageFeedbackTracker's/
    VoltageFeedbackDispatcher's own grouping/warning/routing logic has its own direct tests in
    test_igt_utils.py."""

    def test_builds_channel_ranges_from_slots_in_order(self, connected_instance):
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 10, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 1000.0}}
        slot_a = _slot(elements=3, serial='TRAN-A', volt=[10.0])
        slot_b = _slot(elements=2, serial='TRAN-B', volt=[0.5, 0.6])
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        slots=[slot_a, slot_b])

        connected_instance.execute_protocol([fake_protocol])

        # A single protocol -> one tracker, at index 0 of the dispatcher (see
        # VoltageFeedbackDispatcher's own docstring).
        # pylint: disable=protected-access
        ranges = connected_instance.listener.voltage_feedback._trackers[0]._channel_ranges
        assert [c['serial'] for c in ranges] == ['TRAN-A', 'TRAN-B']
        assert (ranges[0]['channel_start'], ranges[0]['channel_end']) == (0, 3)
        assert (ranges[1]['channel_start'], ranges[1]['channel_end']) == (3, 5)
        assert ranges[0]['expected_volt'] == 10.0
        assert ranges[1]['expected_volt'] == 0.55  # mean of [0.5, 0.6]

    def test_builds_a_none_expected_volt_when_no_active_calibration(self, connected_instance):
        """volt=None (see _slot()'s own default) means no active calibration -- the slot still
        gets a channel range, just with expected_volt=None, so VoltageFeedbackTracker still
        reports its measured average (see its own docstring) instead of dropping it."""
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 10, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 1000.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        slots=[_slot(serial='TRAN-OFF')])

        connected_instance.execute_protocol([fake_protocol])

        # pylint: disable=protected-access
        ranges = connected_instance.listener.voltage_feedback._trackers[0]._channel_ranges
        assert len(ranges) == 1
        assert ranges[0]['serial'] == 'TRAN-OFF'
        assert ranges[0]['expected_volt'] is None

    def test_num_groups_uses_the_configured_value_for_a_short_protocol(self, connected_instance,
                                                                       patch_config):
        patch_config.set('Equipment.Manufacturer.IGT', 'Voltage feedback groups', '5')
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 10, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 1000.0}}  # 1 s -- the 60s floor never kicks in
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        # 10 pulses / 5 groups = 2 pulses per group.
        # pylint: disable-next=protected-access
        assert connected_instance.listener.voltage_feedback._trackers[0]._pulses_per_group == 2

    def test_num_groups_is_raised_to_stay_within_the_one_minute_floor_for_a_long_protocol(
            self, connected_instance, patch_config):
        """A long protocol split into only 'Voltage feedback groups' groups could otherwise go
        many minutes between updates -- the num_groups formula raises the group count (never
        lowers it) so a report is still logged at least once a minute."""
        patch_config.set('Equipment.Manufacturer.IGT', 'Voltage feedback groups', '5')
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 1000, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 600000.0}}  # 10 minutes
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        # 10 min / 60s floor -> 10 groups (not the configured 5), so 1000 / 10 = 100/group.
        # pylint: disable-next=protected-access
        assert connected_instance.listener.voltage_feedback._trackers[0]._pulses_per_group == 100

    def test_margin_and_consecutive_for_warning_are_config_driven(self, connected_instance,
                                                                  patch_config):
        patch_config.set('Equipment.Manufacturer.IGT', 'Voltage feedback margin [V]', '7.5')
        patch_config.set('Equipment.Manufacturer.IGT',
                         'Voltage feedback consecutive groups for warning', '3')
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 10, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 1000.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.execute_protocol([fake_protocol])

        tracker = connected_instance.listener.voltage_feedback._trackers[0]
        # pylint: disable=protected-access
        assert tracker._margin_v == 7.5
        assert tracker._consecutive_for_warning == 3

    def test_builds_one_independent_tracker_per_interleaved_protocol(
            self, connected_instance, mocker):
        """GitHub #137 follow-up: each protocol in an interleaved group gets its own tracker
        (with its own channel ranges), not one shared tracker built from protocols[0] only --
        otherwise every other protocol's pulses would be compared against the wrong protocol's
        expected voltages (e.g. the exact "one transducer active, the other at 0%, alternating"
        pattern this whole feature exists to report on)."""
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 10, 'pulse_train_delay': 0.0,
            'total_protocol_duration_ms': 1000.0}}
        protocol_a = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                     pulse_ramp_shape='Rectangular - no ramping',
                                     pulse_rep_int=0.5, trigger_option='None', n_triggers=None,
                                     slots=[_slot(serial='TRAN-A', volt=[20.0])])
        protocol_b = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                     pulse_ramp_shape='Rectangular - no ramping',
                                     pulse_rep_int=0.5, trigger_option='None', n_triggers=None,
                                     slots=[_slot(serial='TRAN-B', volt=[0.4])])
        mocker.patch.object(connected_instance, '_assert_duration_given_when_interleaving')
        mocker.patch.object(connected_instance, '_assert_ready_to_run')

        connected_instance.execute_protocol([protocol_a, protocol_b],
                                            total_alternating_duration_ms=1000)

        # pylint: disable=protected-access
        dispatcher = connected_instance.listener.voltage_feedback
        assert len(dispatcher._trackers) == 2
        assert dispatcher._trackers[0]._channel_ranges[0]['serial'] == 'TRAN-A'
        assert dispatcher._trackers[0]._channel_ranges[0]['expected_volt'] == 20.0
        assert dispatcher._trackers[1]._channel_ranges[0]['serial'] == 'TRAN-B'
        assert dispatcher._trackers[1]._channel_ranges[0]['expected_volt'] == 0.4


# ---------------------------------------------------------------------------
# wait_for_trigger
# ---------------------------------------------------------------------------

class TestWaitForTrigger:

    def test_pulse_train_trigger_prepares_with_n_triggers_and_zero_delay(self, mocker,
                                                                         connected_instance,
                                                                         patch_config):
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        connected_instance.gen.prepareSequence.assert_called_once_with(0, 3, 0, mocker.ANY)
        connected_instance.gen.startSequence.assert_called_once()

    def test_marks_buffer_as_armed_once_arming_succeeds(self, connected_instance, patch_config):
        """wait_for_trigger_result() relies on this to tell a genuinely armed buffer apart from
        one that was merely sent (GitHub #122/#125) -- proven here directly, not just through
        wait_for_trigger_result()'s own guard."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'armed': False}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        assert connected_instance.sent_protocols[0]['armed'] is True

    def test_raises_when_total_alternating_duration_ms_omitted_for_interleaved_protocols(
            self, connected_instance):
        """Unlike a single protocol (which gets its own repetition count from its own
        pulse_train_rep_dur/pulse_train_rep_int), the interleaved group as a whole has no
        fallback for how long to keep alternating -- omitting it (leaving the default None) must
        not silently proceed. Checked before trigger_option is ever consulted, so 'None' (an
        arbitrary but valid choice) is fine here."""
        fake_protocol1 = SimpleNamespace(buffer_num=0)
        fake_protocol2 = SimpleNamespace(buffer_num=0)

        with pytest.raises(FDSValidationError):
            connected_instance.wait_for_trigger([fake_protocol1, fake_protocol2], 'None')

    def test_sets_measure_channels_flag_for_long_pulse(self, connected_instance, patch_config):
        """Extra exec_flags are always computed based on pulse_dur -- a separate code path from
        the reconnect-retry forwarding logic above, so it needs its own direct coverage.
        pulse_dur above the MeasureChannels threshold (default 4.570 ms) sets that flag. Note:
        MeasureChannels/MeasureBoards/MeasureTimings are not independent bits (3/2/1), so the
        resulting flags are compared for exact equality rather than checked with '&'."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=5.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureChannels)
        assert int(exec_flags) == int(expected)

    def test_sets_measure_boards_flag_for_medium_pulse(self, connected_instance, patch_config):
        """Same as above, one threshold down: pulse_dur between the
        MeasureBoards (0.035 ms) and MeasureChannels (4.570 ms) defaults."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=1.0, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureBoards)
        assert int(exec_flags) == int(expected)

    def test_sets_measure_timings_flag_for_short_pulse(self, connected_instance, patch_config):
        """Same as above, lowest threshold: pulse_dur between the
        MeasureTimings (0.001 ms) and MeasureBoards (0.035 ms) defaults."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.01, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        exec_flags = connected_instance.gen.prepareSequence.call_args.args[3]
        expected = (unifus.ExecFlag.DisableMonitoringChannelCombiner |
                    unifus.ExecFlag.DisableMonitoringChannelCurrentOut |
                    unifus.ExecFlag.TriggerOneSequence |
                    unifus.ExecFlag.MeasureTimings)
        assert int(exec_flags) == int(expected)

    def test_whole_protocol_trigger_prepares_with_stored_repetition_and_delay(self, mocker,
                                                                              connected_instance,
                                                                              patch_config):
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        connected_instance.wait_for_trigger([fake_protocol], 'TriggerWholeProtocol')

        connected_instance.gen.prepareSequence.assert_called_once_with(0, 2, 5.0, mocker.ANY)

    def test_unknown_trigger_option_raises(self, connected_instance, patch_config):
        """Regression: fake_protocol previously had no pulse_dur, so _compute_exec_flags()
        actually raised AttributeError before the trigger_option check was ever reached --
        invisible while both paths shared the same SystemExit, surfaced as a real test failure
        once they became distinguishable FDSValidationError/FDSHardwareError types."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        with pytest.raises(FDSValidationError):
            connected_instance.wait_for_trigger([fake_protocol], 'Bogus')

    def test_raises_when_never_sent_regardless_of_connection_state(self, mocker, tmp_path):
        """A protocol that was never sent is a caller mistake either way -- is_protocol_sent()
        is checked before is_connected() (see the source), so neither the 'already connected'
        happy path nor the 'not connected' reconnect-and-resend path is ever reached."""
        instance = IGT(log_dir=str(tmp_path))
        mock_connect = mocker.patch.object(instance, 'connect')
        mock_send = mocker.patch.object(instance, 'send_protocol')

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'))

        with pytest.raises(FDSValidationError):
            instance.wait_for_trigger([fake_protocol], 'None')

        mock_connect.assert_not_called()
        mock_send.assert_not_called()

    def test_reconnects_sends_and_waits_when_not_connected(self, mocker, tmp_path, patch_config):
        """Mirrors execute_protocol's reconnect test -- wait_for_trigger has the identical 'not
        connected -> connect(), then retry' shape.

        This reconnect-and-resend path is only reached once a protocol is already known to have
        been sent (pre-populated here) -- it recovers a dropped connection after a real send, it
        doesn't fill in for a caller who never sent anything at all (see
        test_raises_when_never_sent_regardless_of_connection_state for that case, which must
        not reconnect or send)."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        instance = IGT(log_dir=str(tmp_path))
        instance.sent_protocols[0] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}

        def fake_connect(connect_info):
            instance.fus = mocker.Mock()
            instance.fus.isConnected.return_value = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_protocol(*args, **kwargs):
            instance.sent_protocols[0] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}
        mock_send = mocker.patch.object(instance, 'send_protocol', side_effect=fake_send_protocol)

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping', slots=[])

        instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3)

        mock_connect.assert_called_once_with('igt/config/gen_test.json')
        mock_send.assert_called_once()
        instance.gen.startSequence.assert_called_once()

    def test_reconnect_resends_with_this_calls_own_duration(
            self, mocker, tmp_path, patch_config):
        """The reconnect-and-resend path passes total_alternating_duration_ms straight through,
        unmodified -- safe because _assert_ready_to_run() (specifically
        _assert_duration_matches_sent()) already guarantees it matches what this buffer was
        actually sent with whenever that distinction matters (interleaving); for a single
        protocol like this one, the value is never used for anything physical either way, so it
        being un-reconciled here is harmless by construction, not merely untested."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        instance = IGT(log_dir=str(tmp_path))
        instance.sent_protocols[0] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}

        def fake_connect(connect_info):
            instance.fus = mocker.Mock()
            instance.fus.isConnected.return_value = True
            instance.gen = mocker.Mock()
            instance.listener = mocker.Mock()
            instance.listener.exec_error_code = None
        mocker.patch.object(instance, 'connect', side_effect=fake_connect)

        def fake_send_protocol(*args, **kwargs):
            instance.sent_protocols[0] = {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}
        mock_send = mocker.patch.object(instance, 'send_protocol', side_effect=fake_send_protocol)

        fake_protocol = SimpleNamespace(
            buffer_num=0, driving_sys=SimpleNamespace(connect_info='igt/config/gen_test.json'),
            pulse_dur=0.5, pulse_ramp_dur=0, pulse_ramp_shape='Rectangular - no ramping', slots=[])

        instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain', n_triggers=3,
                                  total_alternating_duration_ms=5000)

        mock_send.assert_called_once_with([fake_protocol], 5000, 0)

    def test_raises_on_exception_during_trigger_wait(self, connected_instance, patch_config):
        """The broad 'except Exception: raise FDSHardwareError' wrapper around the
        prepare/start calls -- any hardware-layer failure should surface
        as an FDSHardwareError, not propagate raw."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0}}
        connected_instance.gen.prepareSequence.side_effect = RuntimeError('hardware fault')
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping', slots=[])

        with pytest.raises(FDSHardwareError):
            connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain',
                                                n_triggers=3)

    def test_logs_intensity_summary_before_arming(self, connected_instance, caplog, patch_config):
        """GitHub #125: a researcher should see what's about to fire before going to trigger it
        themselves and wait for the result."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        fake_protocol = SimpleNamespace(buffer_num=0, pulse_dur=0.5, pulse_ramp_dur=0,
                                        pulse_ramp_shape='Rectangular - no ramping',
                                        slots=[_slot(serial='TRAN-A')])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
            'intensity_lines': connected_instance._build_intensity_lines([fake_protocol], 0)}}

        with caplog.at_level('INFO'):
            connected_instance.wait_for_trigger([fake_protocol], 'TriggerOnePulseTrain',
                                                n_triggers=3)

        assert 'This will fire once triggered:' in caplog.text
        assert 'TRAN-A: fake intensity summary' in caplog.text

    def test_raises_when_given_protocol_does_not_match_sent(self, connected_instance,
                                                            patch_config):
        """is_protocol_sent(buffer_num) alone only proves *something* was sent to this buffer,
        not that these specific protocol objects are it -- without _assert_matches_sent(), this
        would silently compute exec_flags/trigger config from a protocol that has nothing to do
        with what's physically on the buffer (GitHub #122/#125). Uses two differently-labeled
        fake slots so a mismatch is unambiguous."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        sent_protocol = SimpleNamespace(buffer_num=0, slots=[_slot(serial='SENT-TRAN')])
        connected_instance.sent_protocols = {0: {'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
                                                 'source_protocols': [sent_protocol],
                                                 'intensity_lines': []}}
        given_protocol = SimpleNamespace(buffer_num=0, pulse_ramp_dur=0,
                                         pulse_ramp_shape='Rectangular - no ramping',
                                         slots=[_slot(serial='GIVEN-TRAN')])

        with pytest.raises(FDSValidationError):
            connected_instance.wait_for_trigger([given_protocol], 'TriggerOnePulseTrain',
                                                n_triggers=3)

        connected_instance.gen.prepareSequence.assert_not_called()

    def test_raises_when_slot_reconfigured_after_send_without_resending(
            self, connected_instance, patch_config):
        """A researcher who calls slot.configure() again after send_protocol() but forgets to
        resend must not have their new value silently ignored (GitHub #122/#125) -- the driving
        system would still arm to fire whatever was baked in at send time. This must actually
        block arming, not just log the discrepancy: log messages alone aren't a reliable enough
        safeguard against a value a researcher doesn't carefully re-check."""
        patch_config.set('Trigger', 'Option.pulse_train', 'TriggerOnePulseTrain')
        patch_config.set('Trigger', 'Option.whole_protocol', 'TriggerWholeProtocol')
        mutable_slot = SimpleNamespace(intensity_summary=lambda: mutable_slot.current_summary,
                                       transducer=SimpleNamespace(serial='TRAN-A'),
                                       oper_freq=500, dephasing_degree=None,
                                       focus_wrt_mid_bowl=40.0, ampl=[30.0])
        mutable_slot.current_summary = 'TRAN-A: 0.30 MPa'
        protocol = SimpleNamespace(buffer_num=0, pulse_ramp_dur=0,
                                   pulse_ramp_shape='Rectangular - no ramping',
                                   slots=[mutable_slot])
        connected_instance.sent_protocols = {0: {
            'n_pulse_train_rep': 2, 'pulse_train_delay': 5.0,
            'source_protocols': [protocol],
            'intensity_lines': connected_instance._build_intensity_lines([protocol], 0),
            'protocol_fingerprints': connected_instance._build_protocol_fingerprints([protocol])}}

        # Reconfigured after sending, without resending -- e.g. slot.configure(...) called again.
        mutable_slot.current_summary = 'TRAN-A: 0.80 MPa'
        mutable_slot.ampl = [80.0]

        with pytest.raises(FDSSafetyError):
            connected_instance.wait_for_trigger([protocol], 'TriggerOnePulseTrain', n_triggers=3)

        connected_instance.gen.prepareSequence.assert_not_called()


# ---------------------------------------------------------------------------
# wait_for_trigger_result
# ---------------------------------------------------------------------------

class TestWaitForTriggerResult:
    """GitHub issue #112: unlike execute_protocol(), wait_for_trigger() only arms the protocol
    to fire on the external trigger and returns immediately -- it never waits for or observes
    the actual (eventual, externally-triggered) execution result. wait_for_trigger_result() is
    the method a caller invokes separately, once the external trigger is expected to have
    fired, to block until completion and check the listener's exec_error_code."""

    def test_raises_when_listener_reports_protocol_execution_error(self, connected_instance):
        """exec_error_code causes an FDSHardwareError before _log_intensity_summary() is ever
        reached, so 'intensity_lines' isn't needed here -- only 'armed' is, to get past the
        arming guard."""
        connected_instance.sent_protocols[0] = {'armed': True}
        connected_instance.listener.exec_error_code = 2863311530

        with pytest.raises(FDSHardwareError):
            connected_instance.wait_for_trigger_result(0)

        connected_instance.listener.wait_protocol.assert_called_once_with(5.0)

    def test_raises_when_wait_protocol_times_out_without_a_result(self, connected_instance):
        """GitHub #78: wait_protocol() returns False specifically on timeout (see its own
        docstring) -- distinct from exec_error_code, which is only ever set once
        onSequenceResult() actually fires (e.g. the external trigger never arrived at all).
        Without checking this return value, the method would fall straight through to logging
        "executed successfully" on a protocol that never actually fired."""
        connected_instance.sent_protocols[0] = {'armed': True}
        connected_instance.listener.wait_protocol.return_value = False
        connected_instance.listener.exec_error_code = None

        with pytest.raises(FDSHardwareError):
            connected_instance.wait_for_trigger_result(0, timeout_s=10.0)

    def test_does_not_raise_when_listener_reports_no_error(self, connected_instance):
        connected_instance.sent_protocols[0] = {'intensity_lines': [], 'armed': True}

        # must not raise
        connected_instance.wait_for_trigger_result(0, timeout_s=10.0)

        connected_instance.listener.wait_protocol.assert_called_once_with(10.0)

    def test_logs_intensity_summary_on_confirmed_success(self, connected_instance, caplog):
        """GitHub #122/#125: confirms what was actually fired once the driving system reports
        the triggered execution succeeded -- sourced from what send_protocol() actually sent to
        this buffer, not from a caller-supplied protocol."""
        sent_protocol = SimpleNamespace(buffer_num=0, slots=[_slot(serial='TRAN-A')])
        connected_instance.sent_protocols[0] = {
            'intensity_lines': connected_instance._build_intensity_lines([sent_protocol], 0),
            'armed': True}

        with caplog.at_level('INFO'):
            connected_instance.wait_for_trigger_result(0, timeout_s=10.0)

        assert 'Triggered protocol executed successfully:' in caplog.text
        assert 'TRAN-A: fake intensity summary' in caplog.text

    def test_raises_when_nothing_was_ever_sent_to_this_buffer(self, connected_instance):
        """A buffer_num that was never actually sent to (e.g. a caller typo, or calling this
        before wait_for_trigger() at all) is always a caller mistake -- wait_for_trigger() itself
        can't have armed this buffer without send_protocol() having been called for it first, so
        there's nothing to genuinely wait for. Exits before ever blocking on wait_protocol(),
        rather than waiting out the full timeout only to report a misleading "success" with an
        empty summary underneath it."""
        with pytest.raises(FDSValidationError):
            connected_instance.wait_for_trigger_result(99, timeout_s=10.0)

        connected_instance.listener.wait_protocol.assert_not_called()

    def test_raises_when_sent_but_never_armed(self, connected_instance):
        """A buffer can be sent-to (send_protocol()) and even executed directly
        (execute_protocol()) without wait_for_trigger() ever having been called for it -- there
        is then nothing armed to wait a trigger result for, even though is_protocol_sent(buffer_
        num) alone would say True. register_sent_protocol() always resets 'armed' to False on a
        fresh send; only a real wait_for_trigger() call sets it back to True."""
        connected_instance.sent_protocols[0] = {'intensity_lines': [], 'armed': False}

        with pytest.raises(FDSValidationError):
            connected_instance.wait_for_trigger_result(0, timeout_s=10.0)

        connected_instance.listener.wait_protocol.assert_not_called()


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

    def test_does_not_block_or_raise(self, connected_instance):
        """Unlike wait_for_trigger_result(), this must never call wait_protocol() or raise --
        it is a pure, immediate getter."""
        connected_instance.listener.exec_error_code = 2863311530

        connected_instance.has_execution_error()  # must not raise

        connected_instance.listener.wait_protocol.assert_not_called()


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------

class TestDisconnect:

    def test_stops_protocol_and_marks_disconnected(self, mocker, connected_instance):
        mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        connected_instance.fus.isConnected.return_value = False

        connected_instance.disconnect()

        connected_instance.gen.stopSequence.assert_called_once()
        connected_instance.fus.clearListeners.assert_called_once()
        connected_instance.fus.disconnect.assert_called_once()
        assert connected_instance.is_connected() is False

    def test_marks_still_connected_when_fus_still_reports_connected(self, mocker,
                                                                    connected_instance):
        mocker.patch("fus_driving_systems.igt.igt_ds.time.sleep")
        connected_instance.fus.isConnected.return_value = True

        connected_instance.disconnect()

        assert connected_instance.is_connected() is True

    def test_noop_when_never_connected(self, tmp_path):
        instance = IGT(log_dir=str(tmp_path))

        instance.disconnect()  # gen and fus both None; must not raise
