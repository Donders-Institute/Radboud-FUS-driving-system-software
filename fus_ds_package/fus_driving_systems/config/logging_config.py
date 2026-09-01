# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Basic packages
import os
import sys

# Miscellaneous packages
from datetime import datetime
import faulthandler
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
# of crashing on a None attribute access. Private (leading underscore): every consumer, inside
# and outside this module, must go through get_logger() instead, since initialize_logger()
# rebinds this name to a different object later on -- a cached reference would go stale.
_logger = logging.getLogger(
    get_config_value(None, config, 'Logging', 'Logger name', 'driving_system'))

# A dedicated child logger (dotted-name hierarchy, e.g. 'driving_system.measurements') for the
# high-volume per-pulse/per-channel hardware measurements IGT's ExecListener.onPulseResult()
# receives -- kept off _logger's own handlers so they don't drown out the info/debug files in
# noise (thousands of lines for a protocol with many repetitions). initialize_logger() gives it
# its own file handler and sets propagate=False, so it's genuinely separate there; sync_logger()
# (the host-application integration point, e.g. SonoRover One) deliberately leaves it alone --
# with no handlers of its own and propagate left at its default (True), records logged to it
# bubble up to _logger's own handlers instead, i.e. wherever the host's own logger sends them --
# matching this package's previous behavior (get_logger().debug(...)) for that integration path,
# since the host has no knowledge of this package's own file-splitting scheme.
_measurements_logger = logging.getLogger(
    get_config_value(None, config, 'Logging', 'Logger name', 'driving_system') + '.measurements')

# The timestamped subfolder initialize_logger() creates for the main FDS log file, exposed via
# get_session_log_dir() below so other log files created later in the same session (e.g. the
# faulthandler log and IGT.connect()'s native IGT log, see enable_crash_detection() below) land
# in that same folder instead of each ending up loose alongside log_dir -- otherwise files from
# one session couldn't be recognized/shared together as a single unit (e.g. with IGT for a bug
# report, GitHub issue #126).
_session_log_dir = None  # pylint: disable=invalid-name

# The `filename` argument most recently passed to initialize_logger() (e.g. "standalone_plain"),
# exposed via get_session_log_filename() below so IGT.connect() can name its own native log
# consistently with the main FDS log by default, instead of falling back to a generic,
# session-independent config default (see connect()'s own log_name resolution).
_session_log_filename = None  # pylint: disable=invalid-name

# The open file faulthandler is currently targeting, kept here (not e.g. an instance attribute
# on IGT) since faulthandler itself is a single, process-wide facility -- there is only ever
# one target, no matter how many driving-system objects get constructed. Also doubles as the
# is_crash_detection_enabled() flag: None until enable_crash_detection() has run once.
_faulthandler_file = None  # pylint: disable=invalid-name


def get_logger():
    """
    Returns the currently active shared logger.

    Modules that need to log should call this at each log call site (e.g.
    'get_logger().info(...)') instead of caching the return value at their own import time:
    initialize_logger()/sync_logger() can (re)point the shared logger at a different or
    reconfigured object later on, and a function call always reads the current value, so
    callers never end up holding a stale reference from before that happened.

    Returns:
        logging.Logger: The currently active shared logger.
    """

    return _logger


def get_measurements_logger():
    """
    Returns the currently active shared logger for high-volume hardware measurements (e.g.
    IGT's per-pulse/per-channel onPulseResult() data) -- see the module-level comment above
    _measurements_logger for why this is a separate logger rather than get_logger() itself.
    For a host application using sync_logger() instead of initialize_logger(), see that
    function's own docstring for how to keep this data out of its own main log too.

    Returns:
        logging.Logger: The currently active shared measurements logger.
    """

    return _measurements_logger


def get_session_log_filename():
    """
    Returns the `filename` argument most recently passed to initialize_logger(), or None if
    initialize_logger() hasn't run yet in this process (e.g. a host application using
    sync_logger() instead).

    Returns:
        str or None: The current session's FDS log filename (see the module-level comment above
        _session_log_filename), or None if unavailable.
    """

    return _session_log_filename


def get_session_log_dir():
    """
    Returns the timestamped session folder created by the most recent initialize_logger()
    call, or None if initialize_logger() hasn't run yet in this process.

    Returns:
        str or None: Absolute path to the shared session log folder (see the module-level
        comment above _session_log_dir), or None if unavailable.
    """

    return _session_log_dir


def is_crash_detection_enabled():
    """
    Returns whether enable_crash_detection() has already run once in this process.

    Returns:
        bool: True if faulthandler has already been enabled via enable_crash_detection().
    """

    return _faulthandler_file is not None


def enable_crash_detection(log_dir, target_dir):
    """
    Enables faulthandler and checks for evidence that a previous process crashed unexpectedly
    (GitHub issue #126) -- the whole-package hook for this: called by both initialize_logger()
    and sync_logger(), the two entry points host code uses to set up logging, so every driving
    system benefits regardless of which one a script/host application (e.g. SonoRover One,
    which uses sync_logger()) happens to call. A no-op if already enabled this process (see
    is_crash_detection_enabled()) -- calling this more than once (e.g. IGT.__init__'s own
    fallback call, see there) never re-triggers the crash check or retargets faulthandler.

    faulthandler only writes to its target file when a fatal signal (e.g. a native segfault)
    actually occurs -- a session that exits normally leaves the file empty/untouched. Each
    session gets its own, uniquely timestamped target_dir (see get_session_log_dir()), so a
    previous session's evidence can't be found by just checking "the same path as this
    session" -- a persistent, cross-process pointer file at log_dir's stable root (unlike
    target_dir, this doesn't change between sessions) records which target_dir the previous
    session actually used.

    Parameters:
        log_dir (str): Stable root log directory -- where the cross-session pointer file and
            kernel-death counter live. Must stay the same across sessions for crash detection
            to find the previous session's evidence.
        target_dir (str): Where THIS session's faulthandler log should be written (typically
            the current session's timestamped subfolder, or log_dir itself if none exists).
    """

    global _faulthandler_file

    if _faulthandler_file is not None:
        return

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    filename = get_config_value(None, config, 'Logging', 'Filename faulthandler',
                                'faulthandler_output.log')
    pointer_filename = get_config_value(None, config, 'Logging', 'Filename session pointer',
                                        '.last_session_log_dir')
    pointer_path = os.path.join(log_dir, pointer_filename)

    try:
        _check_previous_session_crash(log_dir, pointer_path, filename)
    except Exception as e:
        get_logger().debug(f'Could not check for a previous-session crash: {e}')

    with open(pointer_path, 'w', encoding='utf-8') as f:
        f.write(target_dir)

    # BUGFIX: faulthandler writes (via a C-level signal handler) at whatever point in the
    # future a fatal signal occurs -- its target file must stay open for that entire time. A
    # 'with' block here would close the file (and its underlying OS file descriptor) as soon
    # as this line finished, silently disabling every future write: faulthandler.is_enabled()
    # would keep reporting True afterwards, but a probe write to the closed descriptor raises
    # ValueError -- confirmed with a standalone repro before writing this. Kept open via the
    # module-level _faulthandler_file instead, deliberately never closed (process exit is what
    # eventually releases it).
    fault_handler_path = os.path.join(target_dir, filename)
    _faulthandler_file = open(  # pylint: disable=consider-using-with
        fault_handler_path, "w", encoding='utf-8')
    faulthandler.enable(file=_faulthandler_file)


def _check_previous_session_crash(log_dir, pointer_path, filename):
    """
    Detects and counts likely kernel-death crashes (GitHub issue #126) left behind by a
    previous session/process.

    A non-empty faulthandler log found at the location the pointer file records is evidence
    that session crashed before it ever got the chance to shut down cleanly -- checking
    "target_dir" (this session's own, brand new folder) instead would never find anything,
    since it's unique to this session; that was a real, since-fixed bug. Copied (not deleted,
    and not moved -- see below) alongside a persistent counter, so the crash frequency can be
    tracked over time and the archived output attached to a bug report for IGT.

    Parameters:
        log_dir (str): Stable root log directory -- where the kernel-death counter lives.
        pointer_path (str): Path to the pointer file recording the previous session's own
            target_dir, written by the previous enable_crash_detection() call.
        filename (str): Configured faulthandler log filename (basename only).
    """

    if not os.path.exists(pointer_path):
        return

    with open(pointer_path, encoding='utf-8') as f:
        previous_target_dir = f.read().strip()

    previous_fault_handler_path = os.path.join(previous_target_dir, filename)
    if not os.path.exists(previous_fault_handler_path):
        return

    with open(previous_fault_handler_path, encoding='utf-8') as f:
        previous_content = f.read()

    if not previous_content.strip():
        return

    count_filename = get_config_value(None, config, 'Logging', 'Filename kernel death counter',
                                      'kernel_death_count.txt')
    count_path = os.path.join(log_dir, count_filename)
    count = 0
    if os.path.exists(count_path):
        with open(count_path, encoding='utf-8') as f:
            count = int(f.read().strip())
    count += 1

    timestamp_format = get_config_value(None, config, 'Logging', 'Timestamp format',
                                        '%Y-%m-%d_%H-%M-%S')
    timestamp = datetime.now().strftime(timestamp_format)
    # count is included so two crashes within the same second (timestamp_format's precision)
    # don't overwrite each other's archived output. Copied via a fresh write rather than
    # os.replace()/os.rename(): previous_fault_handler_path may still have an open handle (this
    # process's own faulthandler file, kept open deliberately -- see enable_crash_detection --
    # if it happens to be the same session, or a previous process's), and Windows refuses to
    # rename a file that has any open handle, even though reopening/truncating it is fine.
    archived_path = f'{previous_fault_handler_path}.{timestamp}_{count}.crash'
    with open(archived_path, 'w', encoding='utf-8') as f:
        f.write(previous_content)

    with open(count_path, 'w', encoding='utf-8') as f:
        f.write(str(count))

    get_logger().warning(
        'Previous session appears to have crashed unexpectedly (possible kernel death, ' +
        'see GitHub issue #126) -- its faulthandler output was archived to ' +
        f'{archived_path}. This is occurrence number {count}.')


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
    global _logger, _measurements_logger, _session_log_dir, _session_log_filename

    # reset logging
    logger_name = get_config_value(None, config, 'Logging', 'Logger name', 'driving_system')
    _logger = logging.getLogger(logger_name)
    _measurements_logger = logging.getLogger(logger_name + '.measurements')
    for logger in (_logger, _measurements_logger):
        handlers = logger.handlers[:]
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()

    file_log_level = getattr(logging, get_config_value(None, config, 'Logging', 'Log level file',
                                                       'DEBUG').upper())
    console_log_level = getattr(logging, get_config_value(None, config, 'Logging',
                                                          'Log level console', 'INFO').upper())

    # Get current date and time for logging
    date_time = datetime.now()
    timestamp_format = get_config_value(None, config, 'Logging', 'Timestamp format',
                                        '%Y-%m-%d_%H-%M-%S')
    timestamp = date_time.strftime(timestamp_format)

    # All log files for this session -- this FDS log, plus the faulthandler log and
    # IGT.connect()'s native IGT log (see get_session_log_dir()) -- live together in one
    # timestamped subfolder of log_dir, so the whole session can be found/shared as a single
    # unit (e.g. with IGT for a bug report, GitHub issue #126) instead of being scattered flat
    # inside log_dir alongside files from other sessions. mkdir(parents=True) also creates
    # log_dir itself if it didn't already exist.
    _session_log_dir = os.path.join(log_dir, f'{timestamp}_FDS_logs')
    Path(_session_log_dir).mkdir(parents=True, exist_ok=True)
    _session_log_filename = filename

    enable_crash_detection(log_dir, _session_log_dir)

    initial_part_log_filename = get_config_value(None, config, 'Logging',
                                                 'Initial part of log filename', 'log_')
    max_log_file_size_mb = float(get_config_value(None, config, 'Logging',
                                                  'Max log file size [MB]', 10))
    max_bytes = int(max_log_file_size_mb * 1024 * 1024)

    def _make_file_handler(infix, level, delay=False):
        handler = ZipRotatingFileHandler(
            os.path.join(_session_log_dir, initial_part_log_filename + infix + filename + '.txt'),
            mode='w', maxBytes=max_bytes, backupCount=0, delay=delay)
        handler.setLevel(level)
        return handler

    # Three files: 'info' mirrors the console (same level, same clean researcher-facing content
    # -- what's about to run, what actually ran); 'debug' is everything (the file to always
    # share when reporting a problem, GitHub issue #126); 'measurements' is IGT's high-volume
    # per-pulse/per-channel hardware data (see _measurements_logger's own comment), kept
    # separate so it doesn't drown out 'debug' in noise. 'measurements' uses delay=True (the
    # underlying logging.FileHandler defers actually opening/creating the file until its first
    # emit()) since this package is manufacturer-agnostic here -- it has no way to know in
    # advance whether the driving system used this session will ever write to it (only IGT's
    # onPulseResult() does, see get_measurements_logger()) -- so a session using e.g. Sonic
    # Concepts or CITRUS never gets an empty, always-unused 'measurements' file on disk.
    info_file_handler = _make_file_handler('info_', console_log_level)
    debug_file_handler = _make_file_handler('debug_', file_log_level)
    measurements_file_handler = _make_file_handler('measurements_', file_log_level, delay=True)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_log_level)

    formatter_compact = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - " +
                                          "%(funcName)s line %(lineno)d %(message)s")
    for handler in (info_file_handler, debug_file_handler, measurements_file_handler,
                    console_handler):
        handler.setFormatter(formatter_compact)

    _logger.setLevel(min(file_log_level, console_log_level))
    _logger.addHandler(console_handler)
    _logger.addHandler(info_file_handler)
    _logger.addHandler(debug_file_handler)

    # Kept off _logger's own handlers (see _measurements_logger's own module-level comment) --
    # propagate=False so records logged here don't also land in the three handlers above.
    _measurements_logger.setLevel(file_log_level)
    _measurements_logger.addHandler(measurements_file_handler)
    _measurements_logger.propagate = False

    return _logger


def sync_logger(new_logger, log_dir=None):
    """
    Points our shared logger at an externally provided (e.g. host application's) logger's
    handlers, level and propagation setting.

    Mutates the existing logger object in place instead of rebinding this module's shared
    logger to a different object: every consumer module calls get_logger() at each log call
    site rather than caching a reference, so it always reads whatever this mutates -- a plain
    rebind here would still work for them, but would not reach any (unlikely) caller that
    cached the logger object itself instead of calling get_logger().

    Also enables crash detection (GitHub issue #126) if it hasn't already been enabled this
    process -- the other of the two whole-package hooks (see enable_crash_detection()),
    covering host applications (e.g. SonoRover One) that use sync_logger() instead of
    initialize_logger() to set up logging.

    _measurements_logger (see get_measurements_logger()) is deliberately left untouched here --
    no handlers of its own, propagate at its default True -- so its high-volume per-pulse/
    per-channel records keep bubbling up into new_logger's own handlers, matching this
    package's pre-split behavior for a host application that has no knowledge of the file
    split initialize_logger() does. If the host wants this data kept out of its own main log
    the way initialize_logger() keeps it out of the debug file, it can attach its own handler
    directly to logging.getLogger(new_logger.name + '.measurements') and set that logger's own
    propagate = False -- the same mechanism initialize_logger() uses internally, just applied
    from the host's side of the split instead of this package's.

    Parameters:
        new_logger (logging.Logger): The externally provided logger to mirror.
        log_dir (str, optional): Where the faulthandler log and its persistent, cross-session
            bookkeeping should live if crash detection hasn't already been enabled by
            initialize_logger(). Defaults to config 'Logging'/'Temporary logging path'.
    """

    _logger.handlers = list(new_logger.handlers)
    _logger.setLevel(new_logger.level)
    _logger.propagate = new_logger.propagate

    if log_dir is None:
        log_dir = get_config_value(None, config, 'Logging', 'Temporary logging path', 'C:\\Temp')

    enable_crash_detection(log_dir, log_dir)
