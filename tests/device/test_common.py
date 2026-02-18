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

from io import StringIO
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

    def _start_impl(self):
        """Mock."""

    def name(self):
        """Mock."""

    def notalive(self):
        """Mock."""

    def _poweroff_impl(self):
        """Mock."""

    def _reboot_impl(self, _):
        """Mock."""
        return False


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

        log = StringIO()
        dev.start_log_collect({"device": log, "console": log})

        g_mock_read = b"x" * 10000
        ret = dev.send_cmd_read_until_pattern(b"", b"x", 1)
        assert ret.status == CmdStatus.SUCCESS

        g_mock_read = b"x" * 10000
        ret = dev.send_cmd_read_until_pattern(b"", b"y", 1)
        assert ret.status == CmdStatus.TIMEOUT

        assert dev.flood is True
        assert "fault detected: flood" in log.getvalue()

        g_mock_read = b"x" * 10000
        ret = dev.send_cmd_read_until_pattern(b"", b"y", 1)
        assert ret.status == CmdStatus.TIMEOUT


def test_device_common_panic_char():

    with patch("ntfc.device.common.get_os") as mock_get_os:
        mock_get_os.return_value = SimpleNamespace(panic_char="X")

        with patch("ntfc.envconfig.EnvConfig") as mockdevice:
            config = mockdevice.return_value

            dev = DeviceMock(config)
            assert dev.panic_char == "X"


def test_device_common_log_helpers():

    with patch("ntfc.envconfig.EnvConfig") as mockdevice:
        config = mockdevice.return_value

        dev = DeviceMock(config)
        log = StringIO()
        dev.start_log_collect({"device": log, "console": log})

        dev._log_device_event("event")
        dev._log_console_input(b"cmd\n")
        dev.log_event("public")

        dev._log_runtime_event("reboot")
        dev._mark_started()
        dev._log_runtime_event("poweroff")
        assert dev.reboot() is False

        output = log.getvalue()
        assert "event" in output
        assert "console_in" in output
        assert "public" in output
        assert "runtime=unknown" in output
        assert "poweroff runtime=" in output

        dev.start_log_collect({})
        dev._log_device_event("no-device-log")
        dev._log_console_input(b"no-device-log")

        dev.stop_log_collect()
        dev._log_device_event("buffered")
        dev._log_console_input(b"buffered-cmd")
        dev.start_log_collect({})
        dev.start_log_collect({"device": log, "console": log})
        output = log.getvalue()
        assert "buffered" in output
        assert "buffered-cmd" in output


# TODO: missing tests
