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
from ntfc.parsers.custom import CustomParser, CustomParserConfig
from ntfc.pytest.parsers import (
    PARSER_FIXTURES,
    ParserPlugin,
    _build_custom_config,
    _discover_cache,
    _discover_custom_tests,
    _discover_tests,
    _make_custom_parser,
    _make_parser,
    _read_parser_marker,
)

_LIST_PATTERN = r"TEST:\s+(?P<name>\w+)"
_RESULT_PATTERN = r"(?P<status>PASS|FAIL)\s+(?P<name>\w+)"


@pytest.fixture(autouse=True)
def _clear_caches():
    _discover_cache.clear()
    yield
    _discover_cache.clear()


def _make_custom_config(**kwargs) -> CustomParserConfig:
    defaults = dict(
        list_pattern=_LIST_PATTERN,
        result_pattern=_RESULT_PATTERN,
    )
    defaults.update(kwargs)
    return CustomParserConfig(**defaults)


def _make_node(
    binary: Optional[str] = None,
    flt: Optional[str] = None,
    custom_cfg: Optional[CustomParserConfig] = None,
):
    """Build a minimal pytest item-like object with optional marker.

    Custom config is embedded directly in the ``parser_binary`` marker
    kwargs, mirroring the real user-facing API.
    """
    if binary is None:
        binary_marker = None
    else:
        mk_kwargs: dict = {}
        if flt is not None:
            mk_kwargs["filter"] = flt
        if custom_cfg is not None:
            mk_kwargs.update(
                list_pattern=custom_cfg.list_pattern,
                result_pattern=custom_cfg.result_pattern,
                list_args=custom_cfg.list_args,
                run_args=custom_cfg.run_args,
                filter_args=custom_cfg.filter_args,
                success_value=custom_cfg.success_value,
            )
        binary_marker = SimpleNamespace(
            args=(binary,),
            kwargs=mk_kwargs,
        )

    node = MagicMock()
    node.get_closest_marker.return_value = binary_marker
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


def _make_custom_core(device_items=None):
    """Build a mock ProductCore that returns custom list output."""
    from ntfc.device.common import CmdReturn, CmdStatus

    items = device_items or []
    lines = "\n".join(f"TEST: {i.name}" for i in items)
    cmd_return = CmdReturn(status=CmdStatus.SUCCESS, output=lines)
    conf = SimpleNamespace(elf_path="")
    return SimpleNamespace(
        conf=conf,
        sendCommandReadUntilPattern=lambda *_a, **_kw: cmd_return,
    )


def _make_metafunc(fixture_names, node=None):
    """Build a mock Metafunc object."""
    mf = MagicMock()
    mf.fixturenames = fixture_names
    mf.definition = node or _make_node(binary=None)
    return mf


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


def test_discover_tests_cache_hit(monkeypatch):
    """Second call with the same key returns the cached list."""
    core = _make_core(device_items=[_Item(name="test_a")])
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)
    result1 = _discover_tests(CmockaParser, "cache_hit_bin", None)
    result2 = _discover_tests(CmockaParser, "cache_hit_bin", None)
    assert result1 is result2
    assert len(result2) == 1


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
    assert call_kwargs[0][0] == "cmocka_parser"
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


def test_build_custom_config_no_marker():
    node = _make_node(binary=None)
    assert _build_custom_config(node) is None


def test_build_custom_config_no_cfg_kwargs():
    """parser_binary present but no custom config kwargs → None."""
    node = _make_node(binary="bin")
    assert _build_custom_config(node) is None


def test_build_custom_config_returns_config():
    cfg_in = _make_custom_config()
    node = _make_node(binary="bin", custom_cfg=cfg_in)
    cfg_out = _build_custom_config(node)
    assert isinstance(cfg_out, CustomParserConfig)
    assert cfg_out.list_pattern == _LIST_PATTERN
    assert cfg_out.result_pattern == _RESULT_PATTERN


def test_discover_custom_tests_no_product(monkeypatch):
    monkeypatch.delattr(pytest, "product", raising=False)
    cfg = _make_custom_config()
    result = _discover_custom_tests("bin", None, cfg)
    assert result == []


def test_discover_custom_tests_returns_items(monkeypatch):
    items = [_Item(name="test_a"), _Item(name="test_b")]
    core = _make_custom_core(device_items=items)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    cfg = _make_custom_config()
    result = _discover_custom_tests("bin", None, cfg)
    assert len(result) == 2
    assert result[0].name == "test_a"


def test_discover_custom_tests_with_filter(monkeypatch):
    items = [_Item(name="test_a"), _Item(name="other")]
    core = _make_custom_core(device_items=items)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    cfg = _make_custom_config()
    result = _discover_custom_tests("bin", "test_*", cfg)
    assert len(result) == 1
    assert result[0].name == "test_a"


def test_make_custom_parser_success(monkeypatch):
    core = _make_custom_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    cfg = _make_custom_config()
    request = SimpleNamespace(
        param="test_foo",
        node=_make_node(binary="bin", custom_cfg=cfg),
    )
    parser = _make_custom_parser(request)
    assert isinstance(parser, CustomParser)
    assert parser.test_name == "test_foo"


def test_make_custom_parser_no_binary_skips():
    cfg = _make_custom_config()
    request = SimpleNamespace(
        param=None,
        node=_make_node(binary=None, custom_cfg=cfg),
    )
    with pytest.raises(pytest.skip.Exception):
        _make_custom_parser(request)


def test_make_custom_parser_no_cfg_kwargs_skips(monkeypatch):
    """parser_binary present but no custom config kwargs → skip."""
    core = _make_custom_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    request = SimpleNamespace(
        param=None,
        node=_make_node(binary="bin"),
    )
    with pytest.raises(pytest.skip.Exception):
        _make_custom_parser(request)


def test_make_custom_parser_no_param(monkeypatch):
    core = _make_custom_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    cfg = _make_custom_config()
    request = SimpleNamespace(node=_make_node(binary="bin", custom_cfg=cfg))
    parser = _make_custom_parser(request)
    assert parser.test_name is None


def test_generate_tests_custom_no_marker():
    plugin = ParserPlugin()
    mf = _make_metafunc(["custom_parser"], node=_make_node(binary=None))
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_custom_no_cfg_kwargs():
    """parser_binary present but no custom config kwargs → no parametrize."""
    plugin = ParserPlugin()
    node = _make_node(binary="my_bin")
    mf = _make_metafunc(["custom_parser"], node=node)
    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_custom_empty_discovery(monkeypatch):
    plugin = ParserPlugin()
    cfg = _make_custom_config()
    node = _make_node(binary="my_bin", custom_cfg=cfg)
    mf = _make_metafunc(["custom_parser"], node=node)

    core = _make_custom_core(device_items=[])
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_not_called()


def test_generate_tests_custom_parametrizes(monkeypatch):
    plugin = ParserPlugin()
    cfg = _make_custom_config()
    node = _make_node(binary="my_bin", custom_cfg=cfg)
    mf = _make_metafunc(["custom_parser"], node=node)

    items = [_Item(name="test_a"), _Item(name="test_b")]
    core = _make_custom_core(device_items=items)
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    plugin.pytest_generate_tests(mf)
    mf.parametrize.assert_called_once()
    call_kwargs = mf.parametrize.call_args
    assert call_kwargs[0][0] == "custom_parser"
    assert call_kwargs[0][1] == ["test_a", "test_b"]
    assert call_kwargs[1]["indirect"] is True


def test_custom_parser_fixture(monkeypatch):
    plugin = ParserPlugin()
    core = _make_custom_core()
    product_mock = SimpleNamespace(core=lambda _: core)
    monkeypatch.setattr(pytest, "product", product_mock, raising=False)

    cfg = _make_custom_config()
    request = SimpleNamespace(
        param="test_foo",
        node=_make_node(binary="bin", custom_cfg=cfg),
    )
    parser = plugin.custom_parser.__wrapped__(plugin, request)
    assert isinstance(parser, CustomParser)
    assert parser.test_name == "test_foo"
