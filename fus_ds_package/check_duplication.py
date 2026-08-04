"""Fail if duplicated code exceeds a percentage threshold.

Works around pylint's built-in "percent duplicated lines" report (under
[SIMILARITIES] / --reports=y), which reports 0.000% even when duplicate-code
(R0801) findings exist -- verified against pylint 3.3.9. Instead, this parses
the structured duplicate-code messages directly and computes the percentage
against the actual line count of the analysed package.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

THRESHOLD_PERCENT = 3.0
PACKAGE = "fus_driving_systems"


def total_source_lines():
    total = 0
    for path in Path(PACKAGE).rglob("*.py"):
        with path.open(encoding="utf-8") as f:
            total += sum(1 for _ in f)
    return total


def duplicated_lines():
    result = subprocess.run(
        [sys.executable, "-m", "pylint", PACKAGE, "--disable=all",
         "--enable=duplicate-code", "-f", "json2"],
        capture_output=True, text=True, check=False,
    )
    data = json.loads(result.stdout)
    total = 0
    for msg in data["messages"]:
        for start, end in re.findall(r"\[(\d+):(\d+)\]", msg["message"]):
            total += int(end) - int(start) + 1
    return total


def main():
    total_lines = total_source_lines()
    dup_lines = duplicated_lines()
    percent = (dup_lines / total_lines) * 100 if total_lines else 0.0
    print(f"Duplicated lines: {dup_lines} / {total_lines} ({percent:.2f}%)")
    if percent > THRESHOLD_PERCENT:
        print(f"FAIL: duplication {percent:.2f}% exceeds {THRESHOLD_PERCENT}% threshold")
        sys.exit(1)
    print(f"OK: within {THRESHOLD_PERCENT}% threshold")


if __name__ == "__main__":
    main()
