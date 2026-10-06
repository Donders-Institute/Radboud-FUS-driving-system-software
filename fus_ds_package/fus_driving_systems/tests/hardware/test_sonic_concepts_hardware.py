# -*- coding: utf-8 -*-
"""
Hardware tests for the Sonic Concepts driving system (see conftest.py for how to run them, the
settings they need, and the safety limits).

What they can and cannot show: the TPO accepts or rejects every command with a response
(E1/E2/E3 for an error), and the package turns a rejection into an exception, so a protocol that
sends cleanly was accepted by the hardware. execute_protocol() only starts the pulse train
(START returns immediately) and the TPO reports nothing back about the emission itself, so
whether ultrasound was actually emitted still has to be checked by eye or with a hydrophone.
"""
import logging
import time

SENT_MESSAGE = 'Protocol sent successfully'
STARTED_MESSAGE = 'Protocol execution started.'


def _messages(records):
    return [record.getMessage() for record in records]


def _errors(records):
    return [record.getMessage() for record in records if record.levelno >= logging.ERROR]


def _wait_for(protocol):
    time.sleep(protocol.pulse_train_dur / 1000.0 + 0.5)


def test_send_and_execute(sc, make_sc_protocol, fds_log):
    """The whole route: send, start, and the confirmation names the timing that was asked for."""
    protocol = make_sc_protocol(pulse_dur=10, pulse_rep_int=50, pulse_train_dur=200)

    sc.send_protocol(protocol)
    assert sc.is_protocol_sent()
    sc.execute_protocol(protocol)
    _wait_for(protocol)

    messages = _messages(fds_log)
    sent = [message for message in messages if message.startswith(SENT_MESSAGE)]
    assert sent and '10.00 ms pulse every 50.00 ms, 200.00 ms total duration' in sent[0]
    assert STARTED_MESSAGE in messages
    assert not _errors(fds_log)


def test_several_power_values_are_accepted(sc, make_sc_protocol, sc_config, fds_log):
    """Global power is SC's only power option; the TPO answers E2 to a value out of range, so
    sending cleanly means each value was accepted. Sent only, never started. The values are
    capped (see conftest.py), so the upper ones can coincide: each distinct one is sent once."""
    powers_w = {sc_config.power_w / 2, sc_config.power_w,
                min(sc_config.power_w * 2, sc_config.max_power_w)}
    for power_w in sorted(powers_w):
        sc.send_protocol(make_sc_protocol(power_w=power_w))

    assert not _errors(fds_log)


def test_abort_leaves_the_connection_usable(sc, make_sc_protocol, fds_log):
    """abort() must be accepted while a pulse train is running, and the same connection must
    then take and start another protocol straight away."""
    long_run = make_sc_protocol(pulse_train_dur=3000)
    sc.send_protocol(long_run)
    sc.execute_protocol(long_run)
    time.sleep(1.0)

    sc.abort()

    follow_up = make_sc_protocol(pulse_train_dur=200)
    sc.send_protocol(follow_up)
    sc.execute_protocol(follow_up)
    _wait_for(follow_up)

    assert STARTED_MESSAGE in _messages(fds_log)
    assert not _errors(fds_log)
