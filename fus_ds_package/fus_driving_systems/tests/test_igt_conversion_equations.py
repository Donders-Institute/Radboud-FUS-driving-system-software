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
If you use this kit in your research or project, please include the following attribution:
Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont
(Image Guided Therapy, Pessac, France) (2024), Radboud FUS measurement kit (version 1.0),
https://github.com/Donders-Institute/Radboud-FUS-measurement-kit
"""

import os
import matplotlib.pyplot as plt
import numpy as np

from fus_driving_systems.config.logging_config import initialize_logger

log_dir = "C://Temp"
filename = "test_igt_conversion_equations"
logger = initialize_logger(log_dir, filename)


from fus_driving_systems import sequence


def test_pp_conversions(pp_file):
    """
    Comprehensive test of both forward and inverse PP evaluations.

    Args:
        pp_file: Path to JSON file containing PP data
    """
    logger.info(f"Testing PP conversions with file: {pp_file}")

    # Load the PP
    pp, breaks = sequence.extract_and_define_pp(pp_file, return_breaks=True)
    if pp is None:
        logger.error("Failed to load PP")
        return

    x_min, x_max = min(breaks), max(breaks)
    logger.info(f"PP domain: [{x_min}, {x_max}]")

    # Test forward evaluation (x to y)
    logger.info("Testing forward evaluation (x to y)")
    test_x_values = np.linspace(x_min, x_max, 5)
    for x in test_x_values:
        y, status = sequence.safe_evaluate_pp(pp, x)
        logger.info(f"x = {x:.2f} -> y = {y:.2f}, status: {status}")

    # Test boundary conditions
    logger.info("Testing boundary conditions")
    y, status = sequence.safe_evaluate_pp(pp, x_min - 1)
    logger.info(f"Below range: x = {x_min - 1:.2f} -> status: {status}")
    y, status = sequence.safe_evaluate_pp(pp, x_max + 1)
    logger.info(f"Above range: x = {x_max + 1:.2f} -> status: {status}")

    # Test inverse evaluation (y to x)
    logger.info("Testing inverse evaluation (y to x)")
    # Get y range
    y_values = [pp(x) for x in np.linspace(x_min, x_max, 100)]
    y_min, y_max = min(y_values), max(y_values)
    logger.info(f"PP range: [{y_min:.2f}, {y_max:.2f}]")

    test_y_values = np.linspace(y_min, y_max, 5)
    for y in test_y_values:
        x, status = sequence.find_x_for_y_in_pp(pp, y)
        if status:
            # Verify by evaluating the result
            y_check, _ = sequence.safe_evaluate_pp(pp, x)
            error = abs(y - y_check)
            logger.info(f"y = {y:.2f} -> x = {x:.2f}, verification error: {error:.6f}")
        else:
            logger.warning(f"Failed to find x for y = {y:.2f}")

    # Test boundary conditions for inverse
    logger.info("Testing inverse boundary conditions")
    x, status = sequence.find_x_for_y_in_pp(pp, y_min - 1)
    logger.info(f"Below range: y = {y_min - 1:.2f} -> status: {status}")
    x, status = sequence.find_x_for_y_in_pp(pp, y_max + 1)
    logger.info(f"Above range: y = {y_max + 1:.2f} -> status: {status}")

    # Test round-trip conversion
    logger.info("Testing round-trip conversion (x -> y -> x)")
    for x_orig in test_x_values:
        y, _ = sequence.safe_evaluate_pp(pp, x_orig)
        x_back, status = sequence.find_x_for_y_in_pp(pp, y)
        if status:
            error = abs(x_orig - x_back)
            logger.info(f"x = {x_orig:.2f} -> y = {y:.2f} -> x = {x_back:.2f}, error: {error:.6f}")
        else:
            logger.warning(f"Round-trip failed for x = {x_orig:.2f}")


def visualize_piecewise_polynomials(pp_files, titles, save_path=None):
    """
    Visualize piecewise polynomial functions from JSON files.

    Args:
        pp_files (list): List of JSON file paths for piecewise polynomials
        titles (list): List of titles for each polynomial
        save_path (str, optional): Path to save the figure. If None, the figure is displayed.
    """
    plt.figure(figsize=(16, 12))

    for i, (pp_file, title) in enumerate(zip(pp_files, titles)):
        plt.subplot(2, 2, i + 1)

        try:
            pp, breaks = sequence.extract_and_define_pp(pp_file, return_breaks=True)

            if pp is None:
                plt.title(f"{title} - Not available")
                continue

            # Create x values for plotting
            x_min, x_max = min(breaks), max(breaks)
            x = np.linspace(x_min, x_max, 1000)

            # Calculate y values
            y = pp(x)

            # Plot the piecewise polynomial
            plt.plot(x, y, 'b-', label='PP Function')
            plt.scatter(breaks, pp(breaks), color='red', zorder=5, label='Knots')

            # Select a few y values to demonstrate inverse lookup
            y_demo = np.linspace(min(y), max(y), 9)
            for y_val in y_demo:
                # Use our find_x_for_y_in_pp function
                x_result, status = sequence.find_x_for_y_in_pp(pp, y_val)
                if status:
                    plt.plot([x_result], [y_val], 'go', markersize=8)
                    plt.annotate(f'y={y_val:.2f} -> x={x_result:.2f}',
                                (x_result, y_val),
                                textcoords="offset points",
                                xytext=(10, 0),
                                ha='left')

            plt.title(title)
            plt.xlabel('x values')
            plt.ylabel('y values')
            plt.grid(True)
            plt.legend()
        except Exception as e:
            logger.error(f"Error visualizing {title}: {e}")
            plt.title(f"{title} - Error: {str(e)}")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        logger.info(f"Figure saved to {save_path}")
    else:
        plt.show()


def demonstrate_inverse_lookup(pp_file, y_values, title):
    """
    Demonstrate looking up x values for given y values in a piecewise polynomial.

    Args:
        pp_file (str): JSON file path for piecewise polynomial
        y_values (list): List of y values to find x values for
        title (str): Title for the plot
    """
    pp, breaks = sequence.extract_and_define_pp(pp_file, return_breaks=True)

    if pp is None:
        logger.error(f"{title} - Not available")
        return

    # Create x values for plotting
    x_min, x_max = min(breaks), max(breaks)
    x = np.linspace(x_min, x_max, 1000)

    # Calculate y values
    y = pp(x)

    plt.figure(figsize=(10, 6))
    plt.plot(x, y, 'b-', label='PP Function')
    plt.scatter(breaks, pp(breaks), color='red', zorder=5, label='Knots')

    # Find x values for each y value
    for y_val in y_values:
        x_result, status = sequence.find_x_for_y_in_pp(pp, y_val)
        if status:
            plt.plot([x_result], [y_val], 'go', markersize=8)
            plt.annotate(f'y={y_val:.2f} -> x={x_result:.2f}',
                        (x_result, y_val),
                        textcoords="offset points",
                        xytext=(10, 0),
                        ha='left')
            logger.info(f"For {title}: y={y_val:.2f} corresponds to x={x_result:.2f}")
        else:
            logger.warning(f"For {title}: Could not find an accurate x value for y={y_val:.2f}")

    plt.title(f"{title} - Inverse Lookup Demonstration")
    plt.xlabel('x values')
    plt.ylabel('y values')
    plt.grid(True)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    logger.info("Starting PP testing and visualization")

    # Define test file paths - update these to your actual paths
    path = ('igt\\config\\conversion_data\\')
    eq_curve_file = path + 'equalizationCurveFitExport.json'
    focus_curve_file = path + 'focusCurveFitExport.json'
    power_curve_file = path + 'powerCurveFitExport.json'
    volt_curve_file = path + 'voltageCurveFit_IGT_32_ch.json'

    # Run specific tests on power curve
    logger.info("Testing power curve conversions")
    test_pp_conversions(power_curve_file)

    # Demonstrate inverse lookup
    demonstrate_inverse_lookup(power_curve_file, [50, 60, 70, 80, 90], "Power Curve")

    # Visualize all curves if they exist
    pp_files = [
        eq_curve_file,
        focus_curve_file,
        power_curve_file,
        volt_curve_file
    ]
    pp_files = [f for f in pp_files if f is not None]

    if pp_files:
        titles = ["Equalization Curve", "Focus Curve", "Power Curve", "Voltage Curve"]
        titles = titles[:len(pp_files)]  # Adjust titles to match available files
        plt_file = os.path.join(log_dir, filename)
        visualize_piecewise_polynomials(pp_files, titles, save_path=plt_file)

    logger.info("PP testing and visualization completed")