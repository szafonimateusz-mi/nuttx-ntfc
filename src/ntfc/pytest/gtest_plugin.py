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

"""Pytest plugin for the Google Test (gtest) framework parser.

This is intentionally a *separate* plugin from
:class:`~ntfc.pytest.parsers.ParserPlugin` because gtest requires dirty
workarounds that do not fit the common parser interface:

* ``--gtest_list_tests`` does not exit cleanly on NuttX.
* Discovery therefore runs *all* tests up front (``run_all``) and caches
  the results at the class level (:attr:`GtestParser._session_results`).
* ``run_single`` returns immediately from that session cache, so no extra
  device round-trip is needed per test case.

Keeping these workarounds here and in :class:`~ntfc.parsers.gtest.GtestParser`
ensures that :class:`~ntfc.pytest.parsers.ParserPlugin` remains a clean,
gtest-unaware abstraction.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import pytest

from ntfc.parsers.gtest import GtestParser
from ntfc.pytest.parsers import _make_parser, _read_parser_marker

if TYPE_CHECKING:
    from ntfc.parsers.base import TestItem

# Discovery cache: (binary, filter) → List[TestItem]
# Prevents re-running the binary for multiple test functions that share
# the same parser_binary marker arguments.
_items_cache: Dict[Tuple[str, Optional[str]], "List[TestItem]"] = {}


###############################################################################
# Helpers
###############################################################################


def _discover_gtest_tests(
    binary: str,
    native_filter: Optional[str],
) -> "List[TestItem]":
    """Discover gtest tests for *binary* on the device.

    :param binary: NuttX shell command name of the gtest binary.
    :param native_filter: Optional fnmatch filter applied after discovery.
    :return: List of :class:`~ntfc.parsers.base.TestItem` objects.
    """
    product = getattr(pytest, "product", None)
    if product is None:
        return []
    core = product.core(0)
    parser = GtestParser(core, binary)
    return parser.get_tests(filter=native_filter)


###############################################################################
# Class: GtestParserPlugin
###############################################################################


class GtestParserPlugin:
    """Pytest plugin that parametrizes the ``gtest_parser`` fixture.

    Handles session-cache lifecycle, test discovery, and fixture
    instantiation for Google Test binaries.  All gtest-specific
    workaround logic lives here and in :class:`~ntfc.parsers.gtest.GtestParser`
    — :class:`~ntfc.pytest.parsers.ParserPlugin` remains unaware of gtest.
    """

    def pytest_configure(self, config: pytest.Config) -> None:
        """Empty configuration.

        We have to keep the cached items.

        :param config: Pytest config object.
        """

    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Parametrize ``gtest_parser`` based on discovered test cases.

        :param metafunc: Pytest Metafunc object for the current test.
        """
        if "gtest_parser" not in metafunc.fixturenames:
            return

        binary, native_filter = _read_parser_marker(metafunc.definition)
        if binary is None:
            return

        cache_key: Tuple[str, Optional[str]] = (binary, native_filter)
        if cache_key not in _items_cache:
            _items_cache[cache_key] = _discover_gtest_tests(
                binary, native_filter
            )
        tests = _items_cache[cache_key]
        if not tests:
            return

        metafunc.parametrize(
            "gtest_parser",
            [t.name for t in tests],
            indirect=True,
            ids=[t.name for t in tests],
        )

    @pytest.fixture  # type: ignore[untyped-decorator]
    def gtest_parser(self, request: pytest.FixtureRequest) -> GtestParser:
        """Fixture providing a :class:`~ntfc.parsers.gtest.GtestParser`.

        Results for the binary are already cached by discovery, so
        :meth:`~ntfc.parsers.gtest.GtestParser.run_single` returns
        immediately from the session cache without issuing a device command.

        :param request: Pytest fixture request (carries ``param``).
        :return: Configured :class:`~ntfc.parsers.gtest.GtestParser` instance.
        """
        return _make_parser(GtestParser, request)  # type: ignore[return-value]
