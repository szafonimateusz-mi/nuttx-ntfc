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

"""Tests for ntfc.pytest.parsers."""

from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock

import pytest

from ntfc.parsers.base import TestItem as _Item
from ntfc.parsers.cmocka import CmockaParser
from ntfc.pytest.parsers import (
    PARSER_FIXTURES,
    ParserPlugin,
    _discover_tests,
    _make_parser,
    _read_parser_marker,
)


def _make_node(binary: Optional[str] = None, flt: Optional[str] = None):
    """Build a minimal pytest item-like object with optional marker."""
    if binary is None:
        marker = None
    else:
        kwargs = {}
        if flt is not None:
            kwargs["filter"] = flt
        marker = SimpleNamespace(
            args=(binary,) if binary else (),
            kwargs=kwargs,
        )

    node = MagicMock()
    node.get_closest_marker.return_value = marker
    return node


def _make_core(device_items=None):
    """Build a mock ProductCore with configurable discovery output."""
    from ntfc.device.common import CmdReturn, CmdStatus

    items = device_items or []
    # Build cmocka-compatible list output: suite header + 4-space-indented
    # test names so that CmockaParser._discover_from_device parses them.
    lines_parts = ["suite"]
    for i in items:
        lines_parts.append(f"    {i.name}")
    lines = "\n".join(lines_parts)
    cmd_return = CmdReturn(status=CmdStatus.SUCCESS, output=lines)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


def test_parser_fixtures_contains_expected_keys():
    assert "cmocka_parser" in PARSER_FIXTURES
    assert PARSER_FIXTURES["cmocka_parser"] is CmockaParser


def test_read_parser_marker_no_marker():
    node = _make_node(binary=None)
    binary, flt = _read_parser_marker(node)
    assert binary is None
    assert flt is None


def test_read_parser_marker_binary_only():
    node = _make_node(binary="my_binary")
    binary, flt = _read_parser_marker(node)
    assert binary == "my_binary"
    assert flt is None


def test_read_parser_marker_with_filter():
    node = _make_node(binary="my_binary", flt="test_*")
    binary, flt = _read_parser_marker(node)
    assert binary == "my_binary"
    assert flt == "test_*"


def test_read_parser_marker_empty_args():
    """Marker present but with no positional args → binary is None."""
    marker = SimpleNamespace(args=(), kwargs={})
    node = MagicMock()
    node.get_closest_marker.return_value = marker
    binary, flt = _read_parser_marker(node)
    assert binary is None
    assert flt is None


def test_discover_tests_no_product(monkeypatch):
    monkeypatch.delattr(pytest, "product", raising=False)
    result = _discover_tests(CmockaParser, "bin", None)
    assert result == []


def test_discover_tests_returns_items(monkeypatch):
    items = [_Item(name="test_a"), _Item(name="test_b")]
    core = _make_core(device_items=items)

    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    result = _discover_tests(CmockaParser, "bin", None)
    assert len(result) == 2
    assert result[0].name == "test_a"


def test_discover_tests_with_filter(monkeypatch):
    items = [_Item(name="test_a"), _Item(name="other")]
    core = _make_core(device_items=items)

    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    result = _discover_tests(CmockaParser, "bin", "test_*")
    assert len(result) == 1
    assert result[0].name == "test_a"


def test_make_parser_returns_parser(monkeypatch):
    core = _make_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    request = SimpleNamespace(
        param="test_foo",
        node=_make_node(binary="my_binary"),
    )

    parser = _make_parser(CmockaParser, request)
    assert isinstance(parser, CmockaParser)
    assert parser.test_name == "test_foo"


def test_make_parser_no_binary_skips(monkeypatch):
    """_make_parser calls pytest.skip when binary is None."""
    request = SimpleNamespace(
        param=None,
        node=_make_node(binary=None),
    )

    with pytest.raises(pytest.skip.Exception):
        _make_parser(CmockaParser, request)


def test_make_parser_no_param(monkeypatch):
    """_make_parser works when request has no param (non-parametrized)."""
    core = _make_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    # request has no 'param' attribute
    request = SimpleNamespace(node=_make_node(binary="bin"))

    parser = _make_parser(CmockaParser, request)
    assert parser.test_name is None


def test_pytest_configure_registers_marker():
    plugin = ParserPlugin()
    config = MagicMock()
    plugin.pytest_configure(config)
    config.addinivalue_line.assert_called_once()
    call_args = config.addinivalue_line.call_args[0]
    assert call_args[0] == "markers"
    assert "parser_binary" in call_args[1]


def _make_metafunc(fixture_names, node=None):
    """Build a mock Metafunc object."""
    mf = MagicMock()
    mf.fixturenames = fixture_names
    mf.definition = node or _make_node(binary=None)
    return mf


def test_generate_tests_no_matching_fixture():
    plugin = ParserPlugin()
    mf = _make_metafunc(["some_other_fixture"])
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_no_marker():
    plugin = ParserPlugin()
    mf = _make_metafunc(["cmocka_parser"], node=_make_node(binary=None))
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_empty_discovery(monkeypatch):
    plugin = ParserPlugin()
    node = _make_node(binary="my_bin")
    mf = _make_metafunc(["cmocka_parser"], node=node)

    # device returns no tests
    core = _make_core(device_items=[])
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_parametrizes(monkeypatch):
    plugin = ParserPlugin()
    node = _make_node(binary="my_bin")
    mf = _make_metafunc(["cmocka_parser"], node=node)

    items = [_Item(name="test_a"), _Item(name="test_b")]
    core = _make_core(device_items=items)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_called_once()
    call_kwargs = mf.parametrize.call_args
    # First positional arg: fixture name
    assert call_kwargs[0][0] == "cmocka_parser"
    # Second positional arg: list of test names
    assert call_kwargs[0][1] == ["test_a", "test_b"]
    assert call_kwargs[1]["indirect"] is True


def test_cmocka_parser_fixture(monkeypatch):
    plugin = ParserPlugin()
    core = _make_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    request = SimpleNamespace(
        param="test_foo",
        node=_make_node(binary="bin"),
    )
    parser = plugin.cmocka_parser.__wrapped__(plugin, request)
    assert isinstance(parser, CmockaParser)
    assert parser.test_name == "test_foo"
