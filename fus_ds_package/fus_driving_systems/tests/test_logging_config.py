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
    # type(h) is ... (not isinstance) because FileHandler is itself a
    # StreamHandler subclass -- isinstance(file_handler, StreamHandler)
    # is True, which would silently double-count it here.
    assert sum(type(h) is logging.FileHandler for h in logger.handlers) == 1
    assert sum(type(h) is logging.StreamHandler for h in logger.handlers) == 1


def test_sync_logger_replaces_module_reference_but_does_not_propagate_to_earlier_consumers():
    """
    Mirrors test_config.py's equivalent test for sync_config(): sync_logger()
    rebinds logging_config.py's own 'logger' name, but a module that already
    did 'from ...logging_config import logger' at its own import time (e.g.
    driving_system.py) keeps pointing at whatever it bound before -- this is
    exactly why conftest.py's initialize_package_logger fixture patches each
    consumer module's 'logger' attribute directly instead of relying on
    sync_logger().
    """
    from fus_driving_systems import driving_system

    original_logger = logging_config.logger
    original_consumer_logger = driving_system.logger
    stand_in_logger = logging.getLogger("unittest.sync_logger_marker")

    try:
        logging_config.sync_logger(stand_in_logger)

        assert logging_config.logger is stand_in_logger
        assert driving_system.logger is original_consumer_logger
        assert driving_system.logger is not stand_in_logger
    finally:
        logging_config.sync_logger(original_logger)
        driving_system.logger = original_consumer_logger
