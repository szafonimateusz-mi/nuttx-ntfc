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

"""Abstract test parser base classes for C framework integration."""

import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from ntfc.core import ProductCore
    from ntfc.lib.elf.elf_parser import ElfParser


###############################################################################
# Dataclasses
###############################################################################


@dataclass
class TestItem:
    """Represents a single C test case discovered from a binary.

    :param name: Test case name.
    :param suite: Optional suite name the test belongs to.
    """

    name: str
    suite: Optional[str] = None


@dataclass
class TestResult:
    """Holds the result of a single C test case execution.

    :param name: Test case name.
    :param passed: Whether the test passed.
    :param output: Raw output produced during the test run.
    :param duration: Optional duration in seconds.
    """

    name: str
    passed: bool
    output: str = field(default="")
    duration: Optional[float] = field(default=None)


###############################################################################
# Class: AbstractTestParser
###############################################################################


class AbstractTestParser(ABC):
    """Abstract base class for C test framework parsers.

    Subclasses implement framework-specific discovery and execution
    logic (e.g. cmocka).
    """

    def __init__(
        self,
        core: "ProductCore",
        binary: str,
        test_name: Optional[str] = None,
    ) -> None:
        """Initialise parser.

        :param core: ProductCore used to run commands on the device.
        :param binary: Name of the binary to invoke.
        :param test_name: Current parametrized test name (if any).
        """
        self._core = core
        self._binary = binary
        self._test_name = test_name
        self._results: Dict[str, TestResult] = {}

    @property
    def test_name(self) -> Optional[str]:
        """Return the current parametrized test name."""
        return self._test_name

    @abstractmethod
    def _discover_from_elf(self, elf_parser: "ElfParser") -> List[TestItem]:
        """Return items from ELF symbols.

        :param elf_parser: ELF parser instance.
        :return: List of TestItem objects, or ``[]`` if not supported.
        """

    @abstractmethod
    def _discover_from_device(self) -> List[TestItem]:
        """Run the binary on the device to list available tests.

        :return: List of TestItem objects.
        """

    def get_tests(
        self, filter: Optional[str] = None  # noqa: A002
    ) -> List[TestItem]:
        """Discover tests; ELF first then device fallback.

        :param filter: Optional fnmatch pattern to narrow the result set.
        :return: List of discovered TestItem objects.
        """
        from ntfc.lib.elf.elf_parser import ElfParser

        items: List[TestItem] = []

        elf_path = self._core.conf.elf_path
        if elf_path:
            try:
                elf_parser = ElfParser(elf_path)
                items = self._discover_from_elf(elf_parser)
            except AttributeError:
                items = []

        if not items:
            items = self._discover_from_device()

        if filter is not None:
            items = [i for i in items if fnmatch.fnmatch(i.name, filter)]

        return items

    @abstractmethod
    def run_single(self, test_name: Optional[str] = None) -> TestResult:
        """Run one test case.

        :param test_name: Test name to run.  Defaults to
         ``self._test_name`` when ``None``.
        :return: TestResult for the executed test.
        """

    @abstractmethod
    def run_all(self) -> Dict[str, TestResult]:
        """Run all tests and cache results in ``self._results``.

        :return: Dict mapping test name to TestResult.
        """

    @abstractmethod
    def run_filtered(self, filter: str) -> Dict[str, TestResult]:  # noqa: A002
        """Run tests matching a framework-native filter string.

        :param filter: Framework-specific filter / pattern string.
        :return: Dict mapping test name to TestResult.
        """

    def get_result(self, test_name: str) -> Optional[TestResult]:
        """Return a cached result from the last run.

        :param test_name: Test name to look up.
        :return: TestResult if found, ``None`` otherwise.
        """
        return self._results.get(test_name)
