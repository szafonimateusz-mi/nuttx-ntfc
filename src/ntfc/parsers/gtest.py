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

"""Google Test (gtest) framework parser."""

import re
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional

from ntfc.parsers.base import AbstractTestParser, TestItem, TestResult

if TYPE_CHECKING:
    from ntfc.lib.elf.elf_parser import ElfParser


###############################################################################
# Class: GtestParser
###############################################################################


class GtestParser(AbstractTestParser):
    """Parser for Google Test (gtest) test suites running on NuttX.

    Discovery runs all tests once (``run_all``) and caches the results at
    the class level for the duration of the pytest session.  Subsequent
    calls to :meth:`run_single` return results from that cache without
    issuing a second device command.

    Uses gtest CLI flags:

    * ``run_all`` — no flags, runs every test and parses
      ``[  OK  ] / [FAILED]`` lines.
    * ``--gtest_filter=<pattern>`` to run a specific test or pattern.
    """

    _OK_FAIL_RE = re.compile(r"\[\s*(OK|FAILED|ERROR)\s*\]\s+(\S+)")

    # Session-scoped result cache: binary → {test_name → TestResult}
    _session_results: ClassVar[Dict[str, Dict[str, TestResult]]] = {}

    @classmethod
    def clear_session(cls) -> None:
        """Clear the session-scoped result cache.

        :meta public:
        :return: None.
        """
        cls._session_results.clear()

    def _discover_from_elf(self, elf_parser: "ElfParser") -> List[TestItem]:
        """Return empty list; gtest registers tests at runtime.

        :param elf_parser: ELF parser instance (unused).
        :return: Always returns ``[]``.
        """
        return []

    def _discover_from_device(self) -> List[TestItem]:
        """Run all tests once and derive test names from the results.

        On first call for a given binary the full test suite is executed
        via :meth:`run_all` and the results are stored in
        :attr:`_session_results`.  Subsequent calls return items directly
        from the cache without touching the device.

        :return: List of :class:`~ntfc.parsers.base.TestItem` objects.
        """
        if self._binary not in GtestParser._session_results:
            self.run_all()
        return [
            TestItem(
                name=name,
                suite=name.split(".")[0] if "." in name else None,
            )
            for name in GtestParser._session_results[self._binary]
        ]

    def _parse_output(self, output: str) -> Dict[str, TestResult]:
        """Parse gtest output into TestResult objects.

        Expected format::

            [       OK ] Suite.test_name (N ms)
            [  FAILED  ] Suite.test_name (N ms)

        :param output: Raw output string from the device.
        :return: Dict mapping test name to TestResult.
        """
        results: Dict[str, TestResult] = {}
        for match in self._OK_FAIL_RE.finditer(output):
            status, name = match.group(1), match.group(2)
            results[name] = TestResult(
                name=name,
                passed=(status == "OK"),
                output=output,
            )
        return results

    def run_single(self, test_name: Optional[str] = None) -> TestResult:
        """Return the cached result for *test_name*.

        If no session cache entry exists for the test, falls back to
        running it individually via ``--gtest_filter``.

        :param test_name: Test name to look up.  Falls back to
         ``self._test_name`` when ``None``.
        :return: :class:`~ntfc.parsers.base.TestResult` for the test.
        """
        name = test_name if test_name is not None else self._test_name
        if not name:
            return TestResult(name="", passed=False, output="no test name")

        cached = GtestParser._session_results.get(self._binary, {}).get(name)
        if cached is not None:
            return cached

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=f"--gtest_filter={name}"
        )
        parsed = self._parse_output(result.output)
        if name in parsed:
            return parsed[name]
        return TestResult(name=name, passed=False, output=result.output)

    def run_all(self) -> Dict[str, TestResult]:
        """Run all tests and populate the session cache.

        :return: Dict mapping test name to TestResult.
        """
        result = self._core.sendCommandReadUntilPattern(self._binary)
        self._results = self._parse_output(result.output)
        GtestParser._session_results[self._binary] = self._results
        return self._results

    def run_filtered(self, filter: str) -> Dict[str, TestResult]:  # noqa: A002
        """Run tests matching a gtest filter pattern.

        :param filter: Pattern passed to ``--gtest_filter``.
        :return: Dict mapping test name to TestResult.
        """
        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=f"--gtest_filter={filter}"
        )
        self._results = self._parse_output(result.output)
        return self._results
