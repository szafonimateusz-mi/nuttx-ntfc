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

"""Product class implementation."""

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Union,
)

from ntfc.cores import CoresHandler
from ntfc.productconfig import ProductConfig

if TYPE_CHECKING:
    from ntfc.core import ProductCore
    from ntfc.device.common import CmdReturn, CmdStatus
    from ntfc.log.handler import LogHandler


###############################################################################
# Class: Product
###############################################################################


class Product:
    """This class implements product under test."""

    def __init__(self, conf: "ProductConfig") -> None:
        """Initialize product under test.

        :param conf: ProductConfig instance
        """
        if not isinstance(conf, ProductConfig):
            raise TypeError("Config instance is required")

        self._name = conf.name
        self._conf = conf
        self._cores = CoresHandler(conf)

    def __str__(self) -> str:
        """Get string for object."""
        return f"Product: {self._name}"

    def init(self) -> None:
        """Initialize all cores."""
        self._cores.init()

    def start(self) -> None:
        """Start for all cores."""
        self._cores.start()

    @property
    def cores(self) -> List[str]:
        """List of cores."""
        return self._cores.cores

    @property
    def conf(self) -> "ProductConfig":
        """Get product configuration."""
        return self._conf

    @property
    def name(self) -> str:
        """Get product name."""
        return self._name

    def core(self, cpu: int = 0) -> "ProductCore":
        """Get product core handler."""
        return self._cores.core(cpu)

    def sendCommand(  # noqa: N802
        self,
        cmd: str,
        expects: Optional[Union[str, List[str]]] = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
        flag: str = "",
        match_all: bool = True,
        regexp: bool = False,
    ) -> "CmdStatus":
        """Call for all cores."""
        return self._cores.sendCommand(
            cmd, expects, args, timeout, flag, match_all, regexp
        )

    def sendCommandReadUntilPattern(  # noqa: N802
        self,
        cmd: str,
        pattern: Optional[Union[str, bytes, List[Union[str, bytes]]]] = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
    ) -> "CmdReturn":
        """Call for all cores."""
        return self._cores.sendCommandReadUntilPattern(
            cmd, pattern, args, timeout
        )

    def readUntilPattern(  # noqa: N802
        self,
        pattern: Union[str, bytes, List[Union[str, bytes]]],
        timeout: int = 30,
        fail_pattern: Optional[
            Union[str, bytes, List[Union[str, bytes]]]
        ] = None,
    ) -> "CmdReturn":
        """Call for all cores."""
        return self._cores.readUntilPattern(pattern, timeout, fail_pattern)

    def sendCtrlCmd(self, ctrl_char: str) -> None:  # noqa: N802
        """Call for all cores."""
        return self._cores.sendCtrlCmd(ctrl_char)

    def reboot(self, timeout: int = 30) -> bool:
        """Call for all cores."""
        return self._cores.reboot(timeout)

    def force_panic(self, timeout: int = 30) -> bool:
        """Call for all cores."""
        return self._cores.force_panic(timeout)

    @property
    def busyloop(self) -> bool:
        """Call for all cores."""
        return self._cores.busyloop

    @property
    def flood(self) -> bool:
        """Call for all cores."""
        return self._cores.flood

    @property
    def crash(self) -> bool:
        """Call for all cores."""
        return self._cores.crash

    @property
    def notalive(self) -> bool:
        """Call for all cores."""
        return self._cores.notalive

    @property
    def cur_core(self) -> Optional[str]:
        """Call for all cores."""
        return self._cores.cur_core

    def start_log_collect(self, logs: "Dict[str, LogHandler]") -> None:
        """Start log collection for product."""
        self._cores.start_log_collect(logs)

    def stop_log_collect(self) -> None:
        """Stop log collection for product."""
        self._cores.stop_log_collect()
