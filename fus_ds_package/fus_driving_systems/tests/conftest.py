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
import faulthandler
import os
from types import SimpleNamespace

import pytest

from discovery import CONVERSION_DATA_SUBPATH, resolve_conversion_data_dir


@pytest.fixture(scope="session", autouse=True)
def _run_tests_from_a_scratch_directory(tmp_path_factory):
    """The real unifus.pyd native extension (imported transitively via igt_ds.py, exercised by
    igt/conftest.py's fixtures) writes its own startup-banner log file the moment a real
    unifus.FUSSystem() is used during a test -- named unifus_<timestamp>.log by the native
    library itself, in the current working directory. This isn't configurable from Python:
    igt_ds.py's own unifus.setLogPath(log_dir, ...) call only affects the *name*, not this
    initial banner, and no log_dir any test passes around changes where it lands. Running the
    whole session from a disposable scratch directory (instead of fus_ds_package/, the package's
    own source tree) keeps this file out of the repo working copy without needing any change to
    the native library itself -- pytest's own tmp_path_factory retention policy cleans it up
    over time, the same as any other test-generated tmp_path."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path_factory.mktemp('pytest_cwd'))

    yield

    os.chdir(original_cwd)


# Every consumer module (tus_protocol.py, driving_system.py, transducer.py, the driving-system
# subclasses, igt/utils.py, igt/transducer_xyz.py) calls logging_config.get_logger() at each
# log call site instead of importing 'logger' as a name, so none of them ever cache a
# reference that could go stale. sync_logger() below mutates the shared logger's
# handlers/level/propagate in place (see logging_config.py) rather than rebinding
# logging_config's own 'logger' name to a different object, so every consumer's next
# get_logger() call picks up the change regardless of import order -- this fixture doesn't
# need to patch any consumer module directly.
@pytest.fixture(scope="session", autouse=True)
def initialize_package_logger():
    """Gives the shared logger a quiet (NullHandler) configuration for the test session, via
    the same sync_logger() entry point used by host applications (e.g. SonoRover One) that
    embed this package with their own already-configured logger."""
    import logging

    from fus_driving_systems.config import logging_config

    test_logger = logging.getLogger("fus_driving_systems.tests")
    if not test_logger.handlers:
        test_logger.addHandler(logging.NullHandler())
    test_logger.setLevel(logging.DEBUG)

    logging_config.sync_logger(test_logger)


@pytest.fixture(autouse=True)
def _reset_session_log_dir():
    """logging_config.initialize_logger() sets a module-level _session_log_dir (see
    get_session_log_dir()) so the faulthandler/native IGT log files land in the same
    timestamped folder as the main FDS log, and enable_crash_detection() sets a module-level
    _faulthandler_file (see is_crash_detection_enabled()) so it only ever runs once per
    process. Reset both after every test, regardless of outcome, so one test calling
    initialize_logger()/sync_logger()/enable_crash_detection() can't leak that state into
    unrelated tests elsewhere in the suite that don't expect it -- these globals would
    otherwise persist for the rest of the pytest process."""
    yield

    from fus_driving_systems.config import logging_config

    logging_config._session_log_dir = None

    if logging_config._faulthandler_file is not None:
        faulthandler.disable()
        logging_config._faulthandler_file.close()
        logging_config._faulthandler_file = None


@pytest.fixture
def patch_config():
    """
    Temporarily overrides config_info[section][key] entries and restores
    them after the test. Mutates the real, shared ConfigParser in place
    (config_info) rather than replacing the object -- read_config()/
    read_additional_config()/sync_config() all work this way, and in-place
    mutation is what propagates to every module that did
    'from ...config import config_info as config' at its own import time.
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
    path) as expected by functions like calc_utils.extract_and_define_pp,
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
    calc_utils.extract_and_define_pp that resolve the path themselves via
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
