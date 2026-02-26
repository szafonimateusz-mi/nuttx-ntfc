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

    @property
    def enable(self) -> bool:
        """Return whether GDB integration is enabled."""
        return self._enable

    @property
    def force_panic(self) -> bool:
        """Return whether to force a panic on the device before coredump."""
        return self._force_panic


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

    @property
    def coredump(self) -> CoredumpConfig:
        """Return coredump configuration."""
        return self._coredump

    @property
    def gdb(self) -> GdbConfig:
        """Return GDB configuration."""
        return self._gdb
