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

"""Dummy device for testing."""

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.device.state import DeviceState, DeviceStateManager

###############################################################################
# Class: DeviceDummy
###############################################################################


class DeviceDummy:  # pragma: no cover
    """Dummy device."""

    def __init__(self, _):
        """Initialize dummy device."""
        # Create state manager
        self._state_mgr = DeviceStateManager(
            heartbeat_send_fn=self.send_cmd_read_until_pattern
        )

        # Device state flags
        self._open = False
        self._interactive_mode = False

    def start(self) -> None:
        """Start dummy device."""
        self._open = True

    def send_cmd_read_until_pattern(
        self, cmd: bytes, pattern: bytes, timeout: int
    ):
        """Send command to device and read until the specified pattern."""
        return CmdReturn(CmdStatus.NOTFOUND)

    def send_ctrl_cmd(self, cmd: str):
        """Send control command to the device."""
        return CmdStatus.NOTFOUND

    @property
    def name(self) -> str:
        """Get device name."""
        return "dummy"

    @property
    def prompt(self) -> str:
        """Return target device prompt."""
        return "NSH> "

    @property
    def no_cmd(self) -> str:
        """Return command not found string."""
        return "command not found"

    @property
    def busyloop(self):
        """Check if the device is in busy loop."""
        return False

    @property
    def flood(self):
        """Check if the device is in flood state."""
        return False

    @property
    def crash(self):
        """Check if the device is crashed."""
        return False

    @property
    def notalive(self) -> bool:
        """Check if the device is dead."""
        return False

    def poweroff(self):
        """Poweroff the device."""
        self._open = False
        return -1

    def reboot(self, timeout: int):
        """Reboot the device."""
        self._open = True
        return -1

    def start_log_collect(self, logs) -> None:
        """Start device log collector."""

    def stop_log_collect(self) -> None:
        """Stop device log collector."""

    ###
    # Device State Monitoring Methods (for testing)
    ###

    def check_device_state(self) -> DeviceState:
        """Check current device state."""
        return self._state_mgr.get_current_state()

    def enable_heartbeat_monitoring(
        self, interval: float = 60, threshold: int = 3
    ) -> None:
        """Enable heartbeat monitoring."""
        self._state_mgr.enable_heartbeat(interval, threshold)

    def disable_heartbeat_monitoring(self) -> None:
        """Disable heartbeat monitoring."""
        self._state_mgr.disable_heartbeat()

    def set_interactive_mode(self, enabled: bool) -> None:
        """Set interactive mode state."""
        self._interactive_mode = enabled
