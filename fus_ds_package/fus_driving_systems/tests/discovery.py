# -*- coding: utf-8 -*-
"""
Shared helper for locating the in-package conversion-data directory and
discovering which calibration files exist there.

Kept separate from conftest.py so that both conftest.py (for fixtures)
and test modules (for building parametrize lists at collection time)
can import it directly, without relying on importing from "conftest"
as a module.
"""
import importlib.resources
from pathlib import Path

import numpy as np

# Subpath of the config data within the package -- adjust if needed
CONVERSION_DATA_SUBPATH = ("igt", "config", "conversion_data")


def resolve_conversion_data_dir() -> Path:
    """
    Locates the directory containing conversion-data JSON files inside
    the installed fus_driving_systems package.
    """
    try:
        base = importlib.resources.files("fus_driving_systems")
        data_dir = base.joinpath(*CONVERSION_DATA_SUBPATH)
        data_dir_path = Path(str(data_dir))
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "Could not find 'fus_driving_systems'. Is the package "
            "installed in this environment? (pip install -e .)"
        ) from e

    if not data_dir_path.exists():
        raise FileNotFoundError(
            f"Conversion data directory not found at {data_dir_path}. "
            f"Does CONVERSION_DATA_SUBPATH ({CONVERSION_DATA_SUBPATH}) "
            f"still match the current package structure?"
        )
    return data_dir_path


def manual_pp_eval(x_values, breaks, coefs):
    """
    Evaluates a piecewise polynomial by hand, directly from breaks/coefs,
    using the documented MATLAB pp convention: coefficients ordered from
    highest to lowest degree, local variable dx = x - breaks[segment].

    This is deliberately independent of any optional convenience arrays
    stored alongside FitParams in the JSON (e.g. 'data', 'focusCurvature',
    'powerCurvature'), since those can be stale snapshots from an earlier
    fit and are not guaranteed to stay in sync with FitParams itself.
    breaks/coefs are the only values the Python loader actually reads,
    so they're the only canonical source of truth to test against.
    """
    x_values = np.atleast_1d(np.asarray(x_values, dtype=float))
    breaks = np.asarray(breaks, dtype=float)
    y_values = np.empty_like(x_values)

    n_pieces = len(coefs)
    for i, x in enumerate(x_values):
        # Find which segment x falls in; clip so the final breakpoint
        # itself still uses the last segment rather than falling outside.
        segment = np.searchsorted(breaks, x, side="right") - 1
        segment = int(np.clip(segment, 0, n_pieces - 1))
        dx = x - breaks[segment]
        y_values[i] = np.polyval(coefs[segment], dx)

    return y_values


def discover_calibration_files():
    """
    Scans the conversion-data directory and groups filenames by curve
    type, based on filename suffix/prefix pattern rather than a
    hardcoded per-transducer serial number list. This means files for
    every transducer currently in the package are picked up
    automatically, as long as the naming convention below holds.

    Returns a dict with keys 'multi_piece' and 'single_piece', each a
    sorted list of filenames (not full paths).
    """
    data_dir = resolve_conversion_data_dir()
    all_files = sorted(p.name for p in data_dir.glob("*.json"))

    multi_piece = [
        f for f in all_files
        if f.endswith("equalizationCurveFitExport.json")
        or f.endswith("focusCurveFitExport.json")
    ]
    single_piece = [
        f for f in all_files
        if f.endswith("powerCurveFitExport.json")
        or f.startswith("voltageCurveFit")
    ]

    return {"multi_piece": multi_piece, "single_piece": single_piece}