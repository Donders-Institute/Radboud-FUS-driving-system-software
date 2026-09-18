# -*- coding: utf-8 -*-
"""
Tests for MockIGT/MockSonicConcepts: verify they satisfy ControlDrivingSystem's own contract
(connect/send_protocol/execute_protocol/disconnect all succeed) without ever touching real
hardware, and that isinstance(..., IGT)/isinstance(..., SonicConcepts) hold, the whole reason
they subclass the real classes instead of ControlDrivingSystem directly (see their own
docstrings). is_protocol_sent() is tested per class, not shared: IGT's own signature takes a
buffer_num, SonicConcepts' (inherited from the base class) doesn't.
"""
import pytest

from fus_driving_systems.exceptions import FDSHardwareError
from fus_driving_systems.igt.igt_ds import IGT
from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
from fus_driving_systems.tus_protocol import TUSProtocol

from fus_ds_gui.models.mock_driving_system import (MOCK_TRIGGER_PRESS_DELAY_S, MockIGT,
                                                   MockSonicConcepts)


def _configure_igt(patch_config):
    patch_config.set('Equipment', 'Driving systems', 'UNITTEST_IGT')
    section = 'Equipment.Driving system.UNITTEST_IGT'
    patch_config.set(section, 'Name', 'Test IGT')
    patch_config.set(section, 'Manufacturer', 'IGT')
    patch_config.set(section, 'Available channels', '2')
    patch_config.set(section, 'Connection info', 'MOCK')
    patch_config.set(section, 'Transducer compatibility', 'UNITTEST_TRAN')
    patch_config.set(section, 'Power options', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Focus options', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Native power parameters', 'Max. pressure in free water [MPa]')
    patch_config.set(section, 'Native focus parameters', 'Focus wrt exit plane [mm]')
    patch_config.set(section, 'Max. transducer slots', '1')
    patch_config.set(section, 'Active?', 'True')
    patch_config.set('Equipment', 'Transducers', 'UNITTEST_TRAN')
    tran_section = 'Equipment.Transducer.UNITTEST_TRAN'
    patch_config.set(tran_section, 'Elements', '2')
    patch_config.set(tran_section, 'Fund. freq.', '300')
    patch_config.set(tran_section, 'Min. focus', '10')
    patch_config.set(tran_section, 'Max. focus', '80')
    patch_config.set(tran_section, 'Exit plane - first element dist.', '5')
    patch_config.set(tran_section, 'Steer information', '')
    patch_config.set(tran_section, 'Active?', 'True')


def _build_igt_protocol():
    """Requires _configure_igt(patch_config) to have already run: a real TUSProtocol, not a
    bare object(), since MockIGT's own send_protocol()/execute_protocol() (unlike
    MockSonicConcepts') read protocol.slots to log the same per-slot summary the real IGT does,
    see MockIGT's own docstring. Timing is configured with a negligible pulse_train_rep_dur so
    execute_protocol()'s own realistic-duration sleep (see its docstring) doesn't slow tests
    down."""

    protocol = TUSProtocol('UNITTEST_IGT')
    protocol.add_slot('UNITTEST_TRAN', 'Focus wrt exit plane [mm]', 40,
                      'Max. pressure in free water [MPa]', 0.5)
    protocol.configure_timing(pulse_dur=1, pulse_train_rep_dur=0.001)
    return protocol


@pytest.fixture(params=[MockIGT, MockSonicConcepts], ids=['MockIGT', 'MockSonicConcepts'])
def mock_ds(request, monkeypatch):
    # connect()'s own artificial delay would otherwise slow this down for no benefit here.
    monkeypatch.setattr('fus_ds_gui.models.mock_driving_system.time.sleep', lambda _s: None)
    return request.param()


def test_starts_disconnected(mock_ds):
    assert mock_ds.is_connected() is False


def test_connect_marks_connected(mock_ds):
    mock_ds.connect('MOCK')

    assert mock_ds.is_connected() is True


def test_disconnect_marks_disconnected(mock_ds):
    mock_ds.connect('MOCK')

    mock_ds.disconnect()

    assert mock_ds.is_connected() is False


def test_execute_protocol_does_not_raise(mock_ds, patch_config):
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    mock_ds.connect('MOCK')
    mock_ds.send_protocol(protocol)

    mock_ds.execute_protocol(protocol)  # must not raise


def test_send_protocol_logs_which_transducers_for_igt(patch_config, caplog):
    """Matches the real IGT.send_protocol()'s own per-protocol "Validating protocol for
    buffer..." line, so a researcher sees which transducer(s) were actually just sent, the same
    way a real connection would show, rather than only a generic "sending..." with no detail at
    all (see MockIGT's own docstring)."""
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    mock_ds = MockIGT()

    with caplog.at_level('INFO'):
        mock_ds.send_protocol(protocol)

    assert 'UNITTEST_TRAN' in caplog.text
    assert 'validating protocol' in caplog.text.lower()
    assert 'sending protocol' in caplog.text.lower()


def test_execute_protocol_logs_a_per_slot_summary_before_and_after(patch_config, caplog):
    """Matches the real IGT.execute_protocol()'s own "About to execute:"/"...executed
    successfully:" pair (_log_intensity_summary(), GitHub #125/#122), so a researcher gets the
    same at-a-glance confirmation via the console panel a real connection would give, rather
    than a GUI-only widget duplicating it (see ExecutionPanel's own docstring)."""
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    mock_ds = MockIGT()

    with caplog.at_level('INFO'):
        mock_ds.execute_protocol(protocol)

    info_messages = [r.message for r in caplog.records if r.levelname == 'INFO']
    assert len(info_messages) == 2
    assert 'about to execute' in info_messages[0].lower()
    assert 'executed successfully' in info_messages[1].lower()
    for message in info_messages:
        assert 'UNITTEST_TRAN' in message


def test_execute_protocol_blocks_for_the_protocols_own_duration(patch_config, monkeypatch):
    """Real IGT.execute_protocol() blocks until the sonication itself is actually done; the
    Executing panel's countdown relies on that (see ExecutingPanel._on_executed()'s own
    docstring) to know when execution finished, rather than the estimate alone. Returning
    immediately here would skip straight to "Execution complete." instead."""
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    protocol.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    mock_ds = MockIGT()
    waited = []
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: waited.append(timeout))

    mock_ds.execute_protocol(protocol)

    assert waited == [5.0]


def test_abort_interrupts_execute_protocol(patch_config, monkeypatch):
    """abort() stands in for stopping real hardware mid-run: a demo run cut short has no clean
    success to report, matching what a real timed-out wait_protocol() would look like."""
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    protocol.configure_timing(pulse_dur=1, pulse_train_rep_dur=5)
    mock_ds = MockIGT()
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: True)  # aborted

    with pytest.raises(FDSHardwareError):
        mock_ds.execute_protocol(protocol)


def test_wait_for_trigger_then_result_logs_waiting_then_fired(patch_config, caplog, monkeypatch):
    _configure_igt(patch_config)
    mock_ds = MockIGT()
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: False)  # not aborted

    with caplog.at_level('INFO'):
        mock_ds.wait_for_trigger(_build_igt_protocol(), 'TriggerWholeProtocol')
        mock_ds.wait_for_trigger_result()

    assert 'waiting for a total of 1 trigger' in caplog.text.lower()
    assert 'triggered protocol executed successfully' in caplog.text.lower()


def test_wait_for_trigger_result_waits_longer_for_more_triggers(
        patch_config, monkeypatch):
    """Real hardware only ever reports one combined result for the whole armed group of
    n_triggers, never progress per individual trigger (onSequenceResult() fires once, after all
    of them have fired), so the Mock waits once, for all of them together, rather than
    logging (or resolving) each one separately."""
    _configure_igt(patch_config)
    mock_ds = MockIGT()
    waited = []
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: waited.append(timeout))

    mock_ds.wait_for_trigger(_build_igt_protocol(), 'TriggerOnePulseTrain', n_triggers=3)
    mock_ds.wait_for_trigger_result()

    assert len(waited) == 1  # one combined wait, not one per trigger
    # 3 triggers * (press delay + pulse_train_dur); pulse_train_dur is 1 ms, see
    # _build_igt_protocol()'s own configure_timing() call.
    assert waited[0] == pytest.approx(3 * (MOCK_TRIGGER_PRESS_DELAY_S + 0.001))


def test_wait_for_trigger_result_uses_the_whole_protocol_duration_for_whole_protocol_trigger(
        patch_config, monkeypatch):
    """A "TriggerWholeProtocol" trigger fires the entire protocol (all repetitions) on a single
    trigger, exactly like a plain execute_protocol() would, unlike "TriggerOnePulseTrain",
    which fires only one pulse train per trigger. Using pulse_train_dur here (much shorter than
    the whole protocol) would make the demo finish long before real hardware ever would."""
    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    protocol.configure_timing(pulse_dur=1, pulse_train_dur=10, pulse_train_rep_dur=5)
    mock_ds = MockIGT()
    waited = []
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: waited.append(timeout))

    mock_ds.wait_for_trigger(protocol, 'TriggerWholeProtocol')
    mock_ds.wait_for_trigger_result()

    assert len(waited) == 1  # a single trigger, whatever n_triggers may have been passed
    assert waited[0] == pytest.approx(MOCK_TRIGGER_PRESS_DELAY_S + 5.0)  # + pulse_train_rep_dur


def test_wait_for_trigger_result_raises_when_aborted(patch_config, monkeypatch):
    _configure_igt(patch_config)
    mock_ds = MockIGT()
    monkeypatch.setattr('threading.Event.wait', lambda self, timeout=None: True)  # aborted

    mock_ds.wait_for_trigger(_build_igt_protocol(), 'TriggerWholeProtocol')
    with pytest.raises(FDSHardwareError):
        mock_ds.wait_for_trigger_result()


def test_mock_igt_is_a_real_igt_instance():
    """The whole reason MockIGT subclasses IGT instead of ControlDrivingSystem: every
    isinstance(..., IGT) check the GUI does (the "connecting can take ~10s" hint,
    ProtocolBuilder.uses_pulse_train_repetition()) must still find this driving system."""

    assert isinstance(MockIGT(), IGT)


def test_mock_sc_is_a_real_sonic_concepts_instance():
    """Same reasoning as test_mock_igt_is_a_real_igt_instance above, for Sonic Concepts' own
    isinstance(..., SonicConcepts) check (the transducer-selection confirmation dialog)."""

    assert isinstance(MockSonicConcepts(), SonicConcepts)


def test_mock_igt_send_protocol_marks_buffer_0_as_sent(patch_config):
    _configure_igt(patch_config)
    mock_ds = MockIGT()

    mock_ds.send_protocol(_build_igt_protocol())

    assert mock_ds.is_protocol_sent(0) is True


def test_mock_igt_disconnect_clears_sent_protocols(patch_config):
    _configure_igt(patch_config)
    mock_ds = MockIGT()
    mock_ds.send_protocol(_build_igt_protocol())

    mock_ds.disconnect()

    assert mock_ds.is_protocol_sent(0) is False


def test_mock_sc_send_protocol_marks_protocol_sent():
    mock_ds = MockSonicConcepts()

    mock_ds.send_protocol(object())

    assert mock_ds.is_protocol_sent() is True


def test_mock_sc_disconnect_clears_protocol_sent():
    mock_ds = MockSonicConcepts()
    mock_ds.send_protocol(object())

    mock_ds.disconnect()

    assert mock_ds.is_protocol_sent() is False


def test_mock_igt_validate_protocol_skips_amplitude_is_none(patch_config):
    """See MockIGT.validate_protocol()'s own docstring: the real IGT.validate_protocol() would
    otherwise always flag every slot with "Amplitude is None" here, since ampl is only ever
    computed from a real, active calibration combo, which this no-active-combo synthetic
    fixture doesn't have (same reasoning as test_protocol_builder.py's own igt_with_transducer
    fixture)."""

    _configure_igt(patch_config)
    protocol = _build_igt_protocol()
    # Sanity check: the real IGT genuinely does flag this, so the assertion below is actually
    # exercising MockIGT's own override, not something that was never a problem to begin with.
    assert any('Amplitude is None' in error for error in IGT().validate_protocol(protocol))

    errors = MockIGT().validate_protocol(protocol)

    assert not any('Amplitude is None' in error for error in errors)


def test_mock_sc_wait_for_trigger_logs_armed(caplog):
    mock_ds = MockSonicConcepts()

    with caplog.at_level('INFO'):
        mock_ds.wait_for_trigger(object())

    assert 'armed' in caplog.text.lower()


def test_mock_sc_abort_logs_and_does_not_raise(caplog):
    mock_ds = MockSonicConcepts()

    with caplog.at_level('INFO'):
        mock_ds.abort()  # must not raise

    assert 'aborted' in caplog.text.lower()
