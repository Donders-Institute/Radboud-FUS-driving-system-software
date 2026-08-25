# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.

Generic value-validation and piecewise-polynomial helpers shared by tus_protocol.py and
transducer_slot.py. Kept in their own module (rather than living in either of those two, or in
utils.py) specifically to avoid a circular import: tus_protocol.py constructs TransducerSlot
instances, so transducer_slot.py can't import from tus_protocol.py; utils.py is imported by
logging_config.py, so this module can't route through get_logger() the way tus_protocol.py's
functions used to and still be importable from there without a cycle. This module calls
get_logger() directly instead, same as tus_protocol.py/transducer_slot.py themselves do -- it has
no dependency on either of them.
"""

# Basic packages
import sys

# Miscellaneous packages
import json
import importlib.resources
import numpy as np
from scipy.interpolate import PPoly
from scipy import optimize

from fus_driving_systems.config.logging_config import get_logger


def validate_value(value, input_param, check_num, check_pos, check_nonzero, check_bool,
                   check_list=False):
    """
    Validates `value` based on specified checks, logs errors if conditions are not met, and exits
    if validation fails.

    Parameters:
        value (any): The value to check.
        input_param (str): Name of the parameter, used in error messages.
        check_num (bool): Checks if value is a number.
        check_pos (bool): Ensures value is non-negative.
        check_nonzero (bool): Ensures value is not zero.
        check_bool (bool): Checks if value is a boolean.
        check_list (bool): Checks if value is a list.

    Returns:
        bool: True if all checks pass; otherwise, logs errors and exits.
    """

    val_messages = []

    if check_list:
        if isinstance(value, list):
            for item in value:
                input_name = 'Items of ' + input_param
                val_messages = _check_parameter(val_messages, item, input_name, check_nonzero,
                                                check_num, check_pos, check_bool)

        else:
            val_messages.append(f'{input_param} should be a list.')
    else:
        val_messages = _check_parameter(val_messages, value, input_param, check_nonzero, check_num,
                                        check_pos, check_bool)

    if val_messages:
        for message in val_messages:
            get_logger().critical(message)
        sys.exit('Validation of input parameters failed.')

    return True


def _check_parameter(val_messages, value, input_name, check_nonzero, check_num, check_pos,
                     check_bool):
    """
    Checks a single value against specified conditions and appends error messages if any checks
    fail.

    Parameters:
        val_messages (list): List to append error messages to.
        value (any): The value to check.
        input_name (str): Name of the parameter, used in error messages.
        check_nonzero (bool): Ensures value is not zero.
        check_num (bool): Checks if value is a number.
        check_pos (bool): Ensures value is non-negative.
        check_bool (bool): Checks if value is a boolean.

    Returns:
        list: The updated list of error messages.
    """

    if check_nonzero and value == 0:
        val_messages.append(f'{input_name} is not allowed to be zero.')
    if check_num and not isinstance(value, (int, float)):
        val_messages.append(f'{input_name} should be a number.')
    if check_pos and value < 0:
        val_messages.append(f'{input_name} is not allowed to be negative.')
    if check_bool and not isinstance(value, bool):
        val_messages.append(f'{input_name} should be a boolean.')
    return val_messages


def extract_and_define_pp(json_dir, return_breaks=False):
    """
    This function loads polynomial coefficients and breakpoints from a JSON file that was exported
    from MATLAB. It handles potential format inconsistencies and converts the data to be compatible
    with SciPy's PPoly class.

    Parameters:
        json_path (str): Path to the JSON file containing the piecewise polynomial parameters.
        return_breaks (bool): If True, returns both the PPoly object and the breakpoints array.
            Default is False.

    Returns:
        scipy.interpolate.PPoly: A piecewise polynomial object that can be used for interpolation.
        numpy.ndarray, optional: Array of breakpoints if return_breaks=True.

    Raises:
        SystemExit: If xTransform is specified but not 'none', as transforms are not implemented.

    Notes:
        The function expects coefficients in the format used by MATLAB and converts them to
        the format expected by SciPy's PPoly constructor. The resulting PPoly has extrapolation
        disabled.
    """

    # Load the JSON file
    json_path = str(importlib.resources.files('fus_driving_systems').joinpath(json_dir))
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract only the necessary components
    try:
        x_transform = np.array(data['xTransform'])
        if x_transform.item() != 'none':
            message = 'A transform of the x value is expected, but not implemented.'
            get_logger().error(message)
            sys.exit(message)
    except KeyError:
        pass  # xTransform simply not being part of the file structure is the expected case.
    except TypeError:
        get_logger().warning('Data structure does not support this type of access.')
    except ValueError as ve:
        get_logger().warning(f'Error converting xTransform to numpy array: {ve}')
    except Exception as e:
        get_logger().warning(f'Unknown error checking for xTransform: {str(e)}')

    breaks = np.array(data['FitParams']['breaks'])
    coefs_data = data['FitParams']['coefs']

    order = len(coefs_data[0])

    # Calculate number of pieces from breaks
    pieces = len(breaks) - 1

    # Order/pieces are no longer logged here -- extract_and_define_pp() is a generic,
    # combo-agnostic utility with no way to dedupe across the repeated calls one combo's four
    # curves involve, or across a driving-system/transducer combo used again later (GitHub issue
    # #140). TransducerSlot._set_transducer() logs a single, deduplicated summary instead, once
    # per combo, alongside the transducer's own info.

    # Convert coefficients to the format expected by PPoly
    # SciPy expects shape (k, m) where k is order and m is pieces
    coefs = np.zeros((order, pieces))
    for i, coef_set in enumerate(coefs_data):
        # This assumes MATLAB provides coefficients in descending order
        coefs[:, i] = coef_set

    # Create the PPoly object
    pp = PPoly(coefs, breaks, extrapolate=False)

    if return_breaks:
        return pp, breaks

    return pp


def safe_evaluate_pp(pp, x_value):
    """
    Safely evaluate polynomial with range information
    """

    # Get domain boundaries
    x_min = pp.x[0]
    x_max = pp.x[-1]

    # Determine if value is outside range
    if x_value < x_min:
        return None, "below_range"
    if x_value > x_max:
        return None, "above_range"
    return pp(x_value), "in_range"


def find_x_for_y_in_pp(pp, y_value, x_min=None, x_max=None, tol=1e-6):
    """
    Find the x value corresponding to a given y value in a monotonic piecewise polynomial.

    Args:
        pp: Piecewise polynomial object (from scipy.interpolate)
        y_value: Target y value to find the corresponding x value for
        x_min: Minimum x value to consider (defaults to pp.x[0])
        x_max: Maximum x value to consider (defaults to pp.x[-1])
        tol: Tolerance for the root finding algorithm

    Returns:
        tuple: (x_value, status_code)
            - x_value: The x value corresponding to y_value, or None if not found
            - status_code: True if an x value was found, False otherwise
    """
    # Set default bounds if not provided
    if x_min is None:
        x_min = pp.x[0]
    if x_max is None:
        x_max = pp.x[-1]

    # Define the objective function: pp(x) - y_value = 0
    def objective(x):
        return pp(x) - y_value

    try:
        # Check if y_value is within the range of pp
        y_min = pp(x_min)
        y_max = pp(x_max)

        # Determine if pp is increasing or decreasing
        is_increasing = y_max > y_min

        # Check if y_value is within range
        if (is_increasing and (y_value < y_min or y_value > y_max)) or \
           (not is_increasing and (y_value > y_min or y_value < y_max)):
            return None, False

        # Use root finding to find the x value
        result = optimize.brentq(objective, x_min, x_max, xtol=tol)

        # Verify the result
        if abs(pp(result) - y_value) <= tol:
            return result, True
        return None, False

    except Exception as e:
        get_logger().error(f"Error finding x value: {e}")
        return None, False


def format_or_unavailable(value, unavailable_reason='out of calibrated range'):
    """
    Formats a calculated power/focus value for a log line, or a fallback string if it's None.

    Parameters:
        value (float or None): The value to format, e.g. slot.press or slot.volt.
        unavailable_reason (str): Why `value` is None, e.g. 'out of calibrated range' (default --
            a power value a curve lookup genuinely couldn't produce for the given input) or 'not
            yet configured' (a value that was reset and never set again, e.g. after a transducer
            change, on a slot no focus/power has been chosen for yet at all). Callers know which
            one applies for their own field; this function doesn't guess.

    Returns:
        str: value formatted to 2 decimal places, or a fallback string naming why if value is
        None.
    """

    return f'{value:.2f}' if value is not None else f'unavailable ({unavailable_reason})'
