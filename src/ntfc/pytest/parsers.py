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

"""Pytest plugin that parametrizes test framework parser fixtures."""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type

import pytest

from ntfc.parsers.cmocka import CmockaParser
from ntfc.parsers.custom import CustomParser, CustomParserConfig

if TYPE_CHECKING:
    from ntfc.parsers.base import AbstractTestParser, TestItem

# Map fixture name → parser class
PARSER_FIXTURES: Dict[str, Type["AbstractTestParser"]] = {
    "cmocka_parser": CmockaParser,
}

# kwargs in parser_binary that belong to CustomParserConfig (not filtering)
_CUSTOM_CFG_KEYS = frozenset(
    {
        "list_pattern",
        "result_pattern",
        "list_args",
        "run_args",
        "filter_args",
        "success_value",
    }
)

# Cache for discovered test items: keyed by (parser_cls_name, binary, filter)
_discover_cache: Dict[Tuple[str, str, Optional[str]], "List[TestItem]"] = {}


###############################################################################
# Helpers — standard parsers
###############################################################################


def _read_parser_marker(
    node: pytest.Item,
) -> Tuple[Optional[str], Optional[str]]:
    """Extract binary name and optional filter from ``parser_binary`` marker.

    :param node: Pytest item or definition node.
    :return: Tuple of (binary, native_filter).  Both are ``None`` when
     the marker is absent.
    """
    marker = node.get_closest_marker("parser_binary")
    if marker is None:
        return None, None
    binary: Optional[str] = marker.args[0] if marker.args else None
    native_filter: Optional[str] = marker.kwargs.get("filter", None)
    return binary, native_filter


def _discover_tests(
    parser_cls: "Type[AbstractTestParser]",
    binary: str,
    native_filter: Optional[str],
) -> "List[TestItem]":
    """Discover tests for *binary* using *parser_cls*.

    Results are cached so that the same binary is not queried twice
    within one pytest session.

    :param parser_cls: Parser class to instantiate.
    :param binary: Binary name to query.
    :param native_filter: Optional fnmatch filter to apply.
    :return: List of TestItem objects.
    """
    cache_key = (parser_cls.__name__, binary, native_filter)
    if cache_key in _discover_cache:
        return _discover_cache[cache_key]

    product = getattr(pytest, "product", None)
    if product is None:
        return []
    core = product.core(0)
    temp_parser = parser_cls(core, binary)
    items = temp_parser.get_tests(filter=native_filter)
    _discover_cache[cache_key] = items
    return items


def _make_parser(
    cls: "Type[AbstractTestParser]", request: pytest.FixtureRequest
) -> "AbstractTestParser":
    """Instantiate a parser for the current parametrized test.

    :param cls: Parser class to instantiate.
    :param request: Pytest fixture request.
    :return: Configured parser instance.
    """
    test_name: Optional[str] = getattr(request, "param", None)
    binary, _ = _read_parser_marker(request.node)
    if binary is None:
        pytest.skip("No parser_binary marker on this test")
    core = pytest.product.core(0)
    return cls(core, binary, test_name=test_name)  # type: ignore[arg-type]


###############################################################################
# Helpers — custom parser
###############################################################################


def _build_custom_config(
    node: pytest.Item,
) -> Optional[CustomParserConfig]:
    """Build a CustomParserConfig from ``parser_binary`` marker kwargs.

    All kwargs except ``filter`` are forwarded to
    :class:`~ntfc.parsers.custom.CustomParserConfig`.  Returns ``None``
    when no custom config kwargs are present in the marker.

    :param node: Pytest item or definition node.
    :return: :class:`CustomParserConfig` instance, or ``None``.
    """
    marker = node.get_closest_marker("parser_binary")
    if marker is None:
        return None
    cfg_kwargs = {
        k: v for k, v in marker.kwargs.items() if k in _CUSTOM_CFG_KEYS
    }
    if not cfg_kwargs:
        return None
    return CustomParserConfig(**cfg_kwargs)


def _discover_custom_tests(
    binary: str,
    native_filter: Optional[str],
    config: CustomParserConfig,
) -> "List[TestItem]":
    """Discover tests for *binary* using :class:`CustomParser`.

    Uses the ``pytest.product`` global set by NTFC before the test
    session starts.  Returns an empty list when ``pytest.product`` is
    not available.

    :param binary: Binary name to query.
    :param native_filter: Optional fnmatch filter to apply.
    :param config: Custom parser configuration.
    :return: List of TestItem objects.
    """
    product = getattr(pytest, "product", None)
    if product is None:
        return []
    core = product.core(0)
    temp_parser = CustomParser(core, binary, config)
    return temp_parser.get_tests(filter=native_filter)


def _make_custom_parser(
    request: pytest.FixtureRequest,
) -> CustomParser:
    """Instantiate a :class:`CustomParser` for the current parametrized test.

    Reads binary and custom config from the ``parser_binary`` marker.

    :param request: Pytest fixture request.
    :return: Configured :class:`CustomParser` instance.
    """
    test_name: Optional[str] = getattr(request, "param", None)
    binary, _ = _read_parser_marker(request.node)
    if binary is None:
        pytest.skip("No parser_binary marker on this test")
    config = _build_custom_config(request.node)
    if config is None:
        pytest.skip("No custom config kwargs in parser_binary marker")
    core = pytest.product.core(0)
    return CustomParser(
        core, binary, config, test_name=test_name  # type: ignore[arg-type]
    )


###############################################################################
# Class: ParserPlugin
###############################################################################


class ParserPlugin:
    """Pytest plugin that turns test frameworks into parametrized items.

    Register the ``parser_binary`` marker and expand ``cmocka_parser`` /
    ``custom_parser`` fixtures into one pytest item per discovered C test
    case.
    """

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the ``parser_binary`` marker.

        :param config: Pytest config object.
        """
        _discover_cache.clear()

        config.addinivalue_line(
            "markers",
            "parser_binary(name, filter=None, **custom_cfg): "
            "binary to run via framework parser; pass list_pattern and "
            "result_pattern kwargs to use the custom_parser fixture",
        )

    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Parametrize parser fixtures based on discovered C tests.

        :param metafunc: Pytest Metafunc object for the current test.
        """
        for fixture_name, parser_cls in PARSER_FIXTURES.items():
            if fixture_name not in metafunc.fixturenames:
                continue

            binary, native_filter = _read_parser_marker(metafunc.definition)
            if binary is None:
                continue

            tests = _discover_tests(parser_cls, binary, native_filter)
            if not tests:
                continue

            metafunc.parametrize(
                fixture_name,
                [t.name for t in tests],
                indirect=True,
                ids=[t.name for t in tests],
            )

        if "custom_parser" not in metafunc.fixturenames:
            return

        binary, native_filter = _read_parser_marker(metafunc.definition)
        if binary is None:
            return

        config = _build_custom_config(metafunc.definition)
        if config is None:
            return

        tests = _discover_custom_tests(binary, native_filter, config)
        if not tests:
            return

        metafunc.parametrize(
            "custom_parser",
            [t.name for t in tests],
            indirect=True,
            ids=[t.name for t in tests],
        )

    @pytest.fixture  # type: ignore[untyped-decorator]
    def cmocka_parser(self, request: pytest.FixtureRequest) -> CmockaParser:
        """Fixture providing a CmockaParser for the current test case.

        :param request: Pytest fixture request (carries ``param``).
        :return: Configured CmockaParser instance.
        """
        parser = _make_parser(CmockaParser, request)
        return parser  # type: ignore[return-value]

    @pytest.fixture  # type: ignore[untyped-decorator]
    def custom_parser(self, request: pytest.FixtureRequest) -> CustomParser:
        """Fixture providing a CustomParser for the current test case.

        Requires a ``parser_binary`` marker with ``list_pattern`` and
        ``result_pattern`` kwargs on the test function.

        :param request: Pytest fixture request (carries ``param``).
        :return: Configured CustomParser instance.
        """
        return _make_custom_parser(request)
