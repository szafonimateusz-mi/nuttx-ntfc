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

"""Debug configuration handlers."""

from typing import Any, Dict

###############################################################################
# Class: CoredumpConfig
###############################################################################


class CoredumpConfig:
    """Coredump debug configuration.

    Parses the ``debug.coredump`` section of a product YAML configuration.
    All fields are optional and default to safe/disabled values.
    """

    VALID_TYPES = ("auto", "gdb", "fastboot", "ymodem")
    _DEFAULT_LIMIT = 5

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialize coredump configuration.

        :param cfg: Raw ``debug.coredump`` dictionary from product YAML.
        :raises ValueError: If ``type`` is not one of the valid values.
        """
        self._enable: bool = bool(cfg.get("enable", False))
        self._limit: int = int(cfg.get("limit", self._DEFAULT_LIMIT))

        raw_type: str = str(cfg.get("type", "auto"))
        if raw_type not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid coredump type '{raw_type}'. "
                f"Must be one of: {', '.join(self.VALID_TYPES)}"
            )
        self._type: str = raw_type

    @property
    def enable(self) -> bool:
        """Return whether coredump collection is enabled."""
        return self._enable

    @property
    def collection_type(self) -> str:
        """Return the coredump collection method.

        :return: One of ``auto``, ``gdb``, ``fastboot``, ``ymodem``.
        """
        return self._type

    @property
    def limit(self) -> int:
        """Return the maximum number of coredumps to collect per session."""
        return self._limit


###############################################################################
# Class: GdbConfig
###############################################################################


class GdbConfig:
    """GDB debug configuration.

    Parses the ``debug.gdb`` section of a product YAML configuration.
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialize GDB configuration.

        :param cfg: Raw ``debug.gdb`` dictionary from product YAML.
        """
        self._enable: bool = bool(cfg.get("enable", False))
        self._force_panic: bool = bool(cfg.get("force_panic", False))
        self._target: str = str(cfg.get("target", ""))

    @property
    def enable(self) -> bool:
        """Return whether GDB integration is enabled."""
        return self._enable

    @property
    def force_panic(self) -> bool:
        """Return whether to force a panic on the device before coredump."""
        return self._force_panic

    @property
    def target(self) -> str:
        """Return the GDB remote target address or socket path.

        The value is passed directly to ``target remote <target>`` in GDB.
        Examples: ``"localhost:1234"``, ``"/tmp/gdb.socket"``.
        An empty string means no ``target remote`` command is sent.

        :return: Target string (may be empty).
        """
        return self._target


###############################################################################
# Class: FastbootConfig
###############################################################################


class FastbootConfig:
    """Fastboot coredump configuration.

    Parses the ``debug.fastboot`` section of a product YAML configuration.
    """

    _DEFAULT_MEM_ADDR = "0x40000000"
    _DEFAULT_MEM_SIZE = "0x08000000"

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialize fastboot configuration.

        :param cfg: Raw ``debug.fastboot`` dictionary from product YAML.
        """
        self._dev_sn: str = str(cfg.get("dev_sn", ""))
        self._mem_addr: str = str(cfg.get("mem_addr", self._DEFAULT_MEM_ADDR))
        self._mem_size: str = str(cfg.get("mem_size", self._DEFAULT_MEM_SIZE))

    @property
    def dev_sn(self) -> str:
        """Return the fastboot device serial number."""
        return self._dev_sn

    @property
    def mem_addr(self) -> str:
        """Return the memory start address for the dump (hex string)."""
        return self._mem_addr

    @property
    def mem_size(self) -> str:
        """Return the memory region size to dump (hex string)."""
        return self._mem_size


###############################################################################
# Class: YmodemConfig
###############################################################################


class YmodemConfig:
    """Ymodem coredump configuration.

    Parses the ``debug.ymodem`` section of a product YAML configuration.
    """

    _DEFAULT_BAUD_RATE = 921600

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialize Ymodem configuration.

        :param cfg: Raw ``debug.ymodem`` dictionary from product YAML.
        """
        self._serial_port: str = str(cfg.get("serial_port", ""))
        self._baud_rate: int = int(
            cfg.get("baud_rate", self._DEFAULT_BAUD_RATE)
        )
        self._sbrb_path: str = str(cfg.get("sbrb_path", ""))

    @property
    def serial_port(self) -> str:
        """Return the host serial port path (e.g. ``/dev/ttyUSB0``)."""
        return self._serial_port

    @property
    def baud_rate(self) -> int:
        """Return the baud rate used for the Ymodem transfer."""
        return self._baud_rate

    @property
    def sbrb_path(self) -> str:
        """Return the path to the ``sbrb.py`` Ymodem receiver script."""
        return self._sbrb_path


###############################################################################
# Class: DebugConfig
###############################################################################


class DebugConfig:
    """Top-level debug configuration.

    Parses the ``debug`` section of a product YAML configuration::

        product:
          debug:
            coredump:
              enable: true
              type: auto
              limit: 5
            gdb:
              enable: true
              force_panic: true
            fastboot:
              dev_sn: "ABC123"
            ymodem:
              serial_port: "/dev/ttyUSB0"
              sbrb_path: "/path/to/sbrb.py"

    When the ``debug`` section is absent the configuration defaults to all
    features disabled.
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialize debug configuration.

        :param cfg: Raw ``debug`` dictionary from product YAML.  May be
            empty when the section is not present in the configuration file.
        :raises ValueError: If a nested section contains an invalid value.
        """
        self._coredump = CoredumpConfig(cfg.get("coredump", {}))
        self._gdb = GdbConfig(cfg.get("gdb", {}))
        self._fastboot = FastbootConfig(cfg.get("fastboot", {}))
        self._ymodem = YmodemConfig(cfg.get("ymodem", {}))

    @property
    def coredump(self) -> CoredumpConfig:
        """Return coredump configuration."""
        return self._coredump

    @property
    def gdb(self) -> GdbConfig:
        """Return GDB configuration."""
        return self._gdb

    @property
    def fastboot(self) -> FastbootConfig:
        """Return fastboot configuration."""
        return self._fastboot

    @property
    def ymodem(self) -> YmodemConfig:
        """Return Ymodem configuration."""
        return self._ymodem
