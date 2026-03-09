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
from typing import TYPE_CHECKING, Dict, List, Optional

from ntfc.parsers.base import AbstractTestParser, TestItem, TestResult

if TYPE_CHECKING:
    from ntfc.lib.elf.elf_parser import ElfParser


###############################################################################
# Class: GtestParser
###############################################################################


class GtestParser(AbstractTestParser):
    """Parser for Google Test (gtest) test suites running on NuttX.

    Uses gtest CLI flags:

    * ``--gtest_list_tests`` to enumerate test names.
    * ``--gtest_filter=<pattern>`` to run a specific test or pattern.
    """

    _OK_FAIL_RE = re.compile(r"\[\s*(OK|FAILED)\s*\]\s+(\S+)")

    def _discover_from_elf(self, elf_parser: "ElfParser") -> List[TestItem]:
        """Return empty list; gtest registers tests at runtime.

        :param elf_parser: ELF parser instance (unused).
        :return: Always returns ``[]``.
        """
        return []

    def _discover_from_device(self) -> List[TestItem]:
        """Run ``<binary> --gtest_list_tests`` and parse the output.

        The output format is::

            Suite1.
              test_foo
              test_bar
            Suite2.
              test_baz

        Test names are returned as ``Suite.test_name``.

        :return: List of TestItem objects.
        """
        from ntfc.device.common import CmdStatus

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args="--gtest_list_tests"
        )
        if result.status != CmdStatus.SUCCESS:
            return []

        items: List[TestItem] = []
        suite: Optional[str] = None
        for line in result.output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not line.startswith(" ") and stripped.endswith("."):
                suite = stripped[:-1]
            elif line.startswith("  ") and suite is not None:
                test_name = f"{suite}.{stripped}"
                items.append(TestItem(name=test_name, suite=suite))
        return items

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
        """Run one test using ``--gtest_filter=<name>``.

        :param test_name: Test name to run.  Falls back to
         ``self._test_name`` when ``None``.
        :return: TestResult for the test.
        """
        name = test_name if test_name is not None else self._test_name
        if not name:
            return TestResult(name="", passed=False, output="no test name")

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=f"--gtest_filter={name}"
        )
        parsed = self._parse_output(result.output)
        if name in parsed:
            return parsed[name]
        return TestResult(name=name, passed=False, output=result.output)

    def run_all(self) -> Dict[str, TestResult]:
        """Run all tests with no filter flags.

        :return: Dict mapping test name to TestResult.
        """
        result = self._core.sendCommandReadUntilPattern(self._binary)
        self._results = self._parse_output(result.output)
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
