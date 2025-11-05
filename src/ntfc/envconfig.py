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

"""Configuration handler."""

import pprint
from typing import Dict, Union

import yaml

from ntfc.lib.elf.elf_parser import ElfParser


class ProductConfig:
    """Product configuration."""

    def __init__(self, cfg: Dict) -> None:
        """Initialzie product configuration."""
        self._config = cfg

        self._kv_values = []
        self._elf = []

        for core in range(len(self.cores)):
            conf_path = self.core(cpu=core).get("conf_path", None)
            if conf_path:
                # add entry in dict
                self._kv_values.append({})
                # load config values
                self._load_core_config(core)
                # check some .config requirements
                if self._kv_validate(core) is False:
                    raise IOError

        if self.cores:
            self._load_elf()

    def _load_core_config(self, core: int) -> None:
        """Load core configuration."""
        with open(self.core(cpu=core)["conf_path"], "r") as f:
            for line in f:
                # ignore all commented lines
                if line[0] != "#" and line[0] != "\n":
                    name = line.split("=")[0]
                    val = line.split("=")[1]

                    # parse option value
                    if val[0] == "y":
                        val = True
                    else:
                        val = val[1:-2]

                    self._kv_values[core][name] = val

    def _kv_validate(self, core: int) -> bool:
        """Check if configuration can be used with this tool."""
        requirements = [["CONFIG_DEBUG_SYMBOLS", True]]

        for req in requirements:
            if self.kv_check(req[0], core) != req[1]:
                return False
        return True

    def _load_elf(self) -> None:
        """Load ELF symbols."""
        for core in range(len(self.cores)):
            path = self.core(cpu=core).get("elf_path", None)
            if path:
                elf = ElfParser(path)
            else:
                elf = None

            self._elf.append(elf)

    @property
    def config(self) -> Dict:
        """Return test configuration."""
        return self._config

    @property
    def cores(self) -> Dict:
        """Return product cores configuration."""
        return self._config["cores"]

    @property
    def kv_conf(self) -> Dict:
        """Return kconfig options."""
        return self._kv_values

    def kv_check(self, cfg: str, core=0) -> bool:
        """Check Kconfig option."""
        return (
            self._kv_values[core][cfg]
            if self._kv_values[core].get(cfg)
            else False
        )

    def core(self, cpu: int = 0) -> Dict:
        """Return core parameters."""
        if cpu == 0:
            cpuname = "main_core"
        else:
            cpuname = "core" + str(cpu)

        return self.cores.get(cpuname, "")

    def cmd_check(self, cmd: str, core: int = 0) -> bool:
        """Check if command is available in binary."""
        if self._elf[core]:
            symbol_name = f"{cmd}_main" if "cmocka" in cmd else cmd
            return self._elf[core].has_symbol(symbol_name)

        return False


class EnvConfig:
    """This class handles tests environment configuration."""

    def __init__(self, yaml_cfg: Union[str, Dict], args=None):
        """Initialzie tests environment configuration."""
        self._args = []
        self._cfg_values = {}

        if isinstance(yaml_cfg, str):
            self._load_config(yaml_cfg)
        elif isinstance(yaml_cfg, dict):
            self._cfg_values = yaml_cfg
        else:
            raise TypeError

        self._products = self._products_create(self._cfg_values)

        self._print_config()

    def _products_create(self, config: dict):
        """Create product configuration."""
        products = []
        for k in config.keys():
            if "product" in k:
                p = ProductConfig(config[k])
                products.append(p)

        return products

    def _load_config(self, yaml_path: str) -> None:
        """Load configuration."""
        with open(yaml_path, "r") as f:
            self._cfg_values = yaml.safe_load(f)

    def _print_config(self) -> None:
        """Print device configuration."""
        print("YAML config:")
        pp = pprint.PrettyPrinter()
        pp.pprint(self._cfg_values)

    @property
    def device(self) -> Dict:
        """Return device parameters."""
        return self._cfg_values.get("device", None)

    @property
    def product(self) -> list:
        """Return product instance."""
        return self._products

    def product_get(self, product: int = 0) -> dict:
        """Return product parameters."""
        if product >= len(self._products):
            return None
        return self._products[product].config

    def core(self, product: int = 0, cpu: int = 0) -> Dict:
        """Return core parameters."""
        if product >= len(self._products):
            return ""
        return self._products[product].core(cpu)

    @property
    def config(self) -> Dict:
        """Return test configuration."""
        return self._cfg_values

    @property
    def kv_conf(self) -> Dict:
        """Return kconfig options."""
        product = 0
        return self._products[product].kv_conf

    # dep_config
    def kv_check(self, cfg: str, product: int = 0, core: int = 0) -> bool:
        """Check Kconfig option."""
        return self._products[product].kv_check(cfg, core)

    def cmd_check(self, cmd: str, product: int = 0, core: int = 0) -> bool:
        """Check if command is available in binary."""
        product = 0
        return self._products[product].cmd_check(cmd, core)
