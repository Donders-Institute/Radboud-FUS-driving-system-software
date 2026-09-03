# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.config.logging_config.

initialize_logger() creates a real log directory and a real file handler
on disk, and registers a logger under a name in Python's global logging
registry (logging.getLogger(name) -- a process-wide singleton keyed by
name, independent of this package). Each test uses patch_config to give
itself a unique 'Logging'/'Logger name' so tests can't accumulate
handlers on -- or interfere with -- each other or with any other logger,
and the test_logger_name fixture below always tears those handlers down
afterwards regardless of test outcome.
"""
from datetime import datetime
import faulthandler
import importlib.metadata
import logging
from pathlib import Path
import zipfile

import pytest

from fus_driving_systems.config import logging_config


@pytest.fixture
def test_logger_name(request):
    name = f"unittest.{request.node.name}"
    yield name
    logger_obj = logging.getLogger(name)
    for handler in logger_obj.handlers[:]:
        logger_obj.removeHandler(handler)
        handler.close()


def _read_zip_text(zip_path):
    """Reads the single archived entry inside a rotated ZipRotatingFileHandler .zip file."""
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        names = zip_file.namelist()
        assert len(names) == 1, f"expected exactly one archived entry, got {names}"
        return zip_file.read(names[0]).decode()


def _configure_logging(patch_config, logger_name, file_level='DEBUG',
                       console_level='INFO'):
    patch_config.set('Logging', 'Logger name', logger_name)
    patch_config.set('Logging', 'Log level file', file_level)
    patch_config.set('Logging', 'Log level console', console_level)
    patch_config.set('Logging', 'Timestamp format', '')
    patch_config.set('Logging', 'Initial part of log filename', 'unittest_')


def test_initialize_logger_creates_log_dir_if_missing(patch_config, tmp_path,
                                                      test_logger_name):
    log_dir = tmp_path / "nested" / "log_dir"
    assert not log_dir.exists()

    _configure_logging(patch_config, test_logger_name)
    logging_config.initialize_logger(str(log_dir), "testrun")

    assert log_dir.exists()


def test_initialize_logger_writes_log_messages_to_a_file(patch_config, tmp_path,
                                                         test_logger_name):
    """The log files live inside the timestamped session folder (get_session_log_dir()), not
    directly in log_dir -- see test_initialize_logger_creates_a_timestamped_session_folder.
    Only 'info' (mirrors the console level) and 'debug' (everything -- the one to always share
    when reporting a problem) receive this INFO-level message (DEBUG captures INFO too). The
    third file, 'measurements' (IGT's high-volume hardware data, kept separate -- see
    get_measurements_logger()), uses delay=True and is never even created here, since nothing
    writes to it via the main logger -- see
    test_initialize_logger_creates_measurements_file_only_once_something_is_logged_to_it for the
    case where something does."""
    _configure_logging(patch_config, test_logger_name)
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    logger.info("hello from the test suite")
    for handler in logger.handlers:
        handler.flush()

    session_log_dir = Path(logging_config.get_session_log_dir())
    log_files = list(session_log_dir.glob("*.txt"))
    assert len(log_files) == 2
    info_file = next(f for f in log_files if 'info' in f.name)
    debug_file = next(f for f in log_files if 'debug' in f.name)
    assert "hello from the test suite" in info_file.read_text()
    assert "hello from the test suite" in debug_file.read_text()
    assert not any('measurements' in f.name for f in log_files)


def test_initialize_logger_logs_the_package_version(patch_config, tmp_path, test_logger_name,
                                                    mocker):
    """Reproducing a result later needs to know which version of the software produced it --
    logged once per session, into both the info and debug files, so it's always in whatever log
    a researcher already has lying around."""
    mocker.patch('fus_driving_systems.config.logging_config.importlib.metadata.version',
                 return_value='9.9.9')
    _configure_logging(patch_config, test_logger_name)
    logging_config.initialize_logger(str(tmp_path), "testrun")

    session_log_dir = Path(logging_config.get_session_log_dir())
    log_files = list(session_log_dir.glob("*.txt"))
    info_file = next(f for f in log_files if 'info' in f.name)
    debug_file = next(f for f in log_files if 'debug' in f.name)
    assert 'fus_driving_systems version: 9.9.9' in info_file.read_text()
    assert 'fus_driving_systems version: 9.9.9' in debug_file.read_text()


def test_initialize_logger_creates_measurements_file_only_once_something_is_logged_to_it(
        patch_config, tmp_path, test_logger_name):
    """The flip side of the test above -- delay=True defers opening the file, not creating the
    handler, so once something actually logs through get_measurements_logger() (only IGT's
    onPulseResult() does today), the file appears on disk with that content, for whichever
    driving system's session actually needs it."""
    _configure_logging(patch_config, test_logger_name)
    logging_config.initialize_logger(str(tmp_path), "testrun")

    measurements_logger = logging_config.get_measurements_logger()
    measurements_logger.debug("a measurement line")
    for handler in measurements_logger.handlers:
        handler.flush()

    session_log_dir = Path(logging_config.get_session_log_dir())
    measurements_files = list(session_log_dir.glob("*measurements*.txt"))
    assert len(measurements_files) == 1
    assert "a measurement line" in measurements_files[0].read_text()


def test_initialize_logger_creates_a_timestamped_session_folder(patch_config, tmp_path,
                                                                test_logger_name):
    """GitHub issue #126 follow-up: the FDS log, the faulthandler log and IGT's native log
    should all end up in one shared, timestamped folder so a whole session can be found/shared
    as a single unit -- get_session_log_dir() is how IGT.connect() discovers it."""
    _configure_logging(patch_config, test_logger_name)
    patch_config.set('Logging', 'Timestamp format', '%Y-%m-%d')

    logging_config.initialize_logger(str(tmp_path), "testrun")

    session_log_dir = logging_config.get_session_log_dir()
    assert session_log_dir is not None
    assert Path(session_log_dir).is_dir()
    assert Path(session_log_dir).parent == tmp_path
    today = datetime.now().strftime('%Y-%m-%d')
    assert Path(session_log_dir).name == f'{today}_FDS_logs'


# ---------------------------------------------------------------------------
# enable_crash_detection() / is_crash_detection_enabled() (GitHub issue #126)
# ---------------------------------------------------------------------------

def test_is_crash_detection_enabled_reflects_enable_crash_detection(tmp_path):
    assert logging_config.is_crash_detection_enabled() is False

    logging_config.enable_crash_detection(str(tmp_path), str(tmp_path))

    assert logging_config.is_crash_detection_enabled() is True
    assert faulthandler.is_enabled()


def test_enable_crash_detection_is_a_no_op_when_already_enabled(tmp_path):
    """Calling this more than once in a process (e.g. initialize_logger() followed by IGT's
    own fallback call) must not retarget faulthandler or re-run the crash check."""
    logging_config.enable_crash_detection(str(tmp_path), str(tmp_path / "first"))
    first_file = logging_config._faulthandler_file

    logging_config.enable_crash_detection(str(tmp_path), str(tmp_path / "second"))

    assert logging_config._faulthandler_file is first_file
    assert not (tmp_path / "second").exists()


def test_enable_crash_detection_finds_no_crash_on_a_fresh_log_dir(tmp_path):
    """No pointer file yet (first-ever call for this log_dir) -- nothing to check, no counter
    file created."""
    logging_config.enable_crash_detection(str(tmp_path), str(tmp_path / "session_1"))

    assert not (tmp_path / "kernel_death_count.txt").exists()


def test_enable_crash_detection_detects_archives_and_counts_a_previous_session_crash(
        tmp_path, caplog):
    """The core GitHub issue #126 mechanism, simulating two separate process runs: session 1
    enables crash detection (recording a pointer to its own target folder), then crashes
    (simulated by writing content directly into its faulthandler log, and resetting the
    module-level state the way a fresh process would start). Session 2's call must find that
    evidence via the pointer -- not by looking in its own, brand new target folder, which was
    the real bug this replaced -- archive it, and count it."""
    caplog.set_level(logging.WARNING)
    log_dir = tmp_path / "logs"
    session_1_dir = log_dir / "session_1"
    session_2_dir = log_dir / "session_2"

    logging_config.enable_crash_detection(str(log_dir), str(session_1_dir))
    crash_content = "Fatal Python error: Segmentation fault\n\nThread 0x1234:\n..."
    (session_1_dir / "faulthandler_output.log").write_text(crash_content, encoding='utf-8')
    logging_config._faulthandler_file = None  # simulate a fresh process (session 1 crashed)

    logging_config.enable_crash_detection(str(log_dir), str(session_2_dir))

    assert (log_dir / "kernel_death_count.txt").read_text(encoding='utf-8') == "1"
    archived = list(session_1_dir.glob("*.crash"))
    assert len(archived) == 1
    assert archived[0].read_text(encoding='utf-8') == crash_content
    # session 2's own faulthandler file is fresh/empty, not overwritten with session 1's crash
    assert (session_2_dir / "faulthandler_output.log").read_text(encoding='utf-8') == ""
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any('kernel death' in m and '#126' in m for m in warnings)


def test_enable_crash_detection_counter_increments_across_more_than_one_crash(tmp_path):
    log_dir = tmp_path / "logs"

    logging_config.enable_crash_detection(str(log_dir), str(log_dir / "session_1"))
    (log_dir / "session_1" / "faulthandler_output.log").write_text("crash 1", encoding='utf-8')
    logging_config._faulthandler_file = None

    logging_config.enable_crash_detection(str(log_dir), str(log_dir / "session_2"))
    (log_dir / "session_2" / "faulthandler_output.log").write_text("crash 2", encoding='utf-8')
    logging_config._faulthandler_file = None

    logging_config.enable_crash_detection(str(log_dir), str(log_dir / "session_3"))

    assert (log_dir / "kernel_death_count.txt").read_text(encoding='utf-8') == "2"


def test_crash_check_failure_does_not_prevent_enabling_faulthandler(tmp_path):
    """The crash check is a best-effort diagnostic, not a requirement -- a corrupted
    kernel_death_count.txt must not block faulthandler from being enabled."""
    log_dir = tmp_path / "logs"
    session_1_dir = log_dir / "session_1"
    logging_config.enable_crash_detection(str(log_dir), str(session_1_dir))
    (session_1_dir / "faulthandler_output.log").write_text("crash", encoding='utf-8')
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "kernel_death_count.txt").write_text("not-a-number", encoding='utf-8')
    logging_config._faulthandler_file = None

    logging_config.enable_crash_detection(str(log_dir), str(log_dir / "session_2"))

    assert logging_config.is_crash_detection_enabled() is True


def test_initialize_logger_writes_log_messages_to_the_console(patch_config, tmp_path,
                                                              test_logger_name, capsys):
    _configure_logging(patch_config, test_logger_name)
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    logger.info("hello from the console handler")
    for handler in logger.handlers:
        handler.flush()

    captured = capsys.readouterr()
    assert "hello from the console handler" in captured.out


def test_initialize_logger_sets_logger_level_to_min_of_file_and_console(
        patch_config, tmp_path, test_logger_name):
    """'info' mirrors the console level (both ERROR here); 'debug' mirrors the configured file
    level (WARNING) -- see initialize_logger()'s own comment on why. logger.level is still the
    min of the two underlying config values, unchanged from before the file/level split."""
    _configure_logging(patch_config, test_logger_name, file_level='WARNING',
                       console_level='ERROR')
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    assert logger.level == logging.WARNING

    file_handlers = {Path(h.baseFilename).name: h for h in logger.handlers
                     if isinstance(h, logging.FileHandler)}
    console_handlers = [h for h in logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)]
    info_handler = next(h for name, h in file_handlers.items() if 'info' in name)
    debug_handler = next(h for name, h in file_handlers.items() if 'debug' in name)
    assert info_handler.level == logging.ERROR
    assert debug_handler.level == logging.WARNING
    assert console_handlers[0].level == logging.ERROR


def test_initialize_logger_does_not_accumulate_handlers_on_repeated_calls(
        patch_config, tmp_path, test_logger_name):
    """logger (the main _logger) ends up with 3 handlers: console, 'info' file, 'debug' file.
    The 'measurements' file lives on the separate _measurements_logger instead (see
    get_measurements_logger()) -- checked here too, so its own handler-reset logic (mirroring
    _logger's) is covered by the same repeated-calls test."""
    _configure_logging(patch_config, test_logger_name)
    logging_config.initialize_logger(str(tmp_path), "testrun")
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    assert len(logger.handlers) == 3
    # type(h) is ... (not isinstance) because ZipRotatingFileHandler is itself a
    # StreamHandler subclass (via RotatingFileHandler -> FileHandler -> StreamHandler) --
    # isinstance(file_handler, StreamHandler) is True, which would silently double-count it
    # here.
    assert sum(type(h) is logging_config.ZipRotatingFileHandler
               for h in logger.handlers) == 2
    assert sum(type(h) is logging.StreamHandler for h in logger.handlers) == 1

    measurements_logger = logging_config.get_measurements_logger()
    assert len(measurements_logger.handlers) == 1
    assert type(measurements_logger.handlers[0]) is logging_config.ZipRotatingFileHandler


def test_initialize_logger_rotates_and_zips_when_max_size_is_exceeded(patch_config, tmp_path,
                                                                      test_logger_name):
    """GitHub issue #75: once the log file grows past the configured max size, its current
    content is zipped under a unique name and a fresh, empty file continues receiving new log
    messages -- instead of the file growing forever. The tiny configured size below triggers
    several rollovers (not just one) across 50 messages, each producing its own .zip file --
    exercising both the truncate-on-reopen behavior and the per-rollover unique naming.

    Only the 'debug' file is checked here -- 'info' receives the identical INFO-level content
    (same maxBytes, so it rotates in lockstep) and 'measurements' receives nothing at all in
    this test (nothing writes to get_measurements_logger() here), so restricting the glob to
    'debug' keeps this test's counts deterministic regardless of the other two files."""
    _configure_logging(patch_config, test_logger_name)
    patch_config.set('Logging', 'Max log file size [MB]', str(200 / (1024 * 1024)))  # ~200 B
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    for i in range(50):
        logger.info(f"padding message number {i} to exceed the tiny size threshold")
    for handler in logger.handlers:
        handler.flush()

    session_log_dir = Path(logging_config.get_session_log_dir())
    txt_files = list(session_log_dir.glob("*debug*.txt"))
    zip_files = list(session_log_dir.glob("*debug*.zip"))

    assert len(txt_files) == 1  # the fresh file that kept logging after the last rollover
    assert len(zip_files) > 1  # several rollovers, each its own (uniquely named) .zip file

    zipped_content = "".join(_read_zip_text(zip_file) for zip_file in zip_files)
    # Spot-check start/middle/end of the pre-rollover range (0-48) rather than every message,
    # to catch a gap (e.g. a message lost between two rollovers) without an exhaustive,
    # brittle check of all 49.
    for i in (0, 24, 48):
        assert f"padding message number {i}" in zipped_content

    fresh_content = txt_files[0].read_text()
    assert "padding message number 49" in fresh_content
    assert "padding message number 0" not in fresh_content  # confirms a rollover, not a leftover


def test_zip_rotating_file_handler_rollover_produces_a_valid_zip_file(tmp_path):
    """Unit-level check of ZipRotatingFileHandler.doRollover() in isolation, decoupled from
    initialize_logger()/config: writes past maxBytes and confirms a .zip file with the original
    content appears, and the handler keeps logging afterwards into the same base path."""
    log_path = tmp_path / "handler_test.txt"
    # maxBytes is deliberately bigger than the first message alone (so it doesn't immediately
    # trigger its own empty rollover before being written) but smaller than first + second
    # combined (so exactly one rollover happens, right before the second message).
    handler = logging_config.ZipRotatingFileHandler(str(log_path), mode='w', maxBytes=100,
                                                    backupCount=0)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("unittest.zip_rotating_file_handler")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.debug("first message long enough to push past the tiny 50 byte threshold")
        logger.debug("second message, now in the fresh file")
        handler.flush()

        zip_files = list(tmp_path.glob("*.zip"))
        assert len(zip_files) == 1

        assert "first message" in _read_zip_text(zip_files[0])
        assert "second message" in log_path.read_text()
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_get_package_version_returns_unknown_when_metadata_missing(mocker):
    """A source checkout that was never `pip install`ed has no package metadata to read --
    degrades to a clear 'unknown' instead of crashing logger setup entirely."""
    mocker.patch('fus_driving_systems.config.logging_config.importlib.metadata.version',
                 side_effect=importlib.metadata.PackageNotFoundError)

    assert logging_config._get_package_version() == 'unknown'


def test_sync_logger_mutates_in_place_instead_of_rebinding(tmp_path):
    """
    SOLVED: sync_logger() is the public integration point used by the SonoRover One host
    application, which already has its own configured logger and wants our internal logging
    routed through it. It used to rebind logging_config.py's own logger to a different object,
    which any module that had already cached that object at its own import time would never
    see -- it kept pointing at whatever it bound before. Now sync_logger() copies the host
    logger's handlers/level/propagate onto the existing logger object in place instead.

    Every consumer module (tus_protocol.py, driving_system.py, transducer.py, the driving-system
    subclasses, igt/utils.py, igt/transducer_xyz.py) was itself refactored to call
    get_logger() at each log call site instead of caching the logger object, which
    structurally removes the stale-binding risk for those modules regardless of what
    sync_logger()/initialize_logger() do -- get_logger() always returns whatever the shared
    logger currently is. This test covers logging_config.sync_logger()'s own contract
    directly: it must mutate, not rebind. log_dir=tmp_path keeps sync_logger()'s crash-detection
    side effect (GitHub issue #126) off the real filesystem's default location."""
    original_logger = logging_config._logger
    original_handlers = original_logger.handlers
    original_level = original_logger.level
    original_propagate = original_logger.propagate
    stand_in_logger = logging.getLogger("unittest.sync_logger_marker")
    marker_handler = logging.NullHandler()
    stand_in_logger.addHandler(marker_handler)
    stand_in_logger.setLevel(logging.DEBUG)
    stand_in_logger.propagate = False

    try:
        logging_config.sync_logger(stand_in_logger, log_dir=str(tmp_path))

        assert logging_config._logger is original_logger  # same object, not rebound
        assert logging_config._logger.handlers == [marker_handler]
        assert logging_config._logger.level == logging.DEBUG
        assert logging_config._logger.propagate is False
    finally:
        original_logger.handlers = original_handlers
        original_logger.setLevel(original_level)
        original_logger.propagate = original_propagate


def test_sync_logger_logs_the_package_version(tmp_path, mocker):
    """A host application (e.g. SonoRover One) using sync_logger() instead of
    initialize_logger() must get the same version-logging benefit -- it's routed through
    new_logger's own handlers here, same as everything else sync_logger() logs."""
    mocker.patch('fus_driving_systems.config.logging_config.importlib.metadata.version',
                 return_value='9.9.9')
    original_logger = logging_config._logger
    original_handlers = original_logger.handlers
    original_level = original_logger.level
    original_propagate = original_logger.propagate
    stand_in_logger = logging.getLogger("unittest.sync_logger_version_marker")

    class _CapturingHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.messages = []

        def emit(self, record):
            self.messages.append(record.getMessage())

    capturing_handler = _CapturingHandler()
    stand_in_logger.addHandler(capturing_handler)
    stand_in_logger.setLevel(logging.DEBUG)
    stand_in_logger.propagate = False

    try:
        logging_config.sync_logger(stand_in_logger, log_dir=str(tmp_path))

        assert any('fus_driving_systems version: 9.9.9' in message
                   for message in capturing_handler.messages)
    finally:
        original_logger.handlers = original_handlers
        original_logger.setLevel(original_level)
        original_logger.propagate = original_propagate


def test_get_logger_reflects_sync_logger_from_a_consumer_module(tmp_path):
    """
    Demonstrates the structural fix end-to-end: driving_system.py (a consumer module) calls
    get_logger() at each log call site rather than caching the logger at its own import time,
    so it automatically reflects whatever sync_logger() most recently configured -- no matter
    when driving_system was imported relative to that call."""
    from fus_driving_systems import driving_system

    original_logger = logging_config._logger
    original_handlers = original_logger.handlers
    stand_in_logger = logging.getLogger("unittest.get_logger_marker")
    marker_handler = logging.NullHandler()
    stand_in_logger.addHandler(marker_handler)

    try:
        logging_config.sync_logger(stand_in_logger, log_dir=str(tmp_path))

        assert driving_system.get_logger() is original_logger
        assert driving_system.get_logger().handlers == [marker_handler]
    finally:
        original_logger.handlers = original_handlers
