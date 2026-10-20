# -*- coding: utf-8 -*-
"""Tests for the GUI's startup checks."""
from fus_ds_gui.app import warn_if_demo_pressure_limit_modified

DEMO_LIMIT_KEY = 'Demo maximum pressure allowed in free water [MPa]'


def test_no_warning_for_the_shipped_demo_pressure_limit(patch_config, caplog):
    patch_config.set('Power', DEMO_LIMIT_KEY, '0.6')

    with caplog.at_level('WARNING'):
        warn_if_demo_pressure_limit_modified()

    assert 'MODIFIED' not in caplog.text


def test_warning_names_a_modified_demo_pressure_limit(patch_config, caplog):
    patch_config.set('Power', DEMO_LIMIT_KEY, '1.0')

    with caplog.at_level('WARNING'):
        warn_if_demo_pressure_limit_modified()

    assert 'MODIFIED Demo mode pressure limit of 1.0 MPa (default: 0.6 MPa)' in caplog.text


def test_malformed_demo_pressure_limit_is_not_this_warnings_job(patch_config, caplog):
    patch_config.set('Power', DEMO_LIMIT_KEY, 'not a number')

    with caplog.at_level('WARNING'):
        warn_if_demo_pressure_limit_modified()  # must not raise

    assert 'MODIFIED' not in caplog.text
