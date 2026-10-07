# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.

Every exception this package raises intentionally (as opposed to a bug surfacing as an unrelated
builtin exception), replacing this package's former sys.exit() calls. Every message this package
raises with is also logged at CRITICAL, prefixed with the exception's class name, via
raise_logged() at the same call site, so a failure always ends up in the session's debug log
file regardless of what the caller does with the exception.
"""

from typing import NoReturn


class FDSError(Exception):
    """Base class for every exception this package raises intentionally. Catch this alone when
    the specific category doesn't matter."""


class FDSValidationError(FDSError):
    """A caller gave an invalid, out-of-range, unavailable, or malformed value/option to a
    public setter or method."""


class FDSSafetyError(FDSError):
    """A value would be unsafe to actually send to hardware if allowed through, e.g. exceeds the
    configured maximum pressure, or amplitude over 100%. Kept distinct from FDSValidationError so
    a caller can never accidentally swallow this the same way as an ordinary input mistake."""


class FDSHardwareError(FDSError):
    """Something failed talking to external hardware, an SDK, or the OS: a connection was lost,
    a native SDK call failed, or a resource expected to exist on disk didn't."""


class FDSConfigError(FDSError):
    """The static configuration -- ds_config.ini, a transducer's .ini steer file, or a
    calibration curve JSON -- is missing or malformed."""


class FDSInternalError(FDSError):
    """An internal invariant was violated. Indicates a bug in this package itself, not something
    caused by caller input, hardware, or configuration."""


def log_critical(exc_class, message):
    """Logs message at CRITICAL, prefixed with the name of exc_class, the exception about to be
    raised with it. For the rare site that logs several messages before raising one exception."""

    # Imported here: logging_config imports utils, which imports this module.
    from fus_driving_systems.config.logging_config import get_logger  # pylint: disable=C0415

    get_logger().critical(f'{exc_class.__name__}: {message}', stacklevel=2)


def raise_logged(exc_class, message, cause=None) -> NoReturn:
    """Logs message at CRITICAL, prefixed with the name of exc_class (so the log names the kind
    of failure without that name being repeated by hand at every call site), then raises
    exc_class(message), chained to cause if one is given. The log record shows the caller's own
    module, function and line."""

    from fus_driving_systems.config.logging_config import get_logger  # pylint: disable=C0415

    exc = exc_class(message)
    get_logger().critical(f'{exc_class.__name__}: {message}', stacklevel=2)
    if cause is not None:
        raise exc from cause
    raise exc
