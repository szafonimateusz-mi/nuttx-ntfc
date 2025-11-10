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

"""Serial-based device implementation."""

import re
import time
from threading import Event
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
)

import serial

from ntfc.logger import logger

from .common import CmdReturn, CmdStatus, DeviceCommon
from .getos import get_os

if TYPE_CHECKING:
    from ntfc.envconfig import ProductConfig

###############################################################################
# Class: DeviceSerial
###############################################################################


class DeviceSerial(DeviceCommon):
    """This class implements host-based sim emulator."""

    _BUSY_LOOP_TIMEOUT = 180  # 180 sec with no data read from target

    def __init__(self, conf: "ProductConfig"):
        """Initialize sim emulator device."""
        self._conf = conf
        self._ser = None
        self._logs: Optional[Dict[str, Any]] = None
        self._crash = Event()
        self._busy_loop = Event()
        self._busy_loop_last = 0

        # get OS abstraction
        self._dev = get_os(conf)

    def _decode_exec_args(self, args: str):
        """Decode a serial port configuration string."""
        try:
            baud, parity, data_bits, stop_bits = args.split(",")

            parity_map = {
                "n": serial.PARITY_NONE,
                "N": serial.PARITY_NONE,
                "e": serial.PARITY_EVEN,
                "E": serial.PARITY_EVEN,
                "o": serial.PARITY_ODD,
                "O": serial.PARITY_ODD,
                "m": serial.PARITY_MARK,
                "M": serial.PARITY_MARK,
                "s": serial.PARITY_SPACE,
                "S": serial.PARITY_SPACE,
            }

            bytesize_map = {
                5: serial.FIVEBITS,
                6: serial.SIXBITS,
                7: serial.SEVENBITS,
                8: serial.EIGHTBITS,
            }

            stopbits_map = {
                1: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO,
            }

            return {
                "baudrate": int(baud),
                "parity": parity_map.get(parity, serial.PARITY_NONE),
                "bytesize": bytesize_map.get(int(data_bits), serial.EIGHTBITS),
                "stopbits": stopbits_map.get(
                    float(stop_bits), serial.STOPBITS_ONE
                ),
            }

        except Exception as e:
            raise ValueError(f"Invalid format '{args}': {e}")

    def _dev_is_health(self) -> bool:
        """Check if the serial device is OK."""
        if not self._ser:
            return False

        if self._crash.is_set():
            return False

        if self._busy_loop.is_set():
            return False

        return True

    def _console_log(self, data: bytes) -> None:
        """Log console output."""
        if self._logs is not None:
            self._logs["console"].write(data.decode("utf-8"))

    def _write(self, data: bytes) -> None:
        """Write to the serial device."""
        if not self._ser:
            raise IOError("Host device is not open")

        if not self._dev_is_health():
            return

        # send char by char to avoid line length full
        for c in data:
            self._ser.write(bytes([c]))

        # add new line if missing
        if data[-1] != b"\n":
            self._ser.write(b"\n")

        # read all garbage left by character echo
        _ = self._read_all(timeout=0)
        self._console_log(_)

    def _write_ctrl(self, c: str) -> None:
        """Write a control character to the serial device."""
        if not self._ser:
            raise IOError("serial device is not open")

        if not self._dev_is_health():
            return

        self._ser.write(bytes([c]))

    def _read(self) -> bytes:
        """Read data from the serial device."""
        if not self._ser:
            raise IOError("serial device is not open")

        if not self._dev_is_health():
            return b""

        return self._ser.read(size=1024)

    def _read_all(self, timeout: int = 1) -> bytes:
        """Read data from the serial device."""
        if not self._ser:
            raise IOError("serial device is not open")

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

            # need to sleep for a while, otherwise host CPU load jumps to 100%
            time.sleep(0.1)

        # regex pattern to match ANSI escape sequences
        ansi_escape = re.compile(rb"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        # clean output from garbage
        clean = ansi_escape.sub(b"", output)

        return clean

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

    def start(self) -> None:
        """Start serial communication."""
        timeout = 0
        path = self._conf.core()["exec_path"]
        args = self._conf.core()["exec_args"]

        logger.info(f"serial path: {path}")
        logger.info(f"serial args: {args}")

        if args:
            args = self._decode_exec_args(args)
            print(args)
            self._ser = serial.Serial(path, timeout=timeout, **args)
        else:
            self._ser = serial.Serial(path, timeout=timeout)

        # reboot device if possible
        self.reboot()

        ret = self._wait_for_boot()
        if ret is False:
            raise TimeoutError("device boot timeout")

    def send_command(self, cmd: bytes | str, timeout: int = 1) -> bytes:
        """Send command to the serial device and get the response."""
        if not self._ser:
            raise IOError("Serial device not ready")

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
        """Send command to device and read until the specified pattern."""
        if not isinstance(cmd, bytes):
            raise TypeError("Command must by bytes")

        if not isinstance(pattern, bytes):
            raise TypeError("Pattern must by bytes")

        # clear buffer for reading data after command
        _ = self._read_all()

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

    def send_ctrl_cmd(self, ctrl_char: str) -> CmdStatus:
        """Send control command to the device."""
        if not self._ser:
            raise IOError("Serial device is not open")

        self._write_ctrl(ctrl_char)

        logger.info(f"Sent Ctrl+{ctrl_char}.")

        return CmdStatus.SUCCESS

    @property
    def name(self) -> str:
        """Get device name."""
        return "serial"

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

    @property
    def notalive(self) -> bool:
        """Check if the device is dead."""
        if not self._ser:
            return True
        return False

    def poweroff(self) -> None:
        """Poweroff the device."""
        print("TODO: poweroff")

    def reboot(self, timeout: int = 1) -> bool:
        """Reboot the device."""
        print("TODO: reboot")

    def start_log_collect(self, logs: dict[str, Any]) -> None:
        """Start device log collector."""
        self._logs = logs

    def stop_log_collect(self) -> None:
        """Stop device log collector."""
        self._logs = None
