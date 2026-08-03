# -*- coding: utf-8 -*-
"""Fixtures local to sonic_concepts_ds.py tests."""
import pytest

from fus_driving_systems.sonic_concepts.sonic_concepts_ds import SonicConcepts


@pytest.fixture
def mock_serial(mocker):
    """Patches serial.Serial as imported in sonic_concepts_ds.py; returns
    the fake instance that connect() assigns to self.gen."""
    mock_serial_cls = mocker.patch(
        "fus_driving_systems.sonic_concepts.sonic_concepts_ds.serial.Serial")
    return mock_serial_cls.return_value


@pytest.fixture
def connected_instance(mocker):
    """A SonicConcepts instance with self.gen replaced by a bare Mock,
    bypassing connect() entirely -- the natural seam for testing anything
    downstream of an established connection."""
    instance = SonicConcepts()
    instance.gen = mocker.Mock()
    instance.connected = True
    return instance
