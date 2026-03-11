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

import pytest

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.parsers.gtest import GtestParser


@pytest.fixture(autouse=True)
def _clear_session():
    GtestParser.clear_session()
    yield
    GtestParser.clear_session()


def _make_core(output: str = "", status: CmdStatus = CmdStatus.SUCCESS):
    """Build a minimal mock ProductCore."""
    cmd_return = CmdReturn(status=status, output=output)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


_GTEST_OUTPUT = (
    "[ RUN      ] Suite1.test_foo\n"
    "[       OK ] Suite1.test_foo (0 ms)\n"
    "[ RUN      ] Suite1.test_bar\n"
    "[  FAILED  ] Suite1.test_bar (1 ms)\n"
)


def test_discover_from_elf_returns_empty():
    core = _make_core()
    parser = GtestParser(core, "gtest_bin")
    result = parser._discover_from_elf(None)
    assert result == []


def test_discover_from_device_calls_run_all():
    """_discover_from_device runs all tests and derives names from results."""
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert len(items) == 2
    assert items[0].name == "Suite1.test_foo"
    assert items[0].suite == "Suite1"
    assert items[1].name == "Suite1.test_bar"
    assert items[1].suite == "Suite1"


def test_discover_from_device_uses_session_cache():
    """Second call returns cached items without re-running the binary."""
    calls = []

    def _send(*_a, **_kw):
        calls.append(1)
        return CmdReturn(status=CmdStatus.SUCCESS, output=_GTEST_OUTPUT)

    conf = SimpleNamespace(elf_path="")
    core = SimpleNamespace(conf=conf, sendCommandReadUntilPattern=_send)
    parser = GtestParser(core, "gtest_bin")

    parser._discover_from_device()
    parser._discover_from_device()

    assert len(calls) == 1


def test_discover_from_device_no_results():
    """Empty run output yields no items."""
    core = _make_core(output="")
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert items == []


def test_discover_from_device_no_suite_separator():
    """Names without a '.' have suite=None."""
    output = "[       OK ] bare_test (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "gtest_bin")
    items = parser._discover_from_device()
    assert len(items) == 1
    assert items[0].name == "bare_test"
    assert items[0].suite is None


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


def test_run_single_uses_session_cache():
    """run_single returns the result cached by run_all / discovery."""
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "bin", test_name="Suite1.test_foo")
    parser.run_all()
    result = parser.run_single()
    assert result.passed is True
    assert result.name == "Suite1.test_foo"


def test_run_single_with_explicit_name_from_cache():
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "bin")
    parser.run_all()
    result = parser.run_single("Suite1.test_foo")
    assert result.passed is True


def test_run_single_fallback_to_device():
    """run_single calls device when name not in session cache."""
    output = "[       OK ] Suite.test_foo (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    result = parser.run_single("Suite.test_foo")
    assert result.passed is True
    assert result.name == "Suite.test_foo"


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


def test_run_all_populates_session_cache():
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "bin")
    results = parser.run_all()
    assert results["Suite1.test_foo"].passed is True
    assert results["Suite1.test_bar"].passed is False
    assert GtestParser._session_results["bin"] is results


def test_run_all_accessible_via_get_result():
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "bin")
    parser.run_all()
    assert parser.get_result("Suite1.test_foo") is not None


def test_run_filtered():
    output = "[       OK ] Suite.test_foo (0 ms)\n"
    core = _make_core(output=output)
    parser = GtestParser(core, "bin")
    results = parser.run_filtered("Suite.*")
    assert "Suite.test_foo" in results
    assert results["Suite.test_foo"].passed is True
    assert parser.get_result("Suite.test_foo") is not None


def test_clear_session():
    core = _make_core(output=_GTEST_OUTPUT)
    parser = GtestParser(core, "bin")
    parser.run_all()
    assert "bin" in GtestParser._session_results
    GtestParser.clear_session()
    assert GtestParser._session_results == {}
