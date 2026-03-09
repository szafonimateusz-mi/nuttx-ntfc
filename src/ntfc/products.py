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

"""Products handler class implementation."""

from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.log.logger import logger
from ntfc.parallel import run_parallel

if TYPE_CHECKING:
    from ntfc.product import Product
    from ntfc.type_defs import PatternLike

###############################################################################
# Class: ProductsHandler
###############################################################################


class ProductsHandler:
    """This class implements work-around to run all products at once.

    It can be useful to run tests for many DUT at once.
    Methods are executed in parallel using threads with result collection.
    """

    def __init__(self, products: List["Product"]):
        """Initialize all products handler."""
        self._products = products

    def sendCommand(  # noqa: N802
        self,
        cmd: str,
        expects: Optional[Union[str, List[str]]] = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
        flag: str = "",
        match_all: bool = True,
        regexp: bool = False,
    ) -> CmdStatus:
        """Send command to all products in parallel."""
        results = run_parallel(
            self._products,
            lambda p: p.sendCommand(
                cmd, expects, args, timeout, flag, match_all, regexp
            ),
        )

        for idx, ret in enumerate(results):
            if ret != CmdStatus.SUCCESS:
                logger.info(
                    f"sendCommand failed for product {self._products[idx]}"
                )
                return cast("CmdStatus", ret)

        return CmdStatus.SUCCESS

    def sendCommandReadUntilPattern(  # noqa: N802
        self,
        cmd: str,
        pattern: "Optional[PatternLike]" = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
    ) -> CmdReturn:
        """Send command to all products in parallel."""
        results = run_parallel(
            self._products,
            lambda p: p.sendCommandReadUntilPattern(
                cmd, pattern, args, timeout
            ),
        )

        for idx, ret in enumerate(results):
            if ret.status != CmdStatus.SUCCESS:
                logger.info(
                    f"sendCommandReadUntilPattern failed for "
                    f"product {self._products[idx]}"
                )
                return cast("CmdReturn", ret)

        return CmdReturn(CmdStatus.SUCCESS)

    def readUntilPattern(  # noqa: N802
        self,
        pattern: "PatternLike",
        timeout: int = 30,
        fail_pattern: "Optional[PatternLike]" = None,
    ) -> CmdReturn:
        """Read device output until pattern on all products in parallel."""
        results = run_parallel(
            self._products,
            lambda p: p.readUntilPattern(pattern, timeout, fail_pattern),
        )

        for idx, ret in enumerate(results):
            if ret.status != CmdStatus.SUCCESS:
                logger.info(
                    f"readUntilPattern failed for "
                    f"product {self._products[idx]}"
                )
                return cast("CmdReturn", ret)

        return CmdReturn(CmdStatus.SUCCESS)

    def sendCtrlCmd(self, ctrl_char: str) -> None:  # noqa: N802
        """Send ctrl command to all products in parallel."""
        run_parallel(self._products, lambda p: p.sendCtrlCmd(ctrl_char))

    @property
    def busyloop(self) -> bool:
        """Get busyloop flag from products in parallel."""
        results = run_parallel(self._products, lambda p: p.busyloop)
        for idx, result in enumerate(results):
            if result:
                logger.info(f"busyloop for product {self._products[idx]}")
                return True
        return False

    @property
    def flood(self) -> bool:
        """Get flood flag from products in parallel."""
        results = run_parallel(self._products, lambda p: p.flood)
        for idx, result in enumerate(results):
            if result:
                logger.info(f"flood for product {self._products[idx]}")
                return True
        return False

    @property
    def crash(self) -> bool:
        """Get crash flag from products in parallel."""
        results = run_parallel(self._products, lambda p: p.crash)
        for idx, result in enumerate(results):
            if result:
                logger.info(f"crash for product {self._products[idx]}")
                return True
        return False

    @property
    def notalive(self) -> bool:
        """Get notalive flag from products in parallel."""
        results = run_parallel(self._products, lambda p: p.notalive)
        for idx, result in enumerate(results):
            if result:
                logger.info(f"notalive for product {self._products[idx]}")
                return True
        return False

    def reboot(self) -> bool:
        """Run reboot for all products in parallel."""
        results = run_parallel(self._products, lambda p: p.reboot())
        for idx, result in enumerate(results):
            if not result:
                logger.info(f"reboot failed for product {self._products[idx]}")
        return True

    def force_panic(self) -> bool:
        """Force panic for all products in parallel."""
        results = run_parallel(self._products, lambda p: p.force_panic())
        for idx, result in enumerate(results):
            if not result:
                logger.info(
                    f"force_panic failed for product {self._products[idx]}"
                )
        return True

    @property
    def cur_name(self) -> str:
        """Get current product."""
        # TODO: many products not supported yet
        return self._products[0].name

    @property
    def cur_core(self) -> Optional[str]:
        """Get current core."""
        # TODO: many products not supported yet
        return self._products[0].cur_core

    @property
    def conf(self) -> Any:
        """Get configuration of the first product."""
        # Proxy to first product's configuration
        return self._products[0].conf

    @property
    def cores(self) -> Any:
        """Get cores list of the first product."""
        # Proxy to first product's cores
        return self._products[0].cores

    def core(self, cpu: int = 0) -> Any:
        """Get core from the first product by index.

        :param cpu: Core index (0, 1, 2, ...)
        :return: ProductCore instance
        """
        # Proxy to first product's core
        return self._products[0].core(cpu)
