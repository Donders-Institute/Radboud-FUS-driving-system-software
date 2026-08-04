# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.sonic_concepts.sonic_concepts_ds.SonicConcepts.

connect() instantiates serial.Serial() inline (mock_serial fixture, see
conftest.py). Everything downstream of a connection funnels through the
single _send_command() choke point, or reads/writes self.gen directly --
the connected_instance fixture bypasses connect() entirely for those.
"""
import pytest


def test_connect_establishes_connection_on_normal_response(mock_serial):
    from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
    mock_serial.readline.return_value = b'READY\n'
    instance = SonicConcepts()

    instance.connect('COM3')

    assert instance.connected is True
    assert instance.sequence_sent is False


def test_connect_exits_on_e2_response(mock_serial):
    from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
    mock_serial.readline.return_value = b'E2\n'
    instance = SonicConcepts()

    with pytest.raises(SystemExit):
        instance.connect('COM3')
    assert instance.connected is False


def test_send_command_writes_and_returns_response(connected_instance):
    connected_instance.gen.readline.return_value = b'OK\n'

    response = connected_instance._send_command('FOO=1\r\n', sleep_time_s=0)

    connected_instance.gen.write.assert_called_once_with(b'FOO=1\r\n')
    assert response == 'OK'


def test_send_command_exits_on_e2_response(connected_instance):
    connected_instance.gen.readline.return_value = b'E2\n'

    with pytest.raises(SystemExit):
        connected_instance._send_command('FOO=1\r\n', sleep_time_s=0)


def test_set_operating_freq_converts_khz_to_hz(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_operating_freq(300)
    mock_send.assert_called_once_with('GLOBALFREQ=300000.0\r\n')


def test_set_focus_converts_mm_to_micrometer(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_focus(50)
    mock_send.assert_called_once_with('FOCUS=50000.0\r\n')


def test_set_global_power_converts_w_to_mw(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_global_power(2)
    mock_send.assert_called_once_with('GLOBALPOWER=2000.0\r\n', 0.1)


def test_set_global_power_exits_when_none(connected_instance):
    with pytest.raises(SystemExit):
        connected_instance._set_global_power(None)


def test_set_burst_length_sends_command(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_burst_length(500)
    mock_send.assert_called_once_with('BURST=500\r\n', 0.1)


def test_set_period_sends_command(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_period(1000)
    mock_send.assert_called_once_with('PERIOD=1000\r\n', 0.1)


def test_set_timer_converts_ms_to_us(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    connected_instance._set_timer(5)
    mock_send.assert_called_once_with('TIMER=5000.0\r\n', 0.1)


def test_set_burst_and_period_sets_period_first_when_burst_exceeds_current_prp(
        mocker, connected_instance):
    mocker.patch.object(connected_instance, '_send_command', return_value='0.5')
    mock_set_period = mocker.patch.object(connected_instance, '_set_period')
    mock_set_burst_length = mocker.patch.object(connected_instance, '_set_burst_length')
    manager = mocker.Mock()
    manager.attach_mock(mock_set_period, '_set_period')
    manager.attach_mock(mock_set_burst_length, '_set_burst_length')

    connected_instance._set_burst_and_period(des_burst=1, des_period=3)  # ms

    assert manager.mock_calls == [
        mocker.call._set_period(3000.0),
        mocker.call._set_burst_length(1000.0),
    ]


def test_set_burst_and_period_sets_burst_first_when_within_current_prp(
        mocker, connected_instance):
    mocker.patch.object(connected_instance, '_send_command', return_value='5')
    mock_set_period = mocker.patch.object(connected_instance, '_set_period')
    mock_set_burst_length = mocker.patch.object(connected_instance, '_set_burst_length')
    manager = mocker.Mock()
    manager.attach_mock(mock_set_period, '_set_period')
    manager.attach_mock(mock_set_burst_length, '_set_burst_length')

    connected_instance._set_burst_and_period(des_burst=1, des_period=3)  # ms

    assert manager.mock_calls == [
        mocker.call._set_burst_length(1000.0),
        mocker.call._set_period(3000.0),
    ]


def test_set_ramping_rectangular_resets_and_aborts(mocker, connected_instance, patch_config):
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    mock_reset_ramping = mocker.patch.object(connected_instance, '_reset_ramping')

    connected_instance._set_ramping('Rectangular - no ramping', 10)

    mock_reset_ramping.assert_called_once()
    mock_send.assert_called_once_with('ABORT\r\n', 0.1)


def test_set_ramping_unknown_mode_exits(mocker, connected_instance, patch_config):
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    patch_config.set('Ramp', 'Option.lin', 'Linear')
    patch_config.set('Ramp', 'Option.tuk', 'Tukey')
    mocker.patch.object(connected_instance, '_send_command')

    with pytest.raises(SystemExit):
        connected_instance._set_ramping('Something else', 10)


def test_set_ramping_linear_sends_rampmode_1(mocker, connected_instance, patch_config):
    """
    Regression test for a real bug found while writing this test: the
    RAMPMODE command used to be built as 'RAMPMODE={ramp_mode}\\r\\n' -- a
    plain string, missing the f-string prefix that RAMPLENGTH's command has
    one line below it. The literal, un-interpolated text '{ramp_mode}' was
    sent to the driving system instead of the actual mode number, regardless
    of which ramp mode was requested. Fixed by adding the missing f-prefix.
    """
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    patch_config.set('Ramp', 'Option.lin', 'Linear')
    patch_config.set('Ramp', 'Option.tuk', 'Tukey')
    mock_send = mocker.patch.object(connected_instance, '_send_command')

    connected_instance._set_ramping('Linear', 5)

    first_call_command = mock_send.call_args_list[0].args[0]
    assert first_call_command == 'RAMPMODE=1\r\n'


def test_set_ramping_linear_sends_ramplength_command(mocker, connected_instance, patch_config):
    """Symmetric to test_set_ramping_tukey_sends_ramplength_command below --
    Linear's RAMPLENGTH command was previously never independently
    asserted anywhere."""
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    patch_config.set('Ramp', 'Option.lin', 'Linear')
    patch_config.set('Ramp', 'Option.tuk', 'Tukey')
    mock_send = mocker.patch.object(connected_instance, '_send_command')

    connected_instance._set_ramping('Linear', 5)

    assert mock_send.call_count == 2
    second_call_command = mock_send.call_args_list[1].args[0]
    assert second_call_command == 'RAMPLENGTH=5000.0\r\n'


def test_set_ramping_tukey_sends_rampmode_2(mocker, connected_instance, patch_config):
    """Symmetric to the linear case above: Tukey must send mode 2."""
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    patch_config.set('Ramp', 'Option.lin', 'Linear')
    patch_config.set('Ramp', 'Option.tuk', 'Tukey')
    mock_send = mocker.patch.object(connected_instance, '_send_command')

    connected_instance._set_ramping('Tukey', 5)

    first_call_command = mock_send.call_args_list[0].args[0]
    assert first_call_command == 'RAMPMODE=2\r\n'


def test_set_ramping_tukey_sends_ramplength_command(mocker, connected_instance, patch_config):
    """Covers the previously-untested Tukey elif branch (ramp_mode = 2).
    Only asserts the RAMPLENGTH command (the second _send_command call) --
    the RAMPMODE command itself is asserted separately by
    test_set_ramping_tukey_sends_rampmode_2."""
    patch_config.set('Ramp', 'Option.rect', 'Rectangular - no ramping')
    patch_config.set('Ramp', 'Option.lin', 'Linear')
    patch_config.set('Ramp', 'Option.tuk', 'Tukey')
    mock_send = mocker.patch.object(connected_instance, '_send_command')

    connected_instance._set_ramping('Tukey', 5)

    assert mock_send.call_count == 2
    second_call_command = mock_send.call_args_list[1].args[0]
    assert second_call_command == 'RAMPLENGTH=5000.0\r\n'


def test_reset_parameters_sets_local_mode_and_resets_ramping(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')
    mock_reset_ramping = mocker.patch.object(connected_instance, '_reset_ramping')

    connected_instance._reset_parameters()

    mock_send.assert_called_once_with('LOCAL=1\r\n')
    mock_reset_ramping.assert_called_once()


def test_reset_ramping_sends_abort_then_rampmode_zero(mocker, connected_instance):
    mock_send = mocker.patch.object(connected_instance, '_send_command')

    connected_instance._reset_ramping()

    assert mock_send.call_args_list == [
        mocker.call('ABORT\r\n', 0.5),
        mocker.call('RAMPMODE=0\r\n'),
    ]


def test_check_tran_sel_confirm_does_not_exit(mocker, connected_instance):
    mocker.patch('fus_driving_systems.sonic_concepts.sonic_concepts_ds.tkinter.Tk')
    mock_box = mocker.patch(
        'fus_driving_systems.sonic_concepts.sonic_concepts_ds.CTkMessagebox')
    mock_box.return_value.get.return_value = 'Confirm'

    connected_instance.check_tran_sel()  # must not raise


def test_check_tran_sel_cancel_exits(mocker, connected_instance):
    mocker.patch('fus_driving_systems.sonic_concepts.sonic_concepts_ds.tkinter.Tk')
    mock_box = mocker.patch(
        'fus_driving_systems.sonic_concepts.sonic_concepts_ds.CTkMessagebox')
    mock_box.return_value.get.return_value = 'Cancel'

    with pytest.raises(SystemExit):
        connected_instance.check_tran_sel()


def test_disconnect_closes_gen_and_marks_disconnected(connected_instance):
    connected_instance.disconnect()

    connected_instance.gen.close.assert_called_once()
    assert connected_instance.connected is False


def test_send_sequence_calls_setters_in_order_and_marks_sent(mocker, connected_instance):
    manager = mocker.Mock()
    for name in ['_reset_parameters', '_set_operating_freq', '_set_focus',
                 '_set_global_power', '_set_burst_and_period', '_set_timer',
                 '_set_ramping']:
        manager.attach_mock(mocker.patch.object(connected_instance, name), name)
    manager.attach_mock(mocker.patch.object(connected_instance, '_send_command'),
                        '_send_command')

    fake_sequence = mocker.Mock()
    fake_sequence.wait_for_trigger = True
    fake_sequence.oper_freq = 300
    fake_sequence.focus_wrt_exit_plane = 50
    fake_sequence.global_power = 2
    fake_sequence.pulse_dur = 1
    fake_sequence.pulse_rep_int = 2
    fake_sequence.pulse_train_dur = 10
    fake_sequence.pulse_ramp_shape = 'Linear'
    fake_sequence.pulse_ramp_dur = 1

    connected_instance.send_sequence(fake_sequence)

    assert connected_instance.sequence_sent is True
    assert manager.mock_calls == [
        mocker.call._reset_parameters(),
        mocker.call._set_operating_freq(300),
        mocker.call._set_focus(50),
        mocker.call._set_global_power(2),
        mocker.call._set_burst_and_period(1, 2),
        mocker.call._set_timer(10),
        mocker.call._set_ramping('Linear', 1),
        mocker.call._send_command('TRIGGERMODE=1\r\n'),
    ]


def test_send_sequence_reconnects_when_not_connected(mocker):
    """Documents the reconnect-and-retry pattern shared with igt_ds.py:
    if not connected, connect() then retry the same call."""
    from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
    instance = SonicConcepts()
    instance.connected = False

    def fake_connect(connect_info):
        instance.connected = True
    mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)
    for name in ['_reset_parameters', '_set_operating_freq', '_set_focus',
                 '_set_global_power', '_set_burst_and_period', '_set_timer',
                 '_set_ramping']:
        mocker.patch.object(instance, name)

    fake_sequence = mocker.Mock()
    fake_sequence.driving_sys.connect_info = 'COM7'
    fake_sequence.wait_for_trigger = False

    instance.send_sequence(fake_sequence)

    mock_connect.assert_called_once_with('COM7')
    assert instance.sequence_sent is True


def test_execute_sequence_writes_start_command_when_sequence_sent(connected_instance):
    connected_instance.sequence_sent = True
    connected_instance.gen.readline.return_value = b'OK\n'

    connected_instance.execute_sequence(None)

    connected_instance.gen.write.assert_called_once_with(b'START\r')


def test_execute_sequence_exits_on_exception(connected_instance):
    connected_instance.sequence_sent = True
    connected_instance.gen.write.side_effect = OSError('boom')

    with pytest.raises(SystemExit):
        connected_instance.execute_sequence(None)


def test_execute_sequence_sends_then_executes_when_not_yet_sent(mocker, connected_instance):
    connected_instance.sequence_sent = False
    connected_instance.gen.readline.return_value = b'OK\n'

    def fake_send_sequence(seq):
        connected_instance.sequence_sent = True
    mock_send_sequence = mocker.patch.object(connected_instance, 'send_sequence',
                                             side_effect=fake_send_sequence)

    connected_instance.execute_sequence(mocker.Mock())

    mock_send_sequence.assert_called_once()
    connected_instance.gen.write.assert_called_once_with(b'START\r')


def test_execute_sequence_reconnects_when_not_connected(mocker):
    """execute_sequence() has its own reconnect-and-retry branch, separate
    from send_sequence()'s (test_send_sequence_reconnects_when_not_connected
    above) -- not connected here means connect() + send_sequence() +
    execute_sequence() all get retried."""
    from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts
    instance = SonicConcepts()
    instance.connected = False
    instance.gen = mocker.Mock()
    instance.gen.readline.return_value = b'OK\n'

    def fake_connect(connect_info):
        instance.connected = True
    mock_connect = mocker.patch.object(instance, 'connect', side_effect=fake_connect)
    mock_send_sequence = mocker.patch.object(instance, 'send_sequence')

    def fake_send_sequence(seq):
        instance.sequence_sent = True
    mock_send_sequence.side_effect = fake_send_sequence

    fake_sequence = mocker.Mock()
    fake_sequence.driving_sys.connect_info = 'COM7'

    instance.execute_sequence(fake_sequence)

    mock_connect.assert_called_once_with('COM7')
    mock_send_sequence.assert_called_once_with(fake_sequence)
    instance.gen.write.assert_called_once_with(b'START\r')
