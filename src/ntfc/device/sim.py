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
    from ntfc.envconfig import ProductConfig

###############################################################################
# Class: DeviceSim
###############################################################################


class DeviceSim(DeviceHost):
    """This class implements host-based sim emulator."""

    def __init__(self, conf: "ProductConfig"):
        """Initialize sim emulator device."""
        DeviceHost.__init__(self, conf)
        self._conf = conf

    def start(self) -> None:
        """Start sim emulator."""
        elf = self._conf.core(cpu=0)["elf_path"]
        if not elf:
            raise IOError

        cmd = [elf]
        uptime = self._conf.core(cpu=0).get("uptime", 3)

        # open host-based emulation
        self.host_open(cmd, uptime)

    @property
    def name(self) -> str:
        """Get device name."""
        return "sim"
