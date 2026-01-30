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

"""Product core configuration handler."""

from typing import Any, Dict, Optional, Union

from ntfc.lib.elf.elf_parser import ElfParser


class CoreConfig:
    """Product core configuration."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialzie product core configuration."""
        self._config = cfg

        self._kv_values: Dict[str, Any] = {}
        self._elf: Optional[ElfParser] = None

        conf_path = self._config.get("conf_path", None)
        if conf_path:
            # load config values
            self._load_core_config()

        elf_path = self._config.get("elf_path", None)
        if elf_path:
            # load ELF
            self._elf = ElfParser(elf_path)

    def _load_core_config(self) -> None:
        """Load core configuration."""
        with open(self._config["conf_path"], "r", encoding="utf-8") as f:
            for line in f:
                # ignore all commented lines
                if line[0] != "#" and line[0] != "\n":
                    name = line.split("=")[0]
                    val = line.split("=")[1]

                    # parse option value
                    if val[0] == "y":
                        val_parsed: Union[bool, str] = True
                    else:
                        val_parsed = val[1:-2]

                    self._kv_values[name] = val_parsed

    @property
    def uptime(self) -> Any:
        """Return core uptime."""
        return self._config.get("uptime", 3)

    @property
    def device(self) -> Any:
        """Return core device."""
        return self._config.get("device", None)

    @property
    def name(self) -> Any:
        """Return core name."""
        return self._config.get("name", "unknown_name")

    def _load_prompt_from_config(self) -> Optional[str]:
        """Load the prompt string from the .config file."""
        return self._kv_values.get("CONFIG_NSH_PROMPT_STRING", None)

    @property
    def prompt(self) -> Any:
        """Return core prompt.

        First check YAML config, if not present, load from .config file.
        """
        # First check if prompt is explicitly set in YAML config
        yaml_prompt = self._config.get("prompt", None)
        if yaml_prompt:
            return yaml_prompt

        # Otherwise, load from .config file
        return self._load_prompt_from_config()

    @property
    def elf_path(self) -> Any:
        """Return core elf path."""
        return self._config.get("elf_path", "")

    @property
    def exec_path(self) -> Any:
        """Return core exec path."""
        return self._config.get("exec_path", "")

    @property
    def exec_args(self) -> Any:
        """Return core exec args."""
        return self._config.get("exec_args", "")

    @property
    def reboot(self) -> Any:
        """Return core reboot command."""
        return self._config.get("reboot", "")

    def kv_check(self, cfg: str) -> Any:
        """Check Kconfig option and return its value.

        :param cfg: Kconfig option name (e.g., 'CONFIG_DEBUG')
        :return: Config value if set (bool True, string value, etc),
                 False if not found
        """
        if not self._kv_values:
            # No config data loaded
            return False

        return self._kv_values.get(cfg, False)

    def cmd_check(self, cmd: str, core: int = 0) -> bool:
        """Check if command is available in binary."""
        if not self._elf:
            raise AttributeError("no elf data")

        symbol_name = f"{cmd}_main" if "cmocka" in cmd else cmd
        return self._elf.has_symbol(symbol_name)
