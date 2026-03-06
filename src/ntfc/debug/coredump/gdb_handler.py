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

"""GDB-based coredump handler."""

from typing import TYPE_CHECKING

from ntfc.debug.coredump.base import CoredumpHandler

if TYPE_CHECKING:
    from pathlib import Path

    from ntfc.debug.gdb.controller import GdbController


###############################################################################
# Class: GdbHandler
###############################################################################


class GdbHandler(CoredumpHandler):
    """Coredump handler that uses a running :class:`GdbController`.

    :param controller: GDB controller instance used to generate coredumps.
    """

    def __init__(self, controller: "GdbController") -> None:
        """Initialize :class:`GdbHandler`.

        :param controller: GDB controller used for coredump generation.
        """
        super().__init__()
        self._controller = controller

    @property
    def name(self) -> str:
        """Return the handler name ``"gdb"``.

        :return: ``"gdb"``
        """
        return "gdb"

    @property
    def priority(self) -> int:
        """Return the handler priority ``10``.

        :return: ``10``
        """
        return 10

    def is_available(self) -> bool:
        """Return ``True`` when the GDB controller process is running.

        :return: Availability flag.
        """
        return self._controller.is_running()

    def collect(self, output_dir: "Path", prefix: str) -> bool:
        """Generate a coredump via the GDB controller.

        :param output_dir: Directory where the coredump file is written.
        :param prefix: Filename prefix for the output file.
        :return: ``True`` if a corefile was created, ``False`` otherwise.
        """
        result = self._controller.generate_coredump(output_dir, prefix)
        return result is not None
