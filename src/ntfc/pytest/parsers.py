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

"""Pytest plugin that parametrizes C framework parser fixtures."""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type

import pytest

from ntfc.parsers.cmocka import CmockaParser

if TYPE_CHECKING:
    from ntfc.parsers.base import AbstractTestParser, TestItem

# Map fixture name → parser class
PARSER_FIXTURES: Dict[str, Type["AbstractTestParser"]] = {
    "cmocka_parser": CmockaParser,
}


###############################################################################
# Helpers
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

    Uses the ``pytest.product`` global set by NTFC before the test
    session starts.  Returns an empty list when ``pytest.product`` is
    not available.

    :param parser_cls: Parser class to instantiate.
    :param binary: Binary name to query.
    :param native_filter: Optional fnmatch filter to apply.
    :return: List of TestItem objects.
    """
    product = getattr(pytest, "product", None)
    if product is None:
        return []
    core = product.core(0)
    temp_parser = parser_cls(core, binary)
    return temp_parser.get_tests(filter=native_filter)


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
# Class: ParserPlugin
###############################################################################


class ParserPlugin:
    """Pytest plugin that turns C test frameworks into parametrized items.

    Register the ``parser_binary`` marker and expand ``cmocka_parser``
    fixtures into one pytest item per discovered C test case.
    """

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the ``parser_binary`` marker.

        :param config: Pytest config object.
        """
        config.addinivalue_line(
            "markers",
            "parser_binary(name, filter=None): "
            "binary to run via framework parser",
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

    @pytest.fixture  # type: ignore[untyped-decorator]
    def cmocka_parser(self, request: pytest.FixtureRequest) -> CmockaParser:
        """Fixture providing a CmockaParser for the current test case.

        :param request: Pytest fixture request (carries ``param``).
        :return: Configured CmockaParser instance.
        """
        parser = _make_parser(CmockaParser, request)
        return parser  # type: ignore[return-value]
