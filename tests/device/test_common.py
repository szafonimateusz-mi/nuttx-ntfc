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

from types import SimpleNamespace
from unittest.mock import patch

from ntfc.device.common import CmdReturn, CmdStatus, DeviceCommon

g_mock_read = b""


class DeviceMock(DeviceCommon):

    def __init__(self, _):
        """Mock."""

        DeviceCommon.__init__(self, _)

    def _read(self, _=0):
        """Mock."""
        return g_mock_read

    def _write(self, _):
        """Mock."""

    def _write_ctrl(self, _):
        """Mock."""

    def _dev_is_health_priv(
        self,
    ):
        """Mock."""

    def start(self):
        """Mock."""

    def name(self):
        """Mock."""

    def notalive(self):
        """Mock."""

    def poweroff(self):
        """Mock."""

    def reboot(self, _):
        """Mock."""


def test_device_common_data():

    a = CmdStatus(0)
    assert a == 0
    assert str(a) == "SUCCESS"

    b = CmdReturn(0)
    c1, c2, c3 = b
    assert (c1, c2, c3) == (0, None, "")

    b = CmdReturn(-1, None, "test")
    c1, c2, c3 = b
    assert (c1, c2, c3) == (-1, None, "test")


def test_device_common_init():

    with patch("ntfc.envconfig.EnvConfig") as mockdevice:
        config = mockdevice.return_value

        d = DeviceMock(config)
        assert d is not None

        assert d.crash is False
        assert d.busyloop is False
        assert d.flood is False


def test_device_common_send_cmd_pattern():

    with patch("ntfc.envconfig.EnvConfig") as mockdevice:

        global g_mock_read

        config = mockdevice.return_value

        dev = DeviceMock(config)
        assert dev is not None

        assert dev.flood is False

        g_mock_read = b"x" * 10000
        ret = dev.send_cmd_read_until_pattern(b"", b"x", 1)
        assert ret.status == CmdStatus.SUCCESS

        g_mock_read = b"x" * 10000
        ret = dev.send_cmd_read_until_pattern(b"", b"y", 1)
        assert ret.status == CmdStatus.TIMEOUT

        assert dev.flood is True


def test_device_common_panic_char():

    with patch("ntfc.device.common.get_os") as mock_get_os:
        mock_get_os.return_value = SimpleNamespace(panic_char="X")

        with patch("ntfc.envconfig.EnvConfig") as mockdevice:
            config = mockdevice.return_value

            dev = DeviceMock(config)
            assert dev.panic_char == "X"


# TODO: missing tests
