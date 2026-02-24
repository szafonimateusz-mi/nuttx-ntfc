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

"""Build manager for NuttX configuration."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ntfc.log.logger import logger


class NuttXBuilder:
    """NuttX configuration builder (CMake only)."""

    IMAGE_BIN_STR = "$IMAGE_BIN"
    IMAGE_HEX_STR = "$IMAGE_HEX"

    def __init__(self, config: Dict[str, Any], rebuild: bool = True):
        """Initialize NuttX builder."""
        if not isinstance(config, dict):
            raise TypeError("invalid config file type")

        self._cfg_values = config
        self._rebuild = rebuild

    def _run_command(
        self, cmd: List[str], env: Any
    ) -> None:  # pragma: no cover
        """Run command."""
        subprocess.run(cmd, check=True, env=env)

    def _make_dir(self, path: Path) -> None:
        """Create dir."""
        os.makedirs(path, exist_ok=True)

    def _run_cmake(
        self,
        source: str,
        build: str,
        generator: str = "Ninja",
        defines: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Run CMake configure step."""
        build_path = Path(build)
        self._make_dir(build_path)

        # base command
        cmd = [
            "cmake",
            f"-B{build}",
            f"-S{source}",
            f"-G{generator}",
        ]

        # add -DVAR=value parameters
        if defines:  # pragma: no cover
            for k, v in defines.items():
                cmd.append(f"-D{k}={v}")

        # merge environment variables
        run_env = os.environ.copy()
        if env:
            run_env.update(env)  # pragma: no cover

        self._run_command(cmd, env=run_env)

    def _run_build(
        self, build: str, env: Optional[Dict[str, str]] = None
    ) -> None:
        """Run the CMake build step."""
        build_path = Path(build)

        cmd = [
            "cmake",
            "--build",
            str(build_path),
        ]

        run_env = os.environ.copy()
        if env:
            run_env.update(env)  # pragma: no cover

        self._run_command(cmd, env=run_env)

    def _build_core(
        self, core: str, cores: Dict[str, Any], product: str
    ) -> None:
        """Build single core image."""
        if "defconfig" in cores[core]:
            build_dir = (
                product
                + "-"
                + self._cfg_values[product]["name"]
                + "-"
                + cores[core]["name"]
            )

            cfg_build_dir = self._cfg_values["config"].get("build_dir", None)
            if not cfg_build_dir:  # pragma: no cover
                print("ERROR: not found build_dir in YAML configuration!")
                sys.exit(1)

            cfg_cwd = self._cfg_values["config"].get("cwd", None)
            if not cfg_cwd:  # pragma: no cover
                print("ERROR: not found cwd in YAML configuration!")
                sys.exit(1)

            build_path = os.path.join(cfg_build_dir, build_dir)
            build_cfg = cores[core]["defconfig"]
            logger.info(
                f"build image " f"conf: {build_cfg}, out: {build_path}"
            )

            nuttx_dir = os.path.join(cfg_cwd, "nuttx")
            nuttx_elf_path = os.path.join(build_path, "nuttx")
            nuttx_conf_path = os.path.join(build_path, ".config")

            already_build = False
            if os.path.isfile(nuttx_elf_path) and os.path.isfile(
                nuttx_conf_path
            ):
                already_build = True  # pragma: no cover

            # get defines passed to cmake
            defines = {"BOARD_CONFIG": build_cfg}
            custom_defines = cores[core].get("dcmake", [])

            for d in custom_defines:
                defines[d[0]] = d[1]  # pragma: no cover

            if not already_build or self._rebuild:  # pragma: no cover
                # configure build
                self._run_cmake(
                    source=nuttx_dir,
                    build=build_path,
                    generator="Ninja",
                    defines=defines,
                )

                # build
                self._run_build(build_path)

            # add elf and conf path
            cores[core]["elf_path"] = nuttx_elf_path
            cores[core]["conf_path"] = nuttx_conf_path

    def _reboot_core(
        self, core: str, cores: Dict[str, Any]
    ) -> None:  # pragma: no cover
        """Reboot single core."""
        reboot_cmd = cores[core].get("reboot", None)
        if reboot_cmd:
            cmd = reboot_cmd.split()
            logger.info(f"reboot core cmd: {cmd}")
            self._run_command(cmd, env=None)

    def _flash_core(
        self, core: str, cores: Dict[str, Any]
    ) -> None:  # pragma: no cover
        """Flash single core image."""
        flash_cmd = cores[core].get("flash", None)
        if flash_cmd:
            img_path = Path(cores[core]["elf_path"])
            image_hex = str(img_path.parent) + "/nuttx.hex"
            image_bin = str(img_path.parent) + "/nuttx.bin"

            flash_cmd = flash_cmd.replace(self.IMAGE_BIN_STR, image_bin)
            flash_cmd = flash_cmd.replace(self.IMAGE_HEX_STR, image_hex)

            cmd = flash_cmd.split()

            logger.info(f"flash image cmd: {cmd}")
            self._run_command(cmd, env=None)

    def need_build(self) -> bool:
        """Check if we need build something."""
        for product in self._cfg_values:
            if "product" in product:
                cores = self._cfg_values[product]["cores"]
                for core in cores:
                    if cores[core].get("defconfig", None):
                        return True
        return False

    def build_all(self) -> None:
        """Build all defconfigs from configuration file."""
        for product in self._cfg_values:
            if "product" in product:
                cores = self._cfg_values[product]["cores"]
                for core in cores:
                    self._build_core(core, cores, product)

    def flash_all(self) -> None:
        """Flash all available images."""
        for product in self._cfg_values:
            if "product" in product:
                cores = self._cfg_values[product]["cores"]
                for core in cores:
                    # flash core image
                    self._flash_core(core, cores)
                    # reboot after flash
                    self._reboot_core(core, cores)

    def new_conf(self) -> Dict[str, Any]:
        """Get modified YAML config."""
        return self._cfg_values
