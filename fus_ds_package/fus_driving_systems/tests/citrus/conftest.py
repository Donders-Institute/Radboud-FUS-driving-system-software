# -*- coding: utf-8 -*-
"""Fixtures local to citrus_ds.py tests: mocking the raw serial.Serial()
connection citrus_ds.py instantiates inline (no dependency-injection seam)."""
import pytest


@pytest.fixture
def mock_serial(mocker):
    """Patches serial.Serial as imported in citrus_ds.py; returns the fake
    instance that CITRUS.connect() will end up configuring."""
    mock_serial_cls = mocker.patch("fus_driving_systems.citrus.citrus_ds.serial.Serial")
    return mock_serial_cls.return_value
