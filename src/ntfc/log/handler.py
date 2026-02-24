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

"""NTFC log handler module."""

import os
from typing import IO, List

###############################################################################
# Class: LogHandler
###############################################################################


class LogHandler:
    """Opens and manages log files for one core's test session."""

    CONSOLE_SUFFIX = ".console.txt"
    DEVICE_SUFFIX = ".device.txt"

    def __init__(self, core_dir: str, testname: str) -> None:
        """Open log files for a test case.

        Creates *core_dir* if it does not exist, then opens (appending)
        ``<testname>.console.txt`` and ``<testname>.device.txt`` inside it.

        :param core_dir: Directory that will hold the log files.
        :param testname: Test case name used as the file base-name.
        """
        os.makedirs(core_dir, exist_ok=True)
        console_path = os.path.join(core_dir, testname + self.CONSOLE_SUFFIX)
        device_path = os.path.join(core_dir, testname + self.DEVICE_SUFFIX)
        self._console: IO[str] = open(console_path, "a", encoding="utf-8")
        self._device: IO[str] = open(device_path, "a", encoding="utf-8")

    def write_console(self, data: bytes) -> None:
        """Decode bytes and write to the console log.

        :param data: Raw bytes received from the device console.
        """
        self._console.write(data.decode("utf-8"))

    def write_device(self, line: str) -> None:
        """Write one event line to the device log and flush.

        :param line: Formatted event line to write.
        """
        self._device.write(line)
        self._device.flush()

    def writelines_device(self, lines: List[str]) -> None:
        """Bulk-write event lines to the device log and flush.

        :param lines: List of formatted event lines to write.
        """
        self._device.writelines(lines)
        self._device.flush()

    def close(self) -> None:
        """Close both console and device file handles."""
        self._console.close()
        self._device.close()
