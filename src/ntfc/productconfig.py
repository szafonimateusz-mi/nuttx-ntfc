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

"""Product configuration handler."""

from typing import Any, Dict

from ntfc.coreconfig import CoreConfig
from ntfc.logger import logger


class ProductConfig:
    """Product configuration."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """Initialzie product configuration."""
        self._config = cfg

        self._cores = []
        for core in range(len(self.cores)):
            core_cfg = CoreConfig(self.core(cpu=core))
            self._cores.append(core_cfg)

    @property
    def config(self) -> Any:
        """Return test configuration."""
        return self._config

    @property
    def cores(self) -> Any:
        """Return product cores configuration."""
        try:
            return self._config["cores"]
        except KeyError:
            logger.error("no cores info in configuration file!")
            return {}

    @property
    def name(self) -> str:
        """Get product name."""
        try:
            return str(self._config["name"])
        except KeyError:  # pragma: no cover
            logger.error("no product name in configuration file!")
            return "unknown_name"

    def kv_check(self, cfg: str, core: int = 0) -> Any:
        """Check Kconfig option."""
        if len(self._cores) <= core:
            raise AttributeError(f"no data for core {core}")

        return self._cores[core].kv_check(cfg)

    def core(self, cpu: int = 0) -> Dict[str, Any]:
        """Return core parameters."""
        if cpu == 0:
            cpuname = "core0"
        else:
            cpuname = "core" + str(cpu)

        result = self.cores.get(cpuname, "")
        return result if isinstance(result, dict) else {}

    def cmd_check(self, cmd: str, core: int = 0) -> bool:
        """Check if command is available in binary."""
        if len(self._cores) <= core:
            raise AttributeError(f"no data for core {core}")

        return self._cores[core].cmd_check(cmd)

    @property
    def cores_num(self) -> int:
        """Get number of cores."""
        return len(self._cores)

    def cfg_core(self, cpu: int) -> CoreConfig:
        """Get core configuration."""
        return self._cores[cpu]
