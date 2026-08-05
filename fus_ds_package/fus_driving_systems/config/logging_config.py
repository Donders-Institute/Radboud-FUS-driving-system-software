# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Margely Cornelissen, Stein Fekkes (Radboud University) and Erik Dumont (Image
Guided Therapy)

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

**Attribution Notice**:
If you use this kit in your research or project, please refer to the 'How to Cite' section in the
README.md file of https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basic packages
import os
import sys

# Miscellaneous packages
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import zipfile

# Own packages
from fus_driving_systems.config.config import config_info as config
from fus_driving_systems.utils import get_config_value


# A real logging.getLogger(...) singleton from the moment this module is imported (rather than
# None until initialize_logger() runs), so any module that reads it before
# initialize_logger()/sync_logger() ever runs still gets a valid, usable logger object instead
# of crashing on a None attribute access.
logger = logging.getLogger(
    get_config_value(None, config, 'Logging', 'Logger name', 'driving_system'))


def get_logger():
    """
    Returns the currently active shared logger.

    Modules that need to log should call this at each log call site (e.g.
    'get_logger().info(...)') instead of doing 'from ...logging_config import logger' once at
    their own import time: initialize_logger()/sync_logger() can (re)point 'logger' at a
    different or reconfigured object later on, and a function call always reads the current
    value, so callers never end up holding a stale reference from before that happened.

    Returns:
        logging.Logger: The currently active shared logger.
    """

    return logger


class ZipRotatingFileHandler(RotatingFileHandler):
    """
    A size-based rotating file handler that zips each rotated log file instead of using
    RotatingFileHandler's default numbered '.1', '.2', ... suffixes (GitHub issue #75). Used
    only by initialize_logger() below.

    doRollover() zips the base log file to '<base filename>.<rollover timestamp>_<rollover
    count>.zip' (the rollover timestamp and counter avoid collisions across several rollovers
    within the same second), then reopens the base path as a fresh, empty file -- so it's kept
    forever, never renumbered or deleted. The record that triggered the rollover ends up in
    that fresh file: RotatingFileHandler.emit() (not overridden here) calls doRollover() before
    actually writing.

    __init__ restores self.mode to what was requested: RotatingFileHandler.__init__ silently
    forces mode to 'a' whenever maxBytes > 0 (so a restarted long-running service keeps
    appending instead of losing history), which doesn't apply here since doRollover() already
    preserves old content via zip before each fresh start.
    """

    def __init__(self, filename, mode='w', maxBytes=0, backupCount=0, encoding=None,
                 delay=False, errors=None):
        super().__init__(filename, mode=mode, maxBytes=maxBytes, backupCount=backupCount,
                         encoding=encoding, delay=delay, errors=errors)
        # RotatingFileHandler.__init__ silently forces mode to 'a' whenever maxBytes > 0 (so a
        # restarted process appends to an existing file instead of truncating it) -- but
        # doRollover() below always reads and zips the full current content before reopening,
        # so each post-rollover file must start fresh and empty, not appended to.
        self.mode = mode
        self._rollover_count = 0

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        timestamp_format = get_config_value(None, config, 'Logging', 'Timestamp format',
                                            '%Y-%m-%d_%H-%M-%S')
        timestamp = datetime.now().strftime(timestamp_format)
        self._rollover_count += 1
        # The rollover counter guarantees a unique filename even if Timestamp format's
        # resolution (e.g. whole seconds) can't tell two rollovers apart -- a real risk here,
        # since a small configured max size can trigger several rollovers within one second.
        rotated_path = f'{self.baseFilename}.{timestamp}_{self._rollover_count}.zip'
        with zipfile.ZipFile(rotated_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(self.baseFilename, arcname=os.path.basename(self.baseFilename))

        if not self.delay:
            self.stream = self._open()


def initialize_logger(log_dir, filename):
    global logger

    # create directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # reset logging
    logger_name = get_config_value(None, config, 'Logging', 'Logger name', 'driving_system')
    logger = logging.getLogger(logger_name)
    handlers = logger.handlers[:]
    for handler in handlers:
        logger.removeHandler(handler)
        handler.close()

    file_log_level = getattr(logging, get_config_value(None, config, 'Logging', 'Log level file',
                                                       'DEBUG').upper())
    console_log_level = getattr(logging, get_config_value(None, config, 'Logging',
                                                          'Log level console', 'INFO').upper())

    # create logger
    logger = logging.getLogger(logger_name)

    # Get current date and time for logging
    date_time = datetime.now()
    timestamp_format = get_config_value(None, config, 'Logging', 'Timestamp format',
                                        '%Y-%m-%d_%H-%M-%S')
    timestamp = date_time.strftime(timestamp_format)

    # create file handler
    initial_part_log_filename = get_config_value(None, config, 'Logging',
                                                 'Initial part of log filename', 'log_')
    max_log_file_size_mb = float(get_config_value(None, config, 'Logging',
                                                  'Max log file size [MB]', 10))
    file_handler = ZipRotatingFileHandler(
        os.path.join(log_dir, initial_part_log_filename + f'{timestamp}_' + filename + '.txt'),
        mode='w', maxBytes=int(max_log_file_size_mb * 1024 * 1024), backupCount=0)

    # create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # create formatter and add it to the handlers
    formatter_compact = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - " +
                                          "%(funcName)s line %(lineno)d %(message)s")
    file_handler.setFormatter(formatter_compact)
    console_handler.setFormatter(formatter_compact)

    # add the handlers to the logger
    file_handler.setLevel(file_log_level)
    console_handler.setLevel(console_log_level)

    logger.setLevel(min(file_log_level, console_log_level))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def sync_logger(new_logger):
    """
    Points our shared logger at an externally provided (e.g. host application's) logger's
    handlers, level and propagation setting.

    Mutates the existing logger object in place instead of rebinding this module's 'logger'
    name to a different object: every consumer module calls get_logger() at each log call site
    rather than caching a reference, so it always reads whatever this mutates -- a plain rebind
    here would still work for them, but would not reach any (unlikely) caller that cached
    logging_config.logger itself instead of calling get_logger().

    Parameters:
        new_logger (logging.Logger): The externally provided logger to mirror.
    """

    logger.handlers = list(new_logger.handlers)
    logger.setLevel(new_logger.level)
    logger.propagate = new_logger.propagate
