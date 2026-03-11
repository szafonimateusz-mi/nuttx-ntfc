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

"""Tests for ntfc.pytest.gtest_plugin."""

from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock

import pytest

from ntfc.device.common import CmdReturn, CmdStatus
from ntfc.parsers.base import TestItem as _Item
from ntfc.parsers.gtest import GtestParser
from ntfc.pytest.gtest_plugin import (
    GtestParserPlugin,
    _discover_gtest_tests,
    _items_cache,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    GtestParser.clear_session()
    _items_cache.clear()
    yield
    GtestParser.clear_session()
    _items_cache.clear()


_GTEST_OUTPUT = (
    "[ RUN      ] Suite1.test_foo\n"
    "[       OK ] Suite1.test_foo (0 ms)\n"
    "[ RUN      ] Suite1.test_bar\n"
    "[  FAILED  ] Suite1.test_bar (1 ms)\n"
)


def _make_core(output: str = ""):
    """Build a mock ProductCore returning gtest run output."""
    cmd_return = CmdReturn(status=CmdStatus.SUCCESS, output=output)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


def _make_node(
    binary: Optional[str] = None,
    flt: Optional[str] = None,
):
    if binary is None:
        binary_marker = None
    else:
        mk_kwargs = {}
        if flt is not None:
            mk_kwargs["filter"] = flt
        binary_marker = SimpleNamespace(args=(binary,), kwargs=mk_kwargs)
    node = MagicMock()
    node.get_closest_marker.return_value = binary_marker
    return node


def _make_metafunc(fixture_names, node=None):
    mf = MagicMock()
    mf.fixturenames = fixture_names
    mf.definition = node or _make_node(binary=None)
    return mf


def test_pytest_configure_preserves_caches(monkeypatch):
    """pytest_configure does not modify session cache or items cache."""
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    _items_cache[("bin", None)] = [_Item(name="Suite1.test_foo")]
    GtestParser._session_results["bin"] = {}

    plugin = GtestParserPlugin()
    plugin.pytest_configure(MagicMock())

    assert _items_cache == {("bin", None): [_Item(name="Suite1.test_foo")]}
    assert GtestParser._session_results == {"bin": {}}


def test_generate_tests_no_gtest_fixture():
    """pytest_generate_tests skips when gtest_parser not in fixturenames."""
    plugin = GtestParserPlugin()
    mf = _make_metafunc(["cmocka_parser"])
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_no_marker():
    """pytest_generate_tests skips when no parser_binary marker."""
    plugin = GtestParserPlugin()
    mf = _make_metafunc(["gtest_parser"], node=_make_node(binary=None))
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_empty_discovery(monkeypatch):
    """pytest_generate_tests skips parametrize when no tests found."""
    plugin = GtestParserPlugin()
    core = _make_core(output="")
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    mf = _make_metafunc(["gtest_parser"], node=_make_node(binary="empty_bin"))
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_parametrizes(monkeypatch):
    """pytest_generate_tests parametrizes gtest_parser with test names."""
    plugin = GtestParserPlugin()
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    mf = _make_metafunc(["gtest_parser"], node=_make_node(binary="gtest_bin"))
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_called_once()
    args = mf.parametrize.call_args[0]
    assert args[0] == "gtest_parser"
    assert "Suite1.test_foo" in args[1]
    assert "Suite1.test_bar" in args[1]


def test_generate_tests_with_filter(monkeypatch):
    """pytest_generate_tests applies filter from marker kwargs."""
    plugin = GtestParserPlugin()
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    mf = _make_metafunc(
        ["gtest_parser"],
        node=_make_node(binary="gtest_bin", flt="Suite1.test_foo"),
    )
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_called_once()
    args = mf.parametrize.call_args[0]
    assert args[1] == ["Suite1.test_foo"]


def test_generate_tests_uses_items_cache(monkeypatch):
    """Second pytest_generate_tests call uses cached items."""
    calls = []

    def _send(*_a, **_kw):
        calls.append(1)
        return CmdReturn(status=CmdStatus.SUCCESS, output=_GTEST_OUTPUT)

    conf = SimpleNamespace(elf_path="")
    core = SimpleNamespace(conf=conf, sendCommandReadUntilPattern=_send)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    plugin = GtestParserPlugin()
    mf = _make_metafunc(["gtest_parser"], node=_make_node(binary="gtest_bin"))
    plugin.pytest_generate_tests(mf)
    plugin.pytest_generate_tests(mf)

    assert len(calls) == 1


def test_gtest_parser_fixture(monkeypatch):
    """gtest_parser fixture returns a GtestParser with cached results."""
    plugin = GtestParserPlugin()
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    # Populate session cache as discovery would
    GtestParser._session_results["gtest_bin"] = {
        "Suite1.test_foo": GtestParser(core, "gtest_bin")._parse_output(
            _GTEST_OUTPUT
        )["Suite1.test_foo"]
    }

    request = SimpleNamespace(
        param="Suite1.test_foo",
        node=_make_node(binary="gtest_bin"),
    )
    parser = plugin.gtest_parser.__wrapped__(plugin, request)
    assert isinstance(parser, GtestParser)
    assert parser.test_name == "Suite1.test_foo"


def test_discover_gtest_tests_no_product(monkeypatch):
    """Returns empty list when pytest.product is not set."""
    monkeypatch.delattr(pytest, "product", raising=False)
    result = _discover_gtest_tests("bin", None)
    assert result == []


def test_discover_gtest_tests_returns_items(monkeypatch):
    """Returns discovered TestItems from the gtest binary."""
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    result = _discover_gtest_tests("gtest_bin", None)
    assert len(result) == 2
    assert result[0].name == "Suite1.test_foo"


def test_discover_gtest_tests_with_filter(monkeypatch):
    """fnmatch filter limits returned items."""
    core = _make_core(output=_GTEST_OUTPUT)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    result = _discover_gtest_tests("gtest_bin", "Suite1.test_foo")
    assert len(result) == 1
    assert result[0].name == "Suite1.test_foo"
