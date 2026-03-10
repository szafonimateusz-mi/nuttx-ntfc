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

"""Tests for ntfc.parsers.custom."""

from types import SimpleNamespace

import pytest

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.parsers.custom import (
    CustomParser,
    CustomParserConfig,
    _check_named_groups,
)

_LIST_PATTERN = r"TEST:\s+(?P<name>\w+)"
_RESULT_PATTERN = r"(?P<status>PASS|FAIL)\s+(?P<name>\w+)"
_LIST_SUITE_PATTERN = r"\[(?P<suite>\w+)\]\s+(?P<name>\w+)"


def _make_config(**overrides) -> CustomParserConfig:
    defaults = dict(
        list_pattern=_LIST_PATTERN,
        result_pattern=_RESULT_PATTERN,
    )
    defaults.update(overrides)
    return CustomParserConfig(**defaults)


def _make_core(output: str = "", status: CmdStatus = CmdStatus.SUCCESS):
    cmd_return = CmdReturn(status=status, output=output)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


def test_check_named_groups_valid():
    _check_named_groups(r"(?P<name>\w+)", {"name"}, "list_pattern")


def test_check_named_groups_invalid_regex():
    with pytest.raises(ValueError, match="not a valid regex"):
        _check_named_groups(r"(?P<name", {"name"}, "list_pattern")


def test_check_named_groups_missing_group():
    with pytest.raises(ValueError, match="missing required named group"):
        _check_named_groups(r"(\w+)", {"name"}, "list_pattern")


def test_check_named_groups_missing_multiple():
    with pytest.raises(ValueError, match="name"):
        _check_named_groups(r"(\w+)", {"name", "status"}, "result_pattern")


def test_config_defaults():
    cfg = _make_config()
    assert cfg.list_args == "--list"
    assert cfg.run_args == "{name}"
    assert cfg.filter_args == "{filter}"
    assert cfg.success_value == "PASS"


def test_config_custom_values():
    cfg = _make_config(
        list_args="ls",
        run_args="run {name}",
        filter_args="filter {filter}",
        success_value="OK",
    )
    assert cfg.list_args == "ls"
    assert cfg.run_args == "run {name}"
    assert cfg.filter_args == "filter {filter}"
    assert cfg.success_value == "OK"


def test_config_invalid_list_pattern():
    with pytest.raises(ValueError, match="list_pattern"):
        CustomParserConfig(
            list_pattern=r"(?P<name",
            result_pattern=_RESULT_PATTERN,
        )


def test_config_list_pattern_missing_name():
    with pytest.raises(ValueError, match="list_pattern"):
        CustomParserConfig(
            list_pattern=r"TEST:\s+(\w+)",
            result_pattern=_RESULT_PATTERN,
        )


def test_config_invalid_result_pattern():
    with pytest.raises(ValueError, match="result_pattern"):
        CustomParserConfig(
            list_pattern=_LIST_PATTERN,
            result_pattern=r"(?P<status",
        )


def test_config_result_pattern_missing_name():
    with pytest.raises(ValueError, match="result_pattern"):
        CustomParserConfig(
            list_pattern=_LIST_PATTERN,
            result_pattern=r"(?P<status>PASS|FAIL)\s+\w+",
        )


def test_config_result_pattern_missing_status():
    with pytest.raises(ValueError, match="result_pattern"):
        CustomParserConfig(
            list_pattern=_LIST_PATTERN,
            result_pattern=r"PASS\s+(?P<name>\w+)",
        )


def test_discover_from_elf_returns_empty():
    parser = CustomParser(_make_core(), "bin", _make_config())
    assert parser._discover_from_elf(None) == []


_LIST_OUTPUT = (
    "Starting tests...\n"
    "TEST: test_foo\n"
    "noise line\n"
    "TEST: test_bar\n"
    "Done.\n"
)


def test_discover_from_device_success():
    core = _make_core(output=_LIST_OUTPUT)
    parser = CustomParser(core, "bin", _make_config())
    items = parser._discover_from_device()
    assert len(items) == 2
    assert items[0].name == "test_foo"
    assert items[0].suite is None
    assert items[1].name == "test_bar"


def test_discover_from_device_with_suite():
    output = "[suite_a] test_alpha\n[suite_b] test_beta\n"
    core = _make_core(output=output)
    parser = CustomParser(
        core,
        "bin",
        _make_config(
            list_pattern=_LIST_SUITE_PATTERN,
        ),
    )
    items = parser._discover_from_device()
    assert len(items) == 2
    assert items[0].name == "test_alpha"
    assert items[0].suite == "suite_a"
    assert items[1].name == "test_beta"
    assert items[1].suite == "suite_b"


def test_discover_from_device_no_matches():
    core = _make_core(output="no matches here\n")
    parser = CustomParser(core, "bin", _make_config())
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_empty_output():
    core = _make_core(output="")
    parser = CustomParser(core, "bin", _make_config())
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_failure_status():
    core = _make_core(status=CmdStatus.NOTFOUND)
    parser = CustomParser(core, "bin", _make_config())
    items = parser._discover_from_device()
    assert items == []


_RUN_OUTPUT = "PASS test_foo\nFAIL test_bar\n"


def test_parse_output_pass():
    parser = CustomParser(_make_core(), "bin", _make_config())
    results = parser._parse_output(_RUN_OUTPUT)
    assert "test_foo" in results
    assert results["test_foo"].passed is True


def test_parse_output_fail():
    parser = CustomParser(_make_core(), "bin", _make_config())
    results = parser._parse_output(_RUN_OUTPUT)
    assert "test_bar" in results
    assert results["test_bar"].passed is False


def test_parse_output_custom_success_value():
    output = "OK test_foo\nERROR test_bar\n"
    cfg = _make_config(
        result_pattern=r"(?P<status>OK|ERROR)\s+(?P<name>\w+)",
        success_value="OK",
    )
    parser = CustomParser(_make_core(), "bin", cfg)
    results = parser._parse_output(output)
    assert results["test_foo"].passed is True
    assert results["test_bar"].passed is False


def test_parse_output_no_matches():
    parser = CustomParser(_make_core(), "bin", _make_config())
    results = parser._parse_output("nothing here")
    assert results == {}


def test_parse_output_empty():
    parser = CustomParser(_make_core(), "bin", _make_config())
    results = parser._parse_output("")
    assert results == {}


def test_parse_output_stores_raw_output():
    raw = "PASS test_foo\n"
    parser = CustomParser(_make_core(), "bin", _make_config())
    results = parser._parse_output(raw)
    assert results["test_foo"].output == raw


def test_run_single_explicit_name_pass():
    core = _make_core(output="PASS test_foo\n")
    parser = CustomParser(core, "bin", _make_config())
    result = parser.run_single("test_foo")
    assert result.passed is True
    assert result.name == "test_foo"


def test_run_single_uses_test_name_attr():
    core = _make_core(output="PASS test_bar\n")
    parser = CustomParser(core, "bin", _make_config(), test_name="test_bar")
    result = parser.run_single()
    assert result.passed is True
    assert result.name == "test_bar"


def test_run_single_no_name_returns_failure():
    parser = CustomParser(_make_core(), "bin", _make_config())
    result = parser.run_single()
    assert result.passed is False
    assert result.output == "no test name"


def test_run_single_name_not_in_parsed():
    core = _make_core(output="PASS other_test\n")
    parser = CustomParser(core, "bin", _make_config())
    result = parser.run_single("test_missing")
    assert result.passed is False
    assert result.name == "test_missing"


def test_run_single_custom_run_args():
    captured = {}

    def fake_send(binary, args=""):
        captured["args"] = args
        return CmdReturn(status=CmdStatus.SUCCESS, output="PASS test_foo\n")

    core = SimpleNamespace(
        conf=SimpleNamespace(elf_path=""),
        sendCommandReadUntilPattern=fake_send,
    )
    cfg = _make_config(run_args="--run {name}")
    parser = CustomParser(core, "bin", cfg)
    parser.run_single("test_foo")
    assert captured["args"] == "--run test_foo"


def test_run_all():
    output = "PASS test_a\nFAIL test_b\n"
    core = _make_core(output=output)
    parser = CustomParser(core, "bin", _make_config())
    results = parser.run_all()
    assert results["test_a"].passed is True
    assert results["test_b"].passed is False
    assert parser.get_result("test_a") is not None
    assert parser.get_result("test_b") is not None


def test_run_filtered():
    output = "PASS test_foo\n"
    captured = {}

    def fake_send(binary, args=""):
        captured["args"] = args
        return CmdReturn(status=CmdStatus.SUCCESS, output=output)

    core = SimpleNamespace(
        conf=SimpleNamespace(elf_path=""),
        sendCommandReadUntilPattern=fake_send,
    )
    cfg = _make_config(filter_args="--filter {filter}")
    parser = CustomParser(core, "bin", cfg)
    results = parser.run_filtered("test_*")
    assert "test_foo" in results
    assert results["test_foo"].passed is True
    assert captured["args"] == "--filter test_*"
    assert parser.get_result("test_foo") is not None
