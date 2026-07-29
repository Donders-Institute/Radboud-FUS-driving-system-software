# -*- coding: utf-8 -*-
"""
Shared fixtures for FitParams JSON regression tests.

These fixtures point to the configuration files that already live inside
the fus_driving_systems package itself (the same files the software on
the IGT driving systems actually uses), so there's no need for a
separate/duplicated copy in the test suite.

File discovery (which transducers/curve types exist) lives in
_discovery.py so it can be shared with test modules that need to build
parametrize lists at collection time.
"""
import pytest

from _discovery import CONVERSION_DATA_SUBPATH, resolve_conversion_data_dir


@pytest.fixture(scope="session", autouse=True)
def initialize_package_logger():
    """
    sequence.py presumably does 'from ...logging_config import logger'
    at import time -- that's an import-time binding. This name gets
    fixed at the moment sequence.py is first imported (during pytest's
    collection phase), and later calls to initialize_logger() (which
    updates the logger inside logging_config itself) no longer reach
    that copy inside sequence.py.

    Fix: overwrite the 'logger' name directly on the modules themselves,
    rather than relying on initialize_logger()'s own internal state.
    """
    import logging

    from fus_driving_systems import sequence as fds_sequence
    from fus_driving_systems.config import logging_config

    test_logger = logging.getLogger("fus_driving_systems.tests")
    if not test_logger.handlers:
        test_logger.addHandler(logging.NullHandler())
    test_logger.setLevel(logging.DEBUG)

    # Set it in both places, in case the package imports/uses the
    # logger separately in more than one spot.
    logging_config.logger = test_logger
    fds_sequence.logger = test_logger


@pytest.fixture(scope="session")
def conversion_data_dir():
    """Path to the directory with the real, in-package conversion-data JSON files."""
    return resolve_conversion_data_dir()


@pytest.fixture
def resource_path():
    """
    Returns the package-relative path (forward slashes, no absolute
    path) as expected by pkg_resources.resource_filename. Use this
    fixture (not fit_path) when passing a path to functions like
    sequence.extract_and_define_pp, which internally call
    pkg_resources themselves -- those reject absolute paths or '..'.
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
    open() (see load_json) -- not for functions that call
    pkg_resources.resource_filename themselves, since those don't
    accept absolute paths. Use resource_path for that instead.
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