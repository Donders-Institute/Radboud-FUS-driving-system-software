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
import logging
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
    _configure_logging(patch_config, test_logger_name)
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    logger.info("hello from the test suite")
    for handler in logger.handlers:
        handler.flush()

    log_files = list(tmp_path.glob("*.txt"))
    assert len(log_files) == 1
    assert "hello from the test suite" in log_files[0].read_text()


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
    _configure_logging(patch_config, test_logger_name, file_level='WARNING',
                       console_level='ERROR')
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    assert logger.level == logging.WARNING

    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    console_handlers = [h for h in logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)]
    assert file_handlers[0].level == logging.WARNING
    assert console_handlers[0].level == logging.ERROR


def test_initialize_logger_does_not_accumulate_handlers_on_repeated_calls(
        patch_config, tmp_path, test_logger_name):
    _configure_logging(patch_config, test_logger_name)
    logging_config.initialize_logger(str(tmp_path), "testrun")
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    assert len(logger.handlers) == 2
    # type(h) is ... (not isinstance) because ZipRotatingFileHandler is itself a
    # StreamHandler subclass (via RotatingFileHandler -> FileHandler -> StreamHandler) --
    # isinstance(file_handler, StreamHandler) is True, which would silently double-count it
    # here.
    assert sum(type(h) is logging_config.ZipRotatingFileHandler
               for h in logger.handlers) == 1
    assert sum(type(h) is logging.StreamHandler for h in logger.handlers) == 1


def test_initialize_logger_rotates_and_zips_when_max_size_is_exceeded(patch_config, tmp_path,
                                                                      test_logger_name):
    """GitHub issue #75: once the log file grows past the configured max size, its current
    content is zipped under a unique name and a fresh, empty file continues receiving new log
    messages -- instead of the file growing forever. The tiny configured size below triggers
    several rollovers (not just one) across 50 messages, each producing its own .zip file --
    exercising both the truncate-on-reopen behavior and the per-rollover unique naming."""
    _configure_logging(patch_config, test_logger_name)
    patch_config.set('Logging', 'Max log file size [MB]', str(200 / (1024 * 1024)))  # ~200 B
    logger = logging_config.initialize_logger(str(tmp_path), "testrun")

    for i in range(50):
        logger.info(f"padding message number {i} to exceed the tiny size threshold")
    for handler in logger.handlers:
        handler.flush()

    txt_files = list(tmp_path.glob("*.txt"))
    zip_files = list(tmp_path.glob("*.zip"))

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


def test_sync_logger_mutates_in_place_instead_of_rebinding():
    """
    SOLVED: sync_logger() is the public integration point used by the SonoRover One host
    application, which already has its own configured logger and wants our internal logging
    routed through it. It used to rebind logging_config.py's own 'logger' name to a different
    object, which any module that had already done 'from ...logging_config import logger' at
    its own import time would never see -- it kept pointing at whatever it bound before. Now
    sync_logger() copies the host logger's handlers/level/propagate onto the existing logger
    object in place instead.

    Every consumer module (sequence.py, driving_system.py, transducer.py, the driving-system
    subclasses, igt/utils.py, igt/transducer_xyz.py) was itself refactored to call
    get_logger() at each log call site instead of importing 'logger' as a name, which
    structurally removes the stale-binding risk for those modules regardless of what
    sync_logger()/initialize_logger() do -- get_logger() always returns whatever
    logging_config.logger currently is. This test covers logging_config.sync_logger()'s own
    contract directly: it must mutate, not rebind."""
    original_logger = logging_config.logger
    original_handlers = original_logger.handlers
    original_level = original_logger.level
    original_propagate = original_logger.propagate
    stand_in_logger = logging.getLogger("unittest.sync_logger_marker")
    marker_handler = logging.NullHandler()
    stand_in_logger.addHandler(marker_handler)
    stand_in_logger.setLevel(logging.DEBUG)
    stand_in_logger.propagate = False

    try:
        logging_config.sync_logger(stand_in_logger)

        assert logging_config.logger is original_logger  # same object, not rebound
        assert logging_config.logger.handlers == [marker_handler]
        assert logging_config.logger.level == logging.DEBUG
        assert logging_config.logger.propagate is False
    finally:
        original_logger.handlers = original_handlers
        original_logger.setLevel(original_level)
        original_logger.propagate = original_propagate


def test_get_logger_reflects_sync_logger_from_a_consumer_module():
    """
    Demonstrates the structural fix end-to-end: driving_system.py (a consumer module) calls
    get_logger() at each log call site rather than caching 'logger' at its own import time, so
    it automatically reflects whatever sync_logger() most recently configured -- no matter when
    driving_system was imported relative to that call."""
    from fus_driving_systems import driving_system

    original_logger = logging_config.logger
    original_handlers = original_logger.handlers
    stand_in_logger = logging.getLogger("unittest.get_logger_marker")
    marker_handler = logging.NullHandler()
    stand_in_logger.addHandler(marker_handler)

    try:
        logging_config.sync_logger(stand_in_logger)

        assert driving_system.get_logger() is original_logger
        assert driving_system.get_logger().handlers == [marker_handler]
    finally:
        original_logger.handlers = original_handlers
