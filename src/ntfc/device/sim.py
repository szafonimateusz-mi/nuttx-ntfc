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

"""Host-based simulator implementation."""

from typing import TYPE_CHECKING

from .host import DeviceHost

if TYPE_CHECKING:
    from ntfc.coreconfig import CoreConfig

###############################################################################
# Class: DeviceSim
###############################################################################


class DeviceSim(DeviceHost):
    """This class implements host-based sim emulator."""

    def __init__(self, conf: "CoreConfig"):
        """Initialize sim emulator device."""
        DeviceHost.__init__(self, conf)

    def _start_impl(self) -> None:
        """Start sim emulator implementation."""
        elf = self._conf.elf_path
        if not elf:
            raise IOError

        cmd = [elf]
        uptime = self._conf.uptime

        # open host-based emulation
        self.host_open(cmd, uptime)

    @property
    def name(self) -> str:
        """Get device name."""
        return "sim"

    def _write(self, data: bytes) -> None:
        """Write to the host device."""
        if not self.dev_is_health():
            return

        assert self._child

        # send char by char to avoid line length full
        for c in data:
            self._child.send(bytes([c]))

        # add new line if missing
        if data[-1] != ord("\n"):
            # sometimes new line send to sim is missing
            # so we have to send more than one new line
            self._child.send(b"\n")
            self._child.send(b"\n")
