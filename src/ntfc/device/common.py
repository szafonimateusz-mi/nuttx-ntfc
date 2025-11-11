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

"""Device common interface."""

import re
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import astuple, dataclass
from enum import IntEnum
from threading import Event
from typing import TYPE_CHECKING, Any, Dict, Optional

from ntfc.logger import logger

from .getos import get_os

if TYPE_CHECKING:
    from ntfc.envconfig import ProductConfig


###############################################################################
# Class: CmdStatus
###############################################################################


class CmdStatus(IntEnum):
    """Command status."""

    SUCCESS = 0
    NOTFOUND = -1
    TIMEOUT = -2

    def __str__(self) -> str:
        """Return enum string."""
        return self.name


###############################################################################
# Class: CmdReturn
###############################################################################


@dataclass
class CmdReturn:
    """Command return data."""

    status: CmdStatus
    rematch: "Optional[re.Match[Any]]" = None
    output: str = ""

    def valid_match(self) -> bool:
        """Check if RE match is valid."""
        return bool((self.status == CmdStatus.SUCCESS) and self.rematch)

    def __iter__(self) -> Any:
        """Make the dataclass instance iterable."""
        for value in astuple(self):
            yield value


###############################################################################
# Class: DeviceCommon
###############################################################################


class DeviceCommon(ABC):
    """Device common interface."""

    _BUSY_LOOP_TIMEOUT = 180  # 180 sec with no data read from target

    def __init__(self, conf: "ProductConfig"):
        """Initialize common device."""
        self._conf = conf
        # get OS abstraction
        self._dev = get_os(conf)

        # logs handler
        self._logs: Optional[Dict[str, Any]] = None

        # device health
        self._crash = Event()
        self._busy_loop = Event()
        self._busy_loop_last = 0

        self._read_all_sleep = 0.1

    def _console_log(self, data: bytes) -> None:
        """Log console output."""
        if self._logs is not None:
            self._logs["console"].write(data.decode("utf-8"))

    def _wait_for_boot(self, timeout: int = 5) -> bool:
        """Wait for device booted."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            # send new line and expect prompt in returned data
            ret = self.send_command(b"\n", 1)
            if self._dev.prompt in ret:
                return True

            time.sleep(1)

        return False

    def _read_all(self, timeout: int = 1) -> bytes:
        """Read data from the device."""
        output = b""
        end_time = time.time() + timeout

        while True:
            chunk = self._read()
            output += chunk
            time_now = time.time()

            # check for any sign of system crash
            if any(key in output for key in self._dev.crash_keys):
                logger.info("Assertion detected! Set crash flag")
                self._crash.set()
                break

            # check for busy loop
            # trigger an error if there was no data to read for a long time
            if not chunk:
                if self._busy_loop_last and (
                    time_now - self._busy_loop_last > self._BUSY_LOOP_TIMEOUT
                ):
                    self._busy_loop_last = 0
                    self._busy_loop.set()
                    break
            else:
                self._busy_loop_last = time_now

            # check for timeout
            if time_now > end_time:
                break

            # need to sleep for a while, otherwise host CPU load jumps to 100%
            time.sleep(self._read_all_sleep)

        # regex pattern to match ANSI escape sequences
        ansi_escape = re.compile(rb"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        # clean output from garbage
        clean = ansi_escape.sub(b"", output)

        return clean

    def dev_is_health(self) -> bool:
        """Check if the serial device is OK."""
        if not self._dev_is_health_priv():
            return False

        if self._crash.is_set():
            return False

        if self._busy_loop.is_set():
            return False

        return True

    def send_command(self, cmd: bytes | str, timeout: int = 1) -> bytes:
        """Send command to the device and get the response."""
        # convert string to bytes
        if not isinstance(cmd, bytes):
            cmd = cmd.encode("utf-8")

        # read any pending output and drop
        _ = self._read_all(timeout=0)
        self._console_log(_)

        # write command and get response
        self._write(cmd)
        rsp = self._read_all(timeout=timeout)

        logger.debug("Sent command: %s", cmd)

        # console log
        self._console_log(rsp)
        return rsp

    def send_cmd_read_until_pattern(
        self, cmd: bytes, pattern: bytes, timeout: int
    ) -> CmdReturn:
        """Send command to device and read until the specified pattern.

        :param cmd: (bytes) command to send to device
        :param pattern: (bytes, or list of (bytes), optional)
         String or regex pattern to look for. If a list,
         patterns will be concatenated with '.*'.
         The pattern will be converted to bytes for matching.
         Default is None.
        :param timeout: (int) timeout value in seconds

        :return: CmdReturn : command return data
        """
        if not isinstance(cmd, bytes):
            raise TypeError("Command must by bytes")

        if not isinstance(pattern, bytes):
            raise TypeError("Pattern must by bytes")

        # clear buffer for reading data after command
        _ = self._read_all()

        output = self.send_command(cmd, 0)
        end_time = time.time() + timeout
        _match = None
        ret = CmdStatus.TIMEOUT
        while True:
            output += self._read_all()

            # chunk size to process, otherwise re.search can stack
            # REVISIT: its possible to miss some pattern in output
            chunk_size = 10000
            for i in range(0, len(output), chunk_size):
                chunk = output[i : i + chunk_size]

                _match = re.search(pattern, chunk)
                if _match:
                    logger.debug(f">>match: {chunk}, search: {pattern}<<")
                    ret = CmdStatus.SUCCESS
                    break

            # break if found match
            if ret == CmdStatus.SUCCESS:
                break

            # check for timeout
            if time.time() > end_time:
                ret = CmdStatus.TIMEOUT
                break

            # exit before timeout if dev crashed
            if not self.dev_is_health():
                break

        # log console output and return
        self._console_log(output)
        return CmdReturn(ret, _match, output.decode("utf-8"))

    def send_ctrl_cmd(self, ctrl_char: str) -> CmdStatus:
        """Send control command to the device."""
        self._write_ctrl(ctrl_char)
        logger.info(f"Sent Ctrl+{ctrl_char}.")
        return CmdStatus.SUCCESS

    def start_log_collect(self, logs: dict[str, Any]) -> None:
        """Start device log collector."""
        self._logs = logs

    def stop_log_collect(self) -> None:
        """Stop device log collector."""
        self._logs = None

    def _system_cmd(self, cmd: str) -> None:
        logger.info("system command:", cmd)
        subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    @property
    def prompt(self) -> bytes:
        """Return target device prompt."""
        return self._dev.prompt

    @property
    def no_cmd(self) -> str:
        """Return command not found string."""
        return self._dev.no_cmd

    @property
    def busyloop(self) -> bool:
        """Check if the device is in busy loop."""
        return True if self._busy_loop.is_set() else False

    @property
    def crash(self) -> bool:
        """Check if the device is crashed."""
        return True if self._crash.is_set() else False

    @abstractmethod
    def _read(self) -> bytes:
        """Read data from the device."""

    @abstractmethod
    def _write(self, data: bytes) -> None:
        """Write to the device."""

    @abstractmethod
    def _write_ctrl(self, c: str) -> None:
        """Write a control character to the device."""

    @abstractmethod
    def _dev_is_health_priv(self) -> bool:
        """Check if the device is OK."""

    @abstractmethod
    def start(self) -> None:
        """Start device."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get device name."""

    @property
    @abstractmethod
    def notalive(self) -> bool:
        """Check if the device is dead."""

    @abstractmethod
    def poweroff(self) -> None:
        """Poweroff the device."""

    @abstractmethod
    def reboot(self, timeout: int) -> bool:
        """Reboot the device."""
