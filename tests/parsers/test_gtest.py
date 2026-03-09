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

"""Tests for ntfc.parsers.gtest."""

from types import SimpleNamespace

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.parsers.gtest import GtestParser


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
    parser = GtestParser(core, "gtest_bin")
    result = parser._discover_from_elf(None)
    assert result == []


_GTEST_LIST_OUTPUT = (
    "Suite1.\n" "  test_foo\n" "  test_bar\n" "Suite2.\n" "  test_baz\n"
)


def test_discover_from_device_success():
    core = _make_core(output=_GTEST_LIST_OUTPUT)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert len(items) == 3
    assert items[0].name == "Suite1.test_foo"
    assert items[0].suite == "Suite1"
    assert items[1].name == "Suite1.test_bar"
    assert items[2].name == "Suite2.test_baz"
    assert items[2].suite == "Suite2"


def test_discover_from_device_failure_returns_empty():
    core = _make_core(status=CmdStatus.NOTFOUND)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_empty_output():
    core = _make_core(output="")
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_skips_blank_lines():
    output = "Suite1.\n\n  test_foo\n\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert len(items) == 1
    assert items[0].name == "Suite1.test_foo"


def test_discover_from_device_line_before_suite():
    """Lines indented before any suite header are ignored."""
    output = "  orphan_line\nSuite1.\n  test_foo\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    # orphan_line has no suite → skipped
    assert len(items) == 1
    assert items[0].name == "Suite1.test_foo"


_GTEST_OUTPUT = (
    "[ RUN      ] Suite1.test_foo\n"
    "[       OK ] Suite1.test_foo (0 ms)\n"
    "[ RUN      ] Suite1.test_bar\n"
    "[  FAILED  ] Suite1.test_bar (1 ms)\n"
)


def test_parse_output_ok():
    parser = GtestParser(_make_core(), "bin")
    results = parser._parse_output(_GTEST_OUTPUT)
    assert "Suite1.test_foo" in results
    assert results["Suite1.test_foo"].passed is True


def test_parse_output_failed():
    parser = GtestParser(_make_core(), "bin")
    results = parser._parse_output(_GTEST_OUTPUT)
    assert "Suite1.test_bar" in results
    assert results["Suite1.test_bar"].passed is False


def test_parse_output_no_matches():
    parser = GtestParser(_make_core(), "bin")
    results = parser._parse_output("no results here")
    assert results == {}


def test_parse_output_empty():
    parser = GtestParser(_make_core(), "bin")
    results = parser._parse_output("")
    assert results == {}


def test_run_single_with_explicit_name():
    output = "[       OK ] Suite.test_foo (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    result = parser.run_single("Suite.test_foo")
    assert result.passed is True
    assert result.name == "Suite.test_foo"


def test_run_single_uses_test_name_attr():
    output = "[       OK ] Suite.test_bar (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin", test_name="Suite.test_bar")
    result = parser.run_single()
    assert result.passed is True
    assert result.name == "Suite.test_bar"


def test_run_single_no_name_returns_failure():
    core = _make_core()
    parser = GtestParser(core, "bin")
    result = parser.run_single()
    assert result.passed is False
    assert result.output == "no test name"


def test_run_single_name_not_in_parsed():
    output = "[       OK ] Suite.other (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    result = parser.run_single("Suite.missing")
    assert result.passed is False
    assert result.name == "Suite.missing"


def test_run_all():
    output = (
        "[       OK ] Suite.test_a (0 ms)\n"
        "[  FAILED  ] Suite.test_b (1 ms)\n"
    )
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    results = parser.run_all()
    assert results["Suite.test_a"].passed is True
    assert results["Suite.test_b"].passed is False
    assert parser.get_result("Suite.test_a") is not None


def test_run_filtered():
    output = "[       OK ] Suite.test_foo (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    results = parser.run_filtered("Suite.*")
    assert "Suite.test_foo" in results
    assert results["Suite.test_foo"].passed is True
    assert parser.get_result("Suite.test_foo") is not None
