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

"""Tests for ntfc.parsers.cmocka."""

from types import SimpleNamespace

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.parsers.cmocka import CmockaParser


def _make_core(output: str = "", status: CmdStatus = CmdStatus.SUCCESS):
    """Build a minimal mock ProductCore."""
    cmd_return = CmdReturn(status=status, output=output)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


def test_discover_from_elf_returns_empty():
    core = _make_core()
    parser = CmockaParser(core, "cmocka_bin")
    result = parser._discover_from_elf(None)
    assert result == []


_CMOCKA_LIST_OUTPUT = (
    "Cmocka Test Start.\n"
    "tests\n"
    "    test_foo\n"
    "    test_bar\n"
    "nuttx_suite\n"
    "    test_baz\n"
    "Cmocka Test Completed.\n"
)


def test_discover_from_device_success():
    core = _make_core(output=_CMOCKA_LIST_OUTPUT)
    parser = CmockaParser(core, "cmocka_bin")
    items = parser._discover_from_device()
    assert len(items) == 3
    assert items[0].name == "test_foo"
    assert items[0].suite == "tests"
    assert items[1].name == "test_bar"
    assert items[2].name == "test_baz"
    assert items[2].suite == "nuttx_suite"


def test_discover_from_device_skips_noise():
    """Noise lines (driver messages, usage text) between suites are ignored."""
    output = (
        "Cmocka Test Start.\n"
        "tests\n"
        "    test_foo\n"
        "Missing <source>\n"
        "Usage: cmocka_driver -m <source>\n"
        "  -m <source> mount location.\n"
        "devname = /dev/fb0\n"
        "testcase = 0\n"
        "tests\n"
        "    test_bar\n"
        "Cmocka Test Completed.\n"
    )
    core = _make_core(output=output)
    parser = CmockaParser(core, "cmocka_bin")
    items = parser._discover_from_device()
    assert len(items) == 2
    assert items[0].name == "test_foo"
    assert items[1].name == "test_bar"


def test_discover_from_device_orphan_test_ignored():
    """Indented test lines with no preceding suite header are ignored."""
    output = "    orphan_test\ntests\n    test_foo\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "cmocka_bin")
    items = parser._discover_from_device()
    assert len(items) == 1
    assert items[0].name == "test_foo"


def test_discover_from_device_failure_returns_empty():
    core = _make_core(status=CmdStatus.NOTFOUND)
    parser = CmockaParser(core, "cmocka_bin")
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_empty_output():
    core = _make_core(output="")
    parser = CmockaParser(core, "cmocka_bin")
    items = parser._discover_from_device()
    assert items == []


_CMOCKA_OUTPUT = (
    "[====] Starting 2 test(s).\n"
    "[ RUN  ] test_foo\n"
    "[  OK  ] test_foo: Test passed.\n"
    "[ RUN  ] test_bar\n"
    "[ FAIL ] test_bar: assertion failed at line 42.\n"
    "[====] 2 test(s) run. 1 passed. 1 failed.\n"
)


def test_parse_output_ok():
    parser = CmockaParser(_make_core(), "bin")
    results = parser._parse_output(_CMOCKA_OUTPUT)
    assert "test_foo" in results
    assert results["test_foo"].passed is True


def test_parse_output_fail():
    parser = CmockaParser(_make_core(), "bin")
    results = parser._parse_output(_CMOCKA_OUTPUT)
    assert "test_bar" in results
    assert results["test_bar"].passed is False


def test_parse_output_no_matches():
    parser = CmockaParser(_make_core(), "bin")
    results = parser._parse_output("nothing here")
    assert results == {}


def test_parse_output_empty():
    parser = CmockaParser(_make_core(), "bin")
    results = parser._parse_output("")
    assert results == {}


def test_run_single_with_explicit_name():
    output = "[  OK  ] test_foo: Test passed.\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "bin")
    result = parser.run_single("test_foo")
    assert result.passed is True
    assert result.name == "test_foo"


def test_run_single_uses_test_name_attr():
    output = "[  OK  ] test_bar: Test passed.\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "bin", test_name="test_bar")
    result = parser.run_single()
    assert result.passed is True
    assert result.name == "test_bar"


def test_run_single_no_name_returns_failure():
    core = _make_core()
    parser = CmockaParser(core, "bin")
    result = parser.run_single()
    assert result.passed is False
    assert result.output == "no test name"


def test_run_single_name_not_in_parsed():
    """run_single falls back when output doesn't contain the test name."""
    output = "[  OK  ] other_test: Test passed.\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "bin")
    result = parser.run_single("test_missing")
    assert result.passed is False
    assert result.name == "test_missing"


def test_run_all():
    output = "[  OK  ] test_a: Test passed.\n" "[ FAIL ] test_b: failed.\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "bin")
    results = parser.run_all()
    assert "test_a" in results
    assert results["test_a"].passed is True
    assert "test_b" in results
    assert results["test_b"].passed is False
    # cached
    assert parser.get_result("test_a") is not None


def test_run_filtered():
    output = "[  OK  ] test_foo: Test passed.\n"
    core = _make_core(output=output)
    parser = CmockaParser(core, "bin")
    results = parser.run_filtered("test_*")
    assert "test_foo" in results
    assert results["test_foo"].passed is True
    # cached
    assert parser.get_result("test_foo") is not None
