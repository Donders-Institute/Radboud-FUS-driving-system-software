# -*- mode: python ; coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

Builds the standalone GUI executable:
    pyinstaller fus_ds_gui.spec
Produces dist/FDS_GUI/ (run FDS_GUI.exe inside it). onedir, not onefile: faster startup,
and an unpacked folder is far easier to inspect if unifus.pyd (see below) fails to load on a
real driving system's PC than a single opaque binary would be.
"""

import glob
import os

from PyInstaller.utils.hooks import copy_metadata

_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
_REPO_ROOT = os.path.join(_SPEC_DIR, '..')
_DS_PACKAGE_ROOT = os.path.join(_REPO_ROOT, 'fus_ds_package')
_DS_PACKAGE = os.path.join(_DS_PACKAGE_ROOT, 'fus_driving_systems')


def _non_python_files(src_dir, dest_dir):
    """(source, dest) pairs for every non-.py file under src_dir, recursively, keeping its
    subdirectory structure under dest_dir. fus_driving_systems and fus_ds_gui are both editable
    installs (pip install -e): PyInstaller's static analysis follows their real .py modules fine
    once fus_ds_package is on pathex (see Analysis() below), but data files (.ini/.json/images)
    aren't reachable through import analysis at all, so they're collected here by hand instead."""

    pairs = []
    for path in glob.glob(os.path.join(src_dir, '**', '*'), recursive=True):
        if os.path.isfile(path) and not path.endswith('.py'):
            rel_dir = os.path.relpath(os.path.dirname(path), src_dir)
            pairs.append((path, os.path.join(dest_dir, rel_dir)))
    return pairs


datas = (
    _non_python_files(os.path.join(_SPEC_DIR, 'fus_ds_gui', 'resources'),
                       os.path.join('fus_ds_gui', 'resources'))
    + _non_python_files(os.path.join(_REPO_ROOT, 'example_protocols'), 'example_protocols')
    + _non_python_files(os.path.join(_DS_PACKAGE, 'config'),
                         os.path.join('fus_driving_systems', 'config'))
    + _non_python_files(os.path.join(_DS_PACKAGE, 'igt', 'config'),
                         os.path.join('fus_driving_systems', 'igt', 'config'))
    # MainWindow's own window title and logging_config's startup log line both read these
    # packages' installed version via importlib.metadata, which needs their dist-info present
    # in the frozen build; pathex above only makes their .py modules discoverable, not this.
    + copy_metadata('fus_ds_gui')
    + copy_metadata('fus_driving_systems')
)

# The IGT native extension: a compiled .pyd, not something Analysis can trace through imports.
binaries = [
    (os.path.join(_DS_PACKAGE, 'igt', 'unifus.pyd'), os.path.join('fus_driving_systems', 'igt')),
]

a = Analysis(
    [os.path.join(_SPEC_DIR, 'fus_ds_gui', 'app.py')],
    # fus_driving_systems is an editable install (PEP 660): site-packages only has a redirect
    # finder, not a real package directory, so plain Analysis() treats it as missing entirely.
    # Pointing pathex at its actual source directory makes it discoverable like a normal package.
    pathex=[_SPEC_DIR, _DS_PACKAGE_ROOT],
    binaries=binaries,
    datas=datas,
    # The dev venv has other Qt bindings installed (pulled in transitively by unrelated tools,
    # not by this app); PyInstaller refuses to bundle more than one, so the ones this app never
    # imports are excluded explicitly rather than left to conflict with PySide6.
    excludes=['PyQt5', 'PyQt6', 'PySide2'],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FDS_GUI',
    console=False,
    icon=os.path.join(_SPEC_DIR, 'fus_ds_gui', 'resources', 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='FDS_GUI',
)
