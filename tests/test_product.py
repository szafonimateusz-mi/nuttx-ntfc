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

import re
from unittest.mock import patch

import pytest

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.product import Product


def test_product_initinval(config_dummy):

    with pytest.raises(TypeError):
        _ = Product(None, None)

    with pytest.raises(TypeError):
        _ = Product(1, None)

    with pytest.raises(TypeError):
        _ = Product(None, 1)

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        _ = Product(mockdevice, config_dummy.product[0])


def test_product_get_core_info(config_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )

        p = Product(dev, config_dummy.product[0])

        # send_cmd_read_until_pattern failed
        assert p.get_core_info() == ()

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, "xxx"
        )
        assert p.get_core_info() == ()

        dev.prompt = b"dummy"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n0 1",
        )
        assert p.get_core_info() == ("0", "1")
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n2 3",
        )
        assert p.get_core_info() == ("2", "3")


def test_product_send_command(config_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.prompt = b"NSH> "
        dev.no_cmd = "command not found"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )
        p = Product(dev, config_dummy.product[0])

        # empty command
        with pytest.raises(ValueError):
            p.sendCommand(None)

        # should work with or without /n
        # pass retcode from send_cmd_read_until_pattern
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS
        )
        assert p.sendCommand("test\n") == CmdStatus.SUCCESS
        assert p.sendCommand("test") == CmdStatus.SUCCESS
        assert p.sendCommand("test", "") == CmdStatus.SUCCESS

        # timeout
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )
        assert p.sendCommand("test\n") == CmdStatus.TIMEOUT

        # command not found
        tmp = re.compile("command not found", 0).search("command not found")
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, tmp
        )
        assert p.sendCommand("test") == CmdStatus.NOTFOUND


def test_product_send_command_read_until_pattern(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev._main_prompt = "nsh>"
        p = Product(dev, config_dummy.product[0])

        with pytest.raises(ValueError):
            p.sendCommandReadUntilPattern("")

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.NOTFOUND
        )
        assert p.sendCommandReadUntilPattern("test", "test") == CmdReturn(
            CmdStatus.NOTFOUND
        )

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS
        )
        assert p.sendCommandReadUntilPattern("test", "test") == CmdReturn(
            CmdStatus.SUCCESS
        )


def test_product_send_ctrl_cmd(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        with pytest.raises(ValueError):
            p.sendCtrlCmd("")

        with pytest.raises(ValueError):
            p.sendCtrlCmd("aaa")

        dev.sendCtrlCmd.return_value = 0
        assert p.sendCtrlCmd("a") is None

        dev.sendCtrlCmd.return_value = 1
        assert p.sendCtrlCmd("a") is None


def test_product_switch_core(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.no_cmd = ""
        p = Product(dev, config_dummy.product[0])

        with pytest.raises(ValueError):
            p.switch_core("")

        p.init()

        assert p.switch_core("") == -1

        p._main_core = "AAA"
        assert p.switch_core("aaa") == 0

        p._main_core = "bbb"
        p._cores = ["bbb", "ccc"]
        assert p.switch_core("aaa") == -1

        p._main_core = "bbb"
        p._cores = ["bbb", "ccc"]
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.NOTFOUND
        )
        assert p.switch_core("ccc") == CmdStatus.NOTFOUND
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS
        )
        assert p.switch_core("ccc") == CmdStatus.SUCCESS


def test_product_get_current_prompt(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.NOTFOUND
        )
        assert p.get_current_prompt() == ">"

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, re.match(rb"(\S+)>", b"nsh>")
        )
        assert p.get_current_prompt() == "nsh>"


def test_product_reboot(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.reboot.return_value = False
        assert p.reboot() is False

        dev.reboot.return_value = True
        assert p.reboot() is True


def test_product_busyloop(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.busyloop = False
        assert p.busyloop is False
        dev.busyloop = True
        assert p.busyloop is True


def test_product_crash(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.crash = False
        assert p.crash is False
        dev.crash = True
        assert p.crash is True


def test_product_notalive(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.notalive = False
        assert p.notalive is False
        dev.notalive = True
        assert p.notalive is True


def test_product_device_status_checker(config_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = Product(dev, config_dummy.product[0])

        dev.busyloop = False
        dev.crash = False
        dev.notalive = False
        assert p.device_status == "NORMAL"

        dev.busyloop = True
        dev.crash = False
        dev.notalive = False
        assert p.device_status == "BUSYLOOP"

        dev.busyloop = False
        dev.crash = True
        dev.notalive = False
        assert p.device_status == "CRASH"

        dev.busyloop = False
        dev.crash = False
        dev.notalive = True
        assert p.device_status == "NOTALIVE"
