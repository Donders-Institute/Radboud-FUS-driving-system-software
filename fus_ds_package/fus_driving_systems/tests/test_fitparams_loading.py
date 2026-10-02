# -*- coding: utf-8 -*-
"""
Regression tests for FitParams JSON loading (breaks/coefs -> PPoly).

Uses the conversion-data JSON files as they actually exist inside the
fus_driving_systems package (via the fixtures in conftest.py), so
there's no standalone/duplicated test copy that could drift out of
sync with the real config.

File lists are discovered dynamically (see discovery.py) by matching
filename patterns rather than hardcoding each transducer's serial
number, so calibration files for every transducer currently in the
package are picked up automatically.

IMPORTANT: these tests deliberately do NOT compare against the
optional 'data'/'focusCurvature'/'powerCurvature' arrays some files
carry alongside FitParams. Those are convenience snapshots generated
at fit time and can go stale relative to FitParams itself (e.g. after
a re-fit that didn't regenerate them) -- for some transducers they've
been observed to disagree with FitParams by a non-trivial amount. The
only thing the Python loader actually reads is FitParams.breaks/coefs,
so that's the only canonical source of truth these tests validate
against, via an independent manual polynomial evaluation
(_discovery.manual_pp_eval).
"""
import json

import numpy as np
import pytest

from fus_driving_systems import calc_utils

from discovery import discover_calibration_files, manual_pp_eval

_discovered = discover_calibration_files()
MULTI_PIECE_FILES = _discovered["multi_piece"]
SINGLE_PIECE_FILES = _discovered["single_piece"]
ALL_FILES = MULTI_PIECE_FILES + SINGLE_PIECE_FILES

# Sanity check: with 6 transducers x 2 multi-piece files each (equalization
# + focus), we expect 12 multi-piece files. Adjust this number if the
# transducer count changes, so a silently-missing file gets caught here
# instead of just quietly not being tested.
EXPECTED_MULTI_PIECE_COUNT = 12


def test_expected_number_of_multipiece_files_discovered():
    """
    Guards against a naming mismatch or a missing transducer silently
    shrinking test coverage: if this fails, either a transducer's
    calibration files aren't following the expected naming pattern, or
    EXPECTED_MULTI_PIECE_COUNT needs updating after adding/removing a
    transducer.
    """
    assert len(MULTI_PIECE_FILES) == EXPECTED_MULTI_PIECE_COUNT, (
        f"Expected {EXPECTED_MULTI_PIECE_COUNT} multi-piece files, "
        f"found {len(MULTI_PIECE_FILES)}: {MULTI_PIECE_FILES}"
    )


@pytest.mark.parametrize("filename", ALL_FILES)
def test_loader_matches_manual_polynomial_evaluation(filename, load_json, resource_path):
    """
    Core regression test, for every discovered file (multi- and
    single-piece alike): builds a pp via the real loader, and compares
    it against a manual, independent evaluation computed directly from
    FitParams.breaks/coefs (see manual_pp_eval). This is what actually
    catches a coefficient-order bug, regardless of how many pieces a
    fit has, and without depending on any optional convenience arrays
    that may not be present or may have gone stale.
    """
    raw = load_json(filename)
    pp, breaks = calc_utils.extract_and_define_pp(resource_path(filename), return_breaks=True)

    coefs = raw["FitParams"]["coefs"]
    test_points = np.linspace(breaks[0], breaks[-1], 25)

    y_manual = manual_pp_eval(test_points, breaks, coefs)
    y_pp = pp(test_points)

    np.testing.assert_allclose(y_pp, y_manual, rtol=1e-6, atol=1e-8)


def test_safe_evaluate_pp_matches_direct_call(load_json, resource_path):
    """
    Checks that the 'safe' wrapper agrees with a direct pp() call
    within the valid domain, for both a multi-piece and a single-piece
    (linear/quadratic) fit.

    NOTE: this only verifies that safe_evaluate_pp is internally
    consistent with the already-constructed pp object -- it does NOT
    independently verify the coefficient order/convention itself.
    Both sides of the comparison use the same pp object, so if pp is
    built incorrectly (e.g. reversed coefs), this test would still
    pass since both sides would be equally wrong. The coefficient
    convention itself is covered by the test above, which compares
    against an independent source (manual polynomial evaluation).
    """
    for filename in ALL_FILES:
        pp, breaks = calc_utils.extract_and_define_pp(resource_path(filename), return_breaks=True)
        x_mid = (min(breaks) + max(breaks)) / 2

        y_direct = pp(x_mid)
        y_safe, status = calc_utils.safe_evaluate_pp(pp, x_mid)

        assert status, f"safe_evaluate_pp reported failure in-domain for {filename}"
        np.testing.assert_allclose(y_safe, y_direct, rtol=1e-6, atol=1e-8)


def test_loader_does_not_reverse_coefficients_for_a_synthetic_single_piece_fit(tmp_path):
    """
    Regression guard for the removed 'reverse coefficients for single-piece
    fits' special case (commit 3d1a604). The parametrized test above already
    exercises every real single-piece file in the package, but a coincidence
    in those real files' coefficients could theoretically mask a
    reintroduced reversal bug. This fixture is deliberately asymmetric
    (forward vs. reversed coefficient order give clearly different values,
    even at the boundary), so a regression fails loudly here regardless of
    what the real calibration files happen to contain.

    Passing an absolute path as json_dir works here because
    extract_and_define_pp resolves it via
    importlib.resources.files('fus_driving_systems').joinpath(json_dir) --
    joinpath() treats an absolute argument as absolute and discards the
    package base, so this never touches the real package data directory.
    """
    breaks = [0.0, 10.0]
    coefs = [[1.0, 0.0, 5.0]]  # descending order: 1*dx^2 + 0*dx + 5
    fit_params = {
        "xTransform": "none",
        "FitParams": {"breaks": breaks, "coefs": coefs},
    }
    json_path = tmp_path / "synthetic_single_piece.json"
    json_path.write_text(json.dumps(fit_params))

    pp = calc_utils.extract_and_define_pp(str(json_path))

    test_points = np.linspace(breaks[0], breaks[-1], 25)
    y_pp = pp(test_points)
    y_manual = manual_pp_eval(test_points, np.array(breaks), coefs)
    np.testing.assert_allclose(y_pp, y_manual, rtol=1e-6, atol=1e-8)

    # Extra-explicit boundary check: at dx=0 the constant term must be 5,
    # not 1 (which is what a reversed-coefficient bug would produce).
    assert pp(0.0) == pytest.approx(5.0)
