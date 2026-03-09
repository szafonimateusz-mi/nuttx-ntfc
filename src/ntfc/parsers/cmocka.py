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

"""Cmocka test framework parser."""

import re
from typing import TYPE_CHECKING, Dict, List, Optional

from ntfc.parsers.base import AbstractTestParser, TestItem, TestResult

if TYPE_CHECKING:
    from ntfc.lib.elf.elf_parser import ElfParser


###############################################################################
# Class: CmockaParser
###############################################################################


class CmockaParser(AbstractTestParser):
    """Parser for cmocka-based C test suites running on NuttX.

    Uses the cmocka CLI flags:

    * ``--list`` to enumerate test names.
    * ``--test <name>`` to run a single test or a pattern.
    """

    _OK_FAIL_RE = re.compile(r"\[\s*(OK|FAIL)\s*\]\s+([^:\s]+)")

    # A suite header is a non-indented, identifier-only line (no spaces,
    # colons, slashes, dots, angle-brackets, equals-signs, or digits as
    # the very first character).
    _SUITE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    # A test-case line is indented with exactly four spaces followed by
    # an identifier.
    _TEST_RE = re.compile(r"^    ([A-Za-z_][A-Za-z0-9_]*)$")

    def _discover_from_elf(self, elf_parser: "ElfParser") -> List[TestItem]:
        """Return empty list; cmocka has no reliable symbol naming.

        :param elf_parser: ELF parser instance (unused).
        :return: Always returns ``[]``.
        """
        return []

    def _discover_from_device(self) -> List[TestItem]:
        """Run ``<binary> --list`` on the device and parse test names.

        The output format produced by the NuttX cmocka runner is::

            Cmocka Test Start.
            suite_name
                test_foo
                test_bar
            another_suite
                test_baz
            Cmocka Test Completed.

        Any line that is not a suite header or a 4-space-indented test
        name is treated as noise and silently ignored (e.g. error
        messages, usage text, ``devname =`` lines emitted by drivers
        before the test list).

        Suite headers are unindented lines that consist solely of ASCII
        identifier characters (``[A-Za-z_][A-Za-z0-9_]*``).  Test names
        are lines indented with exactly four spaces followed by the same
        character class.

        :return: List of TestItem objects.
        """
        from ntfc.device.common import CmdStatus

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args="--list"
        )
        if result.status != CmdStatus.SUCCESS:
            return []

        items: List[TestItem] = []
        suite: Optional[str] = None
        for line in result.output.splitlines():
            test_match = self._TEST_RE.match(line)
            if test_match:
                if suite is not None:
                    items.append(
                        TestItem(name=test_match.group(1), suite=suite)
                    )
                continue
            if self._SUITE_RE.match(line):
                suite = line
        return items

    def _parse_output(self, output: str) -> Dict[str, TestResult]:
        """Parse cmocka test output into TestResult objects.

        Expected format::

            [  OK  ] test_name: Test passed.
            [ FAIL ] test_name: assertion failed at ...

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
        """Run one test using ``--test <exact_name>``.

        :param test_name: Test name to run.  Falls back to
         ``self._test_name`` when ``None``.
        :return: TestResult for the test.
        """
        name = test_name if test_name is not None else self._test_name
        if not name:
            return TestResult(name="", passed=False, output="no test name")

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=f"--test {name}"
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
        """Run tests matching a pattern via ``--test <filter>``.

        :param filter: Pattern string passed to cmocka ``--test``.
        :return: Dict mapping test name to TestResult.
        """
        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=f"--test {filter}"
        )
        self._results = self._parse_output(result.output)
        return self._results
