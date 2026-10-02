# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.
"""

from PySide6.QtWidgets import QApplication, QMessageBox

from fus_driving_systems.exceptions import (FDSConfigError, FDSHardwareError, FDSInternalError,
                                            FDSSafetyError, FDSValidationError)


def show_fds_error(parent, exc):
    """
    Shows exc in a QMessageBox appropriate to its own FDSError subtype:
    - FDSSafetyError gets a distinct, more prominent critical dialog with no "proceed anyway"
      option; a safety check must never be something a researcher can click through by accident.
    - FDSInternalError is framed explicitly as a bug in the software, not the researcher's own
      input, with a button to copy the details for a bug report (see _show_internal_error()).
    - FDSValidationError falls back to a plain warning here (expected, frequent, self-correcting
      input mistakes are better shown inline next to the offending field where a caller has one,
      e.g. ApplyPanel's own error_label; this function is only for callers with no such field to
      show it against, e.g. a menu action).
    - FDSHardwareError/FDSConfigError each get a critical dialog framed around their own likely
      cause (a connection/hardware problem, or a ds_config.ini setup problem, respectively).

    FDSSafetyError/FDSInternalError are checked before the plainer FDSValidationError/
    FDSHardwareError/FDSConfigError branches, so a broad `except FDSError:` still gets the
    subtype-correct dialog instead of always falling into a generic one.

    Every branch surfaces str(exc) verbatim: this codebase's own exception messages are already
    written to be end-user-readable, not just log-oriented.

    Parameters:
        parent (QWidget): Parent widget for the dialog (may be None).
        exc (FDSError): The exception to display.
    """

    if isinstance(exc, FDSSafetyError):
        QMessageBox.critical(parent, "Safety check failed", str(exc))
    elif isinstance(exc, FDSInternalError):
        _show_internal_error(parent, exc)
    elif isinstance(exc, FDSValidationError):
        QMessageBox.warning(parent, "Invalid input", str(exc))
    elif isinstance(exc, FDSHardwareError):
        QMessageBox.critical(parent, "Hardware error", str(exc))
    elif isinstance(exc, FDSConfigError):
        QMessageBox.critical(parent, "Configuration error", f"{exc}\n\nCheck ds_config.ini.")
    else:
        QMessageBox.critical(parent, "Error", str(exc))


def _show_internal_error(parent, exc):
    """FDSInternalError means a bug in this software, not the researcher's own input, framed
    explicitly as such, with a button to copy the details for a bug report."""

    box = QMessageBox(QMessageBox.Icon.Critical, "Internal error",
                      "This is a bug in the software, not your input. Please report it, "
                      f"including the details below.\n\n{exc}", parent=parent)
    copy_button = box.addButton("Copy details", QMessageBox.ButtonRole.ActionRole)
    box.addButton(QMessageBox.StandardButton.Ok)
    box.exec()
    if box.clickedButton() is copy_button:
        QApplication.clipboard().setText(str(exc))
