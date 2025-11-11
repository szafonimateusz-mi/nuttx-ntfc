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

from typing import TYPE_CHECKING

import serial

from ntfc.logger import logger

from .common import DeviceCommon

if TYPE_CHECKING:
    from ntfc.envconfig import ProductConfig

###############################################################################
# Class: DeviceSerial
###############################################################################


class DeviceSerial(DeviceCommon):
    """This class implements host-based sim emulator."""

    def __init__(self, conf: "ProductConfig"):
        """Initialize sim emulator device."""
        DeviceCommon.__init__(self, conf)
        self._ser = None

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

    def _dev_is_health_priv(self) -> bool:
        """Check if the serial device is OK."""
        if not self._ser:
            return False

        return True

    def _write(self, data: bytes) -> None:
        """Write to the serial device."""
        if not self.dev_is_health():
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
        if not self.dev_is_health():
            return

        self._ser.write(bytes([c]))

    def _read(self) -> bytes:
        """Read data from the serial device."""
        if not self.dev_is_health():
            return b""

        return self._ser.read(size=1024)

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

    @property
    def name(self) -> str:
        """Get device name."""
        return "serial"

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
        if "reboot" in self._conf.core():
            logger.info("reboot device")
            cmd = self._conf.core()["reboot"]
            self._system_cmd(cmd)
