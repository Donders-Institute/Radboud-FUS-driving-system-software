# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

import logging
import inspect
import time

from fus_driving_systems.exceptions import FDSConfigError

# Get the start time
wall_t0 = time.time()
cpu_t0 = time.process_time()


class CustomFormatter(logging.Formatter):
    """
    Custom logging formatter that extends the functionality of logging. Formatter to include custom
    log information.

    This formatter calculates the elapsed time since the start of the program and includes it in
    each log message. Additionally, it includes function-related information such as the module,
    function name, and line number. The timestamp of each log record is also included in the
    formatted log message.

    Attributes:
        datefmt (str): The format string for formatting the timestamp in log records.

    Methods:
        format(record): Formats the specified log record by appending custom log information to it.
    """

    def format(self, record):
        """
        Formats the specified log record by appending custom log information to it.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message including custom log information.
        """

        elapsed_wall_time = time.time() - wall_t0
        elapsed_cpu_time = time.process_time() - cpu_t0
        elapsed_str = f"{elapsed_wall_time:.2f} seconds (CPU: {elapsed_cpu_time:.2f} seconds)"

        # Extract function-related information from the record
        func_info = f"{record.module}.{record.funcName} line {record.lineno}"

        # Get the timestamp of the log record
        timestamp = self.formatTime(record, self.datefmt)

        # Combine elapsed time, function information, and function docstring
        log_info = f"Elapsed: {elapsed_str} - {timestamp} - Function: {func_info}"

        # Apply the default formatting from the parent class
        formatted_record = super().format(record)

        # Concatenate the custom log information with the formatted record
        return f"{log_info} - {formatted_record}"


def get_config_value(logger, config, section, key, default, raise_on_missing=False):
    """
    Retrieve a configuration value from a given section and key.

    If the section or key is missing, logs a warning and returns the default value.

    Parameters:
    - logger (logging.Logger): The logger instance to log warnings.
    - config (configparser.ConfigParser): The configuration parser object.
    - section (str): The section in the configuration file.
    - key (str): The key within the section to retrieve.
    - default (any): The default value to return if the section or key is missing.
    - raise_on_missing (bool): If True, raise FDSConfigError instead of returning default when the
      config/section/key is missing.

    Returns:
    - any: The retrieved value or the default if missing.

    Raises:
    - FDSConfigError: If raise_on_missing is True and the config/section/key is missing.
    """

    # Logs the given message with caller-context (file/function/line of whoever called
    # get_config_value) added, at critical level when raise_on_missing (about to raise, no
    # default is being used) or warning level otherwise (falling back to default) -- returns the
    # formatted message either way, so the raise_on_missing branch can reuse it for the exception
    # without a second caller-context lookup.
    def log_missing(message):
        stack = inspect.stack()
        caller_frame = stack[2]  # The function that called get_config_value is two levels up
        file_name = caller_frame.filename
        line_number = caller_frame.lineno
        function_name = caller_frame.function
        location = f"(called from {file_name}, {function_name} at line {line_number})"

        if raise_on_missing:
            message = f"{message} {location}"
            log = logging.critical if logger is None else logger.critical
        else:
            message = f"{message}, using default: {default} {location}"
            # logger is None only in a bootstrap context, before initialize_logger()/
            # sync_logger() has run. logging.warning() (module-level, hits the root logger) is
            # used instead of print() so this still goes through the logging framework and lands
            # on stderr (via the root logger's default "last resort" handler) rather than stdout,
            # matching where a warning belongs.
            log = logging.warning if logger is None else logger.warning
        log(message)
        return message

    # Check if the config is None
    if config is None:
        message = log_missing("Config not found")
        if raise_on_missing:
            raise FDSConfigError(message)
        return default

    # Check if the section exists in the config
    if section not in config:
        message = log_missing(f"Config section '{section}' not found")
        if raise_on_missing:
            raise FDSConfigError(message)
        return default

    # Check if the key exists in the section
    if key not in config[section]:
        message = log_missing(f"Config key '{key}' not found in section '{section}'")
        if raise_on_missing:
            raise FDSConfigError(message)
        return default

    # Return the config value if found
    return config[section][key]


def get_config_folder():
    """
    Returns the configuration folder name.
    """

    return "config"


def get_config_file():
    """
    Returns the configuration file name.
    """

    return "ds_config.ini"
