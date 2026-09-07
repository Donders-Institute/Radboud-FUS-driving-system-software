# -*- coding: utf-8 -*-
"""
Shared fixtures for the fus_ds_gui test suite.

QT_QPA_PLATFORM is forced to 'offscreen' by default (before any PySide6 import elsewhere), so
the suite runs headlessly in CI/this environment without extra setup; set it explicitly in the
environment beforehand to override this with a real platform (e.g. for visually inspecting a
test run on a machine with a display).
"""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def patch_config():
    """
    Temporarily overrides fus_driving_systems' shared config_info entries and restores them
    after the test. Mirrors fus_driving_systems/tests/conftest.py's own fixture of the same
    name and behavior (not importable directly from there, see that file's own module docstring
    for why) so GUI widget tests can use synthetic driving systems instead of depending on
    whatever real ds_config.ini happens to ship with.
    """
    from fus_driving_systems.config.config import config_info

    _MISSING = object()
    snapshot = []

    def _set(section, key, value):
        if section not in config_info:
            config_info[section] = {}
            snapshot.append((section, None, _MISSING))
        snapshot.append((section, key, config_info[section].get(key, _MISSING)))
        config_info[section][key] = value

    yield SimpleNamespace(set=_set)

    for section, key, original in reversed(snapshot):
        if key is None:
            if original is _MISSING:
                config_info.pop(section, None)
        elif original is _MISSING:
            config_info[section].pop(key, None)
        else:
            config_info[section][key] = original
