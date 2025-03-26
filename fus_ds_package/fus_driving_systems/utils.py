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

import logging

import time

# Get the start time
wall_t0 = time.time()
cpu_t0 = time.process_time()


class CustomFormatter(logging.Formatter):
    """
    Custom logging formatter that extends the functionality of logging. Formatter to include custom
    log information.

    This formatter calculates the elapsed time since the start of the program and includes it in
    each log message. Additionally, it includes function-related information such as the module,
    function name, and line number. The timestamp of each log record is also included in the
    formatted log message.

    Attributes:
        datefmt (str): The format string for formatting the timestamp in log records.

    Methods:
        format(record): Formats the specified log record by appending custom log information to it.
    """

    def format(self, record):
        """
        Formats the specified log record by appending custom log information to it.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message including custom log information.
        """

        elapsed_wall_time = time.time() - wall_t0
        elapsed_cpu_time = time.process_time() - cpu_t0
        elapsed_str = f"{elapsed_wall_time:.2f} seconds (CPU: {elapsed_cpu_time:.2f} seconds)"

        # Extract function-related information from the record
        func_info = f"{record.module}.{record.funcName} line {record.lineno}"

        # Get the timestamp of the log record
        timestamp = self.formatTime(record, self.datefmt)

        # Combine elapsed time, function information, and function docstring
        log_info = f"Elapsed: {elapsed_str} - {timestamp} - Function: {func_info}"

        # Apply the default formatting from the parent class
        formatted_record = super().format(record)

        # Concatenate the custom log information with the formatted record
        return f"{log_info} - {formatted_record}"
