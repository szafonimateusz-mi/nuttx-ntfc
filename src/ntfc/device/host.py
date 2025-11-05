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

"""Host-based emulated devices."""

import os
import re
import signal
import time
from threading import Event
from typing import List

import pexpect
import psutil

from ntfc.logger import logger

from .common import CmdReturn, CmdStatus, DeviceCommon
from .nuttx import DeviceNuttx

###############################################################################
# Class: DeviceHost
###############################################################################


class DeviceHost(DeviceCommon):
    """This class implements common interface for host emulated devices."""

    _BUSY_LOOP_TIMEOUT = 180  # 180 sec with no data read from target

    def __init__(self, conf):
        """Initialize host based device.

        :param conf: configuration handler
        """
        self._child = None
        self._cwd = None
        self._cmd = None
        self._logs = None

        self._crash = Event()
        self._busy_loop = Event()
        self._busy_loop_last = 0

        # TODO: pass as init argument
        #       now we use NuttX as default target
        self._dev = DeviceNuttx(conf)

    def _dev_is_health(self) -> bool:
        """Check if the host device is OK."""
        if not self._child.isalive():
            return False

        if self._crash.is_set():
            return False

        return True

    def _dev_reopen(self):
        """Reopen host device."""
        self.host_close()
        return self.host_open(self._cmd)

    def _console_log(self, data: bytes) -> None:
        """Log console output."""
        if self._logs is not None:
            self._logs["console"].write(data.decode("utf-8"))

    def _write(self, data: bytes) -> None:
        """Write to the host device."""
        if not self._dev_is_health():
            return

        # send char by char to avoid line length full
        for c in data:
            self._child.send(bytes([c]))

        # add new line if missing
        if data[-1] != b"\n":
            self._child.send(b"\n")

        # read all garbage left by character echo
        _ = self._read_all(timeout=0)
        self._console_log(_)

    def _write_ctrl(self, c: str) -> None:
        """Write a control character to the host device."""
        if not self._dev_is_health():
            return

        self._child.sendcontrol(c)

    def _readline(self) -> bytes:
        """Read line from the host device."""
        if not self._child:
            raise IOError("Host device is not open")

        if not self._dev_is_health():
            return b""

        try:
            data = self._child.readline()
            return data

        except pexpect.TIMEOUT:
            self._write(b"\n")
            logger.debug("Timeout while reading from device")
            return b""

        except BaseException:
            raise

    def _read(self) -> bytes:
        """Read data from the host device."""
        if not self._child:
            raise IOError("Host device is not open")

        if not self._dev_is_health():
            return b""

        try:
            return self._child.read_nonblocking(size=1024, timeout=1)

        except pexpect.TIMEOUT:
            return b""

        except pexpect.EOF:
            return b""

        except BaseException:
            raise

    def _read_all(self, timeout=1) -> bytes:
        """Read data from the host device."""
        if not self._child:
            raise IOError("Host device is not open")

        if not self._dev_is_health():
            return b""

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

        # regex pattern to match ANSI escape sequences
        ansi_escape = re.compile(rb"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        # clean output from garbage
        clean = ansi_escape.sub(b"", output)

        return clean

    def _wait_for_boot(self, timeout: int = 10) -> bool:
        """Wait for device booted."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            # send new line and expect prompt in returned data
            ret = self.send_command(b"\n", 1)
            if self._dev.prompt in ret:
                return True

            time.sleep(1)

        return False

    def _kill_process_group(self, process: pexpect.spawn):
        """Kill process group."""
        pid = process.pid

        # terminate process gracefully
        os.killpg(pid, signal.SIGTERM)

        try:
            # wait for the process group to terminate
            parent = psutil.Process(pid)
            parent.wait(timeout=10)
            logger.info(f"Process group {pid} terminated successfully.")

        except psutil.TimeoutExpired:
            logger.warning(
                f"Timeout: Process group {pid}"
                "did not terminate within 5 seconds."
            )
            # force termination
            os.killpg(pid, signal.SIGKILL)
            logger.info(f"Sent SIGKILL to process group {pid}")

    @property
    def prompt(self) -> str:
        """Return target device prompt."""
        return self._dev.prompt

    @property
    def no_cmd(self) -> str:
        """Return command not found string."""
        return self._dev.no_cmd

    def host_open(self, cmd: List[str], uptime: int = 0):
        """Open host-based target device."""
        if self._child:
            raise IOError("Host device already open")

        self._child = None
        self._crash.clear()
        self._busy_loop.clear()

        # we need command to reopen file in the case of crash
        self._cmd = cmd

        logger.info("spawn cmd: {}".format("".join(cmd)))
        print("spawn cmd: {}".format("".join(cmd)))
        self._child = pexpect.spawn(
            "".join(cmd), timeout=10, maxread=20000, cwd=self._cwd
        )

        time.sleep(uptime)

        ret = self._wait_for_boot()
        if ret is False:
            raise TimeoutError("device boot timeout")

        return self._child

    def host_close(self):
        """Close host-based target device."""
        if not self._child:
            raise IOError("Host device not ready")

        if self._child.isalive():
            # send power off
            self.poweroff()
            time.sleep(1)

        if self._child.isalive():
            # kill process group
            self._kill_process_group(self._child)

        self._child = None

        logger.info("host device closed")

    def send_command(self, cmd: bytes | str, timeout: int = 1) -> bytes:
        """Send command to the host device and get the response."""
        if not self._child:
            raise IOError("Host device not ready")

        # convert string to bytes
        if not isinstance(cmd, bytes):
            cmd = cmd.encode("utf-8")

        # update timeout for pexpect
        self._child.timeout = timeout

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
    ):
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
        self._readline()

        output = self.send_command(cmd, 0)
        end_time = time.time() + timeout
        _match = None
        while True:
            output += self._read_all()

            # REVISIT: limit output to last 10000 characters, otherwise
            # re.search can stack
            if len(output) > 10000:
                output = output[-10000:]

            # check output for pattern match
            _match = re.search(pattern, output)
            if _match:
                logger.debug(f">>match: {output}, search: {pattern}<<")
                ret = CmdStatus.SUCCESS
                break

            # check for timeout
            if time.time() > end_time:
                ret = CmdStatus.TIMEOUT
                break

            # exit before timeout if dev crashed
            if not self._dev_is_health():
                break

        # log console output and return
        self._console_log(output)
        return CmdReturn(ret, _match, output.decode("utf-8"))

    def send_ctrl_cmd(self, ctrl_char: str):
        """Send control command to the device."""
        if not self._child:
            raise IOError("Host device is not open")

        self._write_ctrl(ctrl_char)

        logger.info(f"Sent Ctrl+{ctrl_char}.")

        return CmdStatus.SUCCESS

    @property
    def name(self) -> str:
        """Get device name."""
        return "host_unknown"

    @property
    def busyloop(self) -> bool:
        """Check if the device is in busy loop."""
        return True if self._busy_loop.is_set() else False

    @property
    def crash(self) -> bool:
        """Check if the device is crashed."""
        return True if self._crash.is_set() else False

    @property
    def notalive(self) -> bool:
        """Check if the device is dead."""
        if not self._child:
            return True
        return not self._child.isalive()

    def poweroff(self) -> None:
        """Poweroff the device."""
        self.send_command(self._dev.poweroff_cmd)

    def reboot(self, timeout: int) -> bool:
        """Reboot the device."""
        return True if self._dev_reopen() else False

    def start_log_collect(self, logs) -> None:
        """Start device log collector."""
        self._logs = logs

    def stop_log_collect(self) -> None:
        """Stop device log collector."""
        self._logs = None
