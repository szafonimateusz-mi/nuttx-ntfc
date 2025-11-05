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

"""NuttX target device implementation."""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ntfc.envconfig import ProductConfig

###############################################################################
# Class: DeviceNuttx
###############################################################################


class DeviceNuttx:
    """This class implements NuttX target device."""

    _PROMPT = b"nsh>"
    _NO_CMD = "command not found"
    _HELP_CMD = b"help"
    _POWEROFF_CMD = b"poweroff"
    _REBOOT_CMD = b"reboot"
    _UNAME_CMD = b"uname -o"
    _UNAME_RESP = b"NuttX"
    _CRASH_KEYS = [b"Assertion"]

    def __init__(self, conf: "ProductConfig"):
        """Initialize NuttX device."""
        self._conf = conf

    @property
    def prompt(self) -> bytes:
        """Get prompt."""
        return self._PROMPT

    @property
    def no_cmd(self) -> str:
        """Get command not found string."""
        return self._NO_CMD

    @property
    def help_cmd(self) -> bytes:
        """Get help command."""
        return self._HELP_CMD

    @property
    def poweroff_cmd(self) -> bytes:
        """Get poweroff command."""
        return self._POWEROFF_CMD

    @property
    def reboot_cmd(self) -> bytes:
        """Get reboot command."""
        return self._REBOOT_CMD

    @property
    def uname_cmd(self) -> bytes:
        """Get uname command."""
        return self._UNAME_CMD

    @property
    def crash_keys(self) -> List[bytes]:
        """Get keys related to OS crash."""
        return self._CRASH_KEYS
