# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.utils. get_config_value takes logger/config
as plain parameters (not module-level singletons), so these tests need no
fixtures at all -- a real configparser.ConfigParser (the documented type)
and a bare Mock logger are enough.
"""
import configparser
import logging
import re
from unittest.mock import Mock

import pytest

from fus_driving_systems.utils import (CustomFormatter, get_config_file,
                                       get_config_folder, get_config_value)

SECTION = "Some.Section"
KEY = "Some key"
VALUE = "42"
DEFAULT = "default-value"


def _config_missing_section():
    return configparser.ConfigParser()


def _config_missing_key():
    config = configparser.ConfigParser()
    config[SECTION] = {}
    return config


def _config_with_value():
    config = configparser.ConfigParser()
    config[SECTION] = {KEY: VALUE}
    return config


def test_returns_value_when_config_section_and_key_all_present():
    logger = Mock()
    result = get_config_value(logger, _config_with_value(), SECTION, KEY, DEFAULT)
    assert result == VALUE
    logger.warning.assert_not_called()


@pytest.mark.parametrize("config, expected_message_fragment", [
    (None, "Config not found"),
    (_config_missing_section(), f"Config section '{SECTION}' not found"),
    (_config_missing_key(), f"Config key '{KEY}' not found in section '{SECTION}'"),
])
def test_returns_default_and_warns_when_config_is_incomplete(config, expected_message_fragment):
    logger = Mock()
    result = get_config_value(logger, config, SECTION, KEY, DEFAULT)
    assert result == DEFAULT
    logger.warning.assert_called_once()
    warning_message = logger.warning.call_args[0][0]
    assert expected_message_fragment in warning_message
    assert f"using default: {DEFAULT}" in warning_message


@pytest.mark.parametrize("config, expected_message_fragment", [
    (None, "Config not found"),
    (_config_missing_section(), f"Config section '{SECTION}' not found"),
    (_config_missing_key(), f"Config key '{KEY}' not found in section '{SECTION}'"),
])
def test_sys_exits_when_config_is_incomplete_and_is_sys_exit_true(config,
                                                                  expected_message_fragment):
    logger = Mock()
    with pytest.raises(SystemExit) as exc_info:
        get_config_value(logger, config, SECTION, KEY, DEFAULT, is_sys_exit=True)
    assert expected_message_fragment in str(exc_info.value)
    logger.warning.assert_not_called()


def test_falls_back_to_root_logger_when_logger_is_none(caplog):
    """logger=None is only the bootstrap case (before initialize_logger()/sync_logger() has
    run) -- logging.warning() (module-level, hits the root logger) is used instead of print(),
    so this still goes through the logging framework rather than bypassing it."""
    with caplog.at_level('WARNING'):
        result = get_config_value(None, None, SECTION, KEY, DEFAULT)
    assert result == DEFAULT
    assert "Config not found" in caplog.text


def test_get_config_folder():
    assert get_config_folder() == "config"


def test_get_config_file():
    assert get_config_file() == "ds_config.ini"


def _make_log_record(msg="hello", args=(), func="my_function", lineno=42,
                     pathname="some_module.py", level=logging.INFO):
    return logging.LogRecord(
        name="fus_driving_systems.tests", level=level, pathname=pathname,
        lineno=lineno, msg=msg, args=args, exc_info=None, func=func)


def test_custom_formatter_includes_elapsed_time_and_function_info():
    formatted = CustomFormatter().format(_make_log_record())
    assert re.search(
        r"^Elapsed: \d+\.\d{2} seconds \(CPU: \d+\.\d{2} seconds\) - .+ - "
        r"Function: some_module\.my_function line 42 - hello$",
        formatted,
    )


def test_custom_formatter_preserves_message_arg_interpolation():
    """format() delegates the base message to logging.Formatter.format(),
    which applies %-style arg interpolation -- this should still happen
    underneath the custom prefix."""
    formatted = CustomFormatter().format(_make_log_record(msg="value is %s", args=("42",)))
    assert formatted.endswith("- value is 42")
