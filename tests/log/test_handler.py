############################################################################
# SPDX-License-Identifier: Apache-2.0
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.  The
# ASF licenses this file to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
############################################################################

"""Tests for NTFC log handler module."""

import os
import tempfile

from ntfc.log.handler import LogHandler

###############################################################################
# Helpers
###############################################################################


def _read(tmpdir: str, testname: str, suffix: str) -> str:
    """Return the full contents of a log file.

    :param tmpdir: Directory that holds the log files.
    :param testname: Test case name (base-name of the log file).
    :param suffix: File suffix (e.g. ``LogHandler.DEVICE_SUFFIX``).
    :return: File contents as a string.
    """
    with open(os.path.join(tmpdir, testname + suffix)) as f:
        return f.read()


###############################################################################
# Tests: constructor
###############################################################################


def test_init_creates_directory() -> None:
    """Constructor creates the target directory when it does not exist."""
    with tempfile.TemporaryDirectory() as base:
        core_dir = os.path.join(base, "product", "core0")
        h = LogHandler(core_dir, "test_foo")
        h.close()
        assert os.path.isdir(core_dir)


def test_init_creates_log_files() -> None:
    """Constructor creates both console and device log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        h = LogHandler(tmpdir, "test_bar")
        h.close()
        assert os.path.exists(
            os.path.join(tmpdir, "test_bar" + LogHandler.CONSOLE_SUFFIX)
        )
        assert os.path.exists(
            os.path.join(tmpdir, "test_bar" + LogHandler.DEVICE_SUFFIX)
        )


###############################################################################
# Tests: write methods
###############################################################################


def test_write_device_writes_to_device_only() -> None:
    """``write_device`` writes to device log and leaves console untouched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        h = LogHandler(tmpdir, "t")
        h.write_device("event\n")
        h.close()
        assert _read(tmpdir, "t", LogHandler.DEVICE_SUFFIX) == "event\n"
        assert _read(tmpdir, "t", LogHandler.CONSOLE_SUFFIX) == ""


def test_write_console_writes_to_console_only() -> None:
    """``write_console`` writes to console log and leaves device untouched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        h = LogHandler(tmpdir, "t")
        h.write_console(b"output")
        h.close()
        assert _read(tmpdir, "t", LogHandler.CONSOLE_SUFFIX) == "output"
        assert _read(tmpdir, "t", LogHandler.DEVICE_SUFFIX) == ""


def test_writelines_device_writes_all_lines() -> None:
    """``writelines_device`` writes all lines to the device log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        h = LogHandler(tmpdir, "t")
        h.writelines_device(["line1\n", "line2\n"])
        h.close()
        assert _read(tmpdir, "t", LogHandler.DEVICE_SUFFIX) == "line1\nline2\n"
        assert _read(tmpdir, "t", LogHandler.CONSOLE_SUFFIX) == ""


###############################################################################
# Tests: close
###############################################################################


def test_close_closes_both_handles() -> None:
    """``close`` makes subsequent writes raise an error (files are closed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        h = LogHandler(tmpdir, "t")
        h.close()
        # Accessing internal handles to verify they are closed
        assert h._console.closed  # type: ignore[attr-defined]
        assert h._device.closed  # type: ignore[attr-defined]
