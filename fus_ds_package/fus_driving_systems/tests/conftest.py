# -*- coding: utf-8 -*-
"""
Shared fixtures for FitParams JSON regression tests.

These fixtures point to the configuration files that already live inside
the fus_driving_systems package itself (the same files the software on
the IGT driving systems actually uses), so there's no need for a
separate/duplicated copy in the test suite.

File discovery (which transducers/curve types exist) lives in
discovery.py so it can be shared with test modules that need to build
parametrize lists at collection time.
"""
from types import SimpleNamespace

import pytest

from discovery import CONVERSION_DATA_SUBPATH, resolve_conversion_data_dir

# Every module below does 'from ...logging_config import logger' at ITS OWN
# import time -- that's an import-time binding to whatever logging_config.logger
# was at that moment (None, since pytest collection imports these modules
# before any test runs). Reassigning logging_config.logger later (e.g. via
# initialize_logger()) does not reach these already-bound copies. This is a
# test-only artifact, not a production bug: every real entry-point script
# calls initialize_logger() before importing any of these modules, so the
# real logger is already in place by the time they bind their local name.
_LOGGER_CONSUMER_MODULES = [
    "fus_driving_systems.sequence",
    "fus_driving_systems.driving_system",
    "fus_driving_systems.transducer",
    "fus_driving_systems.citrus.citrus_ds",
    "fus_driving_systems.sonic_concepts.sonic_concepts_ds",
    "fus_driving_systems.igt.igt_ds",
    "fus_driving_systems.igt.transducerXYZ",
    "fus_driving_systems.igt.utils",
]


@pytest.fixture(scope="session", autouse=True)
def initialize_package_logger():
    """
    Overwrites the 'logger' name directly on every consumer module,
    rather than relying on logging_config's own internal state -- see
    the _LOGGER_CONSUMER_MODULES comment above for why that's needed.
    """
    import importlib
    import logging

    from fus_driving_systems.config import logging_config

    test_logger = logging.getLogger("fus_driving_systems.tests")
    if not test_logger.handlers:
        test_logger.addHandler(logging.NullHandler())
    test_logger.setLevel(logging.DEBUG)

    logging_config.logger = test_logger
    for modname in _LOGGER_CONSUMER_MODULES:
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            # e.g. igt.* isn't importable without the real unifus.pyd on
            # this machine -- must not break the whole (autouse) session.
            continue
        mod.logger = test_logger


@pytest.fixture
def patch_config():
    """
    Temporarily overrides config_info[section][key] entries and restores
    them after the test. Mutates the real, shared ConfigParser in place
    (config_info) rather than replacing the object -- read_config()/
    read_additional_config() already work this way, and in-place mutation
    is what actually propagates to every module that did
    'from ...config import config_info as config' at its own import time
    (config.py's own sync_config() does NOT propagate for the same reason
    the logger needed the fixture above: it rebinds a name instead of
    mutating the shared object).
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


@pytest.fixture(scope="session")
def conversion_data_dir():
    """Path to the directory with the real, in-package conversion-data JSON files."""
    return resolve_conversion_data_dir()


@pytest.fixture
def resource_path():
    """
    Returns the package-relative path (forward slashes, no absolute
    path) as expected by functions like sequence.extract_and_define_pp,
    which internally resolve it via
    importlib.resources.files('fus_driving_systems').joinpath(...).
    Use this fixture (not fit_path) for those functions.

    """
    def _resource_path(filename):
        subpath = "/".join(CONVERSION_DATA_SUBPATH)
        return f"{subpath}/{filename}"
    return _resource_path


@pytest.fixture
def fit_path(conversion_data_dir):
    """
    Returns the full, absolute path to a config file based on its
    filename. Use this ONLY for reading the raw JSON directly via
    open() (see load_json) -- not for functions like
    sequence.extract_and_define_pp that resolve the path themselves via
    importlib.resources (see resource_path's note on why absolute
    paths aren't appropriate there). Use resource_path for that.
    """
    def _path(filename):
        path = conversion_data_dir / filename
        if not path.exists():
            available = sorted(p.name for p in conversion_data_dir.glob("*.json"))
            raise FileNotFoundError(
                f"'{filename}' not found in {conversion_data_dir}.\n"
                f"Files available there: {available}"
            )
        return path
    return _path


@pytest.fixture
def load_json(fit_path):
    """Loads a config file as a dict, based on its filename."""
    import json

    def _load(filename):
        with open(fit_path(filename)) as f:
            return json.load(f)
    return _load
