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
from unittest.mock import MagicMock, patch

import pytest

from ntfc.core import ProductCore
from ntfc.device.common import CmdReturn, CmdStatus


def test_core_init(envconfig_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value

        with pytest.raises(TypeError):
            _ = ProductCore(None, envconfig_dummy.product[0].cfg_core(0))

        with pytest.raises(TypeError):
            _ = ProductCore(dev, None)

        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        p.init()

        assert p.__str__() == "ProductCore: dummy"
        assert p.cores == ("core0",)
        assert p.device is not None
        assert p.prompt is not None
        assert p.conf is not None


def test_core_internals(envconfig_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )
        dev.no_cmd = "command not found"

        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        assert p._prepare_command("aaa", None) == "aaa"
        assert p._prepare_command("aaa", "bbb") == "aaa bbb"
        assert p._prepare_command("aaa", ["bbb", "ccc"]) == "aaa bbb ccc"

        assert (
            p._build_expect_pattern(["aaa", "bbb"], False, False)
            == "(aaa|bbb)"
        )
        assert (
            p._build_expect_pattern(["aaa", "bbb"], True, False)
            == "(?=.*aaa)(?=.*bbb)"
        )
        assert (
            p._build_expect_pattern(["aaa", "bbb"], True, True)
            == "(?=.*aaa)(?=.*bbb)"
        )
        assert (
            p._build_expect_pattern(["aaa", "bbb"], False, True) == "(aaa|bbb)"
        )

        assert p._encode_for_device("aaa", ["bbb", "ccc"]) == (
            b"aaa",
            b"bbbccc",
        )
        assert p._encode_for_device("aaa", [b"bbb", b"ccc"]) == (
            b"aaa",
            b"bbbccc",
        )
        assert p._encode_for_device("aaa", "bbb") == (b"aaa", b"bbb")
        assert p._encode_for_device("aaa", b"bbb") == (b"aaa", b"bbb")

        assert p._match_not_found(None) is False
        a = re.match(rb"test", b"nsh>")
        assert p._match_not_found(a) is False
        b = re.match(rb"command not found", b"command not found")
        assert p._match_not_found(b) is True


def test_core_send_command(envconfig_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.prompt = b"NSH> "
        dev.no_cmd = "command not found"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

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


def test_core_send_command_read_until_pattern(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev._main_prompt = "nsh>"
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

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


def test_core_send_ctrl_cmd(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        with pytest.raises(ValueError):
            p.sendCtrlCmd("")

        with pytest.raises(ValueError):
            p.sendCtrlCmd("aaa")

        dev.send_ctrl_cmd.return_value = CmdStatus.TIMEOUT
        assert p.sendCtrlCmd("a") is None

        dev.send_ctrl_cmd.return_value = CmdStatus.SUCCESS
        assert p.sendCtrlCmd("a") is None


def test_core_reboot(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.reboot.return_value = False
        assert p.reboot() is False

        dev.reboot.return_value = True
        assert p.reboot() is True


def test_core_busyloop(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.busyloop = False
        assert p.busyloop is False
        dev.busyloop = True
        assert p.busyloop is True


def test_core_crash(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.crash = False
        assert p.crash is False
        dev.crash = True
        assert p.crash is True


def test_core_notalive(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.notalive = False
        assert p.notalive is False
        dev.notalive = True
        assert p.notalive is True


def test_core_status_checker(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.busyloop = False
        dev.crash = False
        dev.notalive = False
        assert p.status == "NORMAL"

        dev.busyloop = True
        dev.crash = False
        dev.notalive = False
        assert p.status == "BUSYLOOP"

        dev.busyloop = False
        dev.crash = True
        dev.notalive = False
        assert p.status == "CRASH"

        dev.busyloop = False
        dev.crash = False
        dev.notalive = True
        assert p.status == "NOTALIVE"


def test_core_get_core_info(envconfig_dummy):

    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )

        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        assert p.cur_core is None

        # send_cmd_read_until_pattern failed
        assert p.get_core_info() == ()

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, "xxx"
        )
        assert p.get_core_info() == ()
        assert p.cur_core is None

        dev.prompt = b"dummy"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n",
        )
        assert p.get_core_info() == ()
        assert p.cur_core is None

        dev.prompt = b"dummy"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n0 1",
        )
        assert p.get_core_info() == ("0", "1")
        assert p.cur_core is None

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n2 3",
        )
        assert p.get_core_info() == ("2", "3")
        assert p.cur_core is None

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS,
            None,
            "Local CPU Remote CPU\n2 3",
        )
        assert p.get_core_info() == ("2", "3")
        assert p.cur_core is None

        p.init()
        assert p.cur_core == "2"


def test_core_switch_core(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.no_cmd = ""
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        with pytest.raises(ValueError):
            p.switch_core("")

        p.init()

        assert p.switch_core("") == -1

        p._core0 = "AAA"
        assert p.switch_core("aaa") == 0

        p._core0 = "bbb"
        p._cores = ["bbb", "ccc"]
        assert p.switch_core("aaa") == -1

        p._core0 = "bbb"
        p._cores = ["bbb", "ccc"]
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.NOTFOUND
        )
        assert p.switch_core("ccc") == CmdStatus.NOTFOUND
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS
        )
        assert p.switch_core("ccc") == CmdStatus.SUCCESS


def test_core_get_current_prompt(envconfig_dummy):
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.NOTFOUND
        )
        assert p.get_current_prompt() == ">"

        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, re.match(rb"(\S+)>", b"nsh>")
        )
        assert p.get_current_prompt() == "nsh>"


def test_core_check_cmd_without_elf_parser(envconfig_dummy):
    """Test check_cmd fallback when ELF parser is not available."""
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        # Set required attributes (but NOT elf_parser)
        dev.prompt = b"nsh>"
        dev.no_cmd = "command not found"
        # IMPORTANT: Explicitly set elf_parser to None to prevent MagicMock
        # from auto-creating it as a truthy attribute
        dev.elf_parser = None

        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        # Mock send_cmd_read_until_pattern for help command
        # Note: ProductCore.sendCommandReadUntilPattern calls dev.send_cmd_read_until_pattern
        help_output = "Available commands: free ps\n"
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, help_output
        )

        # Test command found in help output
        assert p.check_cmd("free") is True

        # Reset the mock for next call
        dev.send_cmd_read_until_pattern.reset_mock()
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, help_output
        )
        assert p.check_cmd("free|ps") is True

        # Reset the mock for next call
        dev.send_cmd_read_until_pattern.reset_mock()
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, help_output
        )
        assert p.check_cmd("ps") is True

        # Reset the mock for next call
        dev.send_cmd_read_until_pattern.reset_mock()
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.SUCCESS, None, help_output
        )

        # Test command not found in help output
        assert p.check_cmd("nonexistent") is False

        # Test with failed help command
        dev.send_cmd_read_until_pattern.return_value = CmdReturn(
            CmdStatus.TIMEOUT
        )
        assert p.check_cmd("test") is False


def test_core_check_cmd_with_elf_parser(envconfig_dummy):
    """Test check_cmd with ELF parser available."""
    with patch("ntfc.device.common.DeviceCommon") as mockdevice:
        dev = mockdevice.return_value
        dev.prompt = b"nsh>"
        dev.no_cmd = "command not found"

        # Create a mock ELF parser
        mock_elf_parser = MagicMock()
        mock_elf_parser.has_symbol.return_value = False

        # Set elf_parser on the device
        dev.elf_parser = mock_elf_parser

        p = ProductCore(dev, envconfig_dummy.product[0].cfg_core(0))

        # Test command not found
        assert p.check_cmd("free") is False
        mock_elf_parser.has_symbol.assert_called_with("free")

        # Test command found
        mock_elf_parser.has_symbol.return_value = True
        assert p.check_cmd("ps") is True
        mock_elf_parser.has_symbol.assert_called_with("ps")

        # Test cmocka pattern (should append _main)
        mock_elf_parser.has_symbol.return_value = True
        assert p.check_cmd("test_cmocka") is True
        mock_elf_parser.has_symbol.assert_called_with("test_cmocka_main")

        # Test alternatives with pipe
        mock_elf_parser.has_symbol.side_effect = [False, True]
        assert p.check_cmd("test1|test2") is True

        # Test regex wildcard pattern
        mock_elf_parser.has_symbol.side_effect = None
        mock_elf_parser.has_symbol.return_value = True
        import re

        assert p.check_cmd("test.*") is True
        # The pattern should be compiled as regex
        call_args = mock_elf_parser.has_symbol.call_args
        assert isinstance(call_args[0][0], re.Pattern)

        # Test all alternatives not found
        mock_elf_parser.has_symbol.return_value = False
        assert p.check_cmd("nonexistent1|nonexistent2") is False
