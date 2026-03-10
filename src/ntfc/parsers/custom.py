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

"""Custom test parser with user-defined regular expressions."""

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from ntfc.parsers.base import AbstractTestParser, TestItem, TestResult

if TYPE_CHECKING:
    from ntfc.core import ProductCore
    from ntfc.lib.elf.elf_parser import ElfParser


###############################################################################
# Helpers
###############################################################################


def _check_named_groups(
    pattern: str,
    required: Set[str],
    field_name: str,
) -> None:
    """Validate that *pattern* contains all *required* named capture groups.

    :param pattern: Regular expression string to compile and inspect.
    :param required: Set of group names that must appear in *pattern*.
    :param field_name: Config attribute name used in error messages.
    :raises ValueError: If *pattern* is not valid regex or a required
        named group is absent.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ValueError(
            f"{field_name!r} is not a valid regex: {exc}"
        ) from exc
    missing = required - set(compiled.groupindex)
    if missing:
        raise ValueError(
            f"{field_name!r} missing required named group(s): "
            + ", ".join(sorted(missing))
        )


###############################################################################
# Config
###############################################################################


@dataclass
class CustomParserConfig:
    """Configuration for a regex-driven custom test parser.

    Pass an instance of this class to :class:`CustomParser` to define how
    the parser discovers tests and interprets their results.

    :param list_pattern: Regex with a ``name`` named group (and optionally
        a ``suite`` named group) applied to each line of the list-command
        output to extract test items.
    :param result_pattern: Regex with ``name`` and ``status`` named groups
        applied to the run output to identify test results.
    :param list_args: Arguments passed to the binary to enumerate tests.
        Defaults to ``"--list"``.
    :param run_args: Argument template for running a single test.  Use
        ``{name}`` as the placeholder for the test name.
        Defaults to ``"{name}"``.
    :param filter_args: Argument template for
        :meth:`CustomParser.run_filtered`.  Use ``{filter}`` as the
        placeholder.  Defaults to ``"{filter}"``.
    :param success_value: Value of the ``status`` capture group that
        indicates a passing test.  Defaults to ``"PASS"``.
    """

    list_pattern: str
    result_pattern: str
    list_args: str = field(default="--list")
    run_args: str = field(default="{name}")
    filter_args: str = field(default="{filter}")
    success_value: str = field(default="PASS")

    def __post_init__(self) -> None:
        """Validate that required named groups are present in patterns.

        :raises ValueError: If a required named group is absent or a
            pattern is not valid regex.
        """
        _check_named_groups(self.list_pattern, {"name"}, "list_pattern")
        _check_named_groups(
            self.result_pattern, {"name", "status"}, "result_pattern"
        )


###############################################################################
# Class: CustomParser
###############################################################################


class CustomParser(AbstractTestParser):
    r"""Parser driven entirely by user-supplied regular expressions.

    Pass a :class:`CustomParserConfig` to control how the parser discovers
    test items and interprets run output.

    **Named groups in** ``list_pattern``:

    * ``name`` *(required)* – test case name.
    * ``suite`` *(optional)* – suite the test belongs to.

    **Named groups in** ``result_pattern``:

    * ``name`` *(required)* – test case name.
    * ``status`` *(required)* – raw status string; compared against
      ``config.success_value`` (case-sensitive) to decide pass/fail.

    Example configuration::

        config = CustomParserConfig(
            list_pattern=r"TEST:\s+(?P<name>\w+)",
            result_pattern=r"(?P<status>PASS|FAIL)\s+(?P<name>\w+)",
            list_args="--list",
            run_args="--run {name}",
            success_value="PASS",
        )
        parser = CustomParser(core, "mybin", config)
    """

    def __init__(
        self,
        core: "ProductCore",
        binary: str,
        config: CustomParserConfig,
        test_name: Optional[str] = None,
    ) -> None:
        """Initialise the custom parser.

        :param core: ProductCore used to run commands on the device.
        :param binary: Name of the binary to invoke.
        :param config: Parser configuration with patterns and templates.
        :param test_name: Current parametrized test name (if any).
        """
        super().__init__(core, binary, test_name)
        self._cfg = config
        self._list_re = re.compile(config.list_pattern)
        self._result_re = re.compile(config.result_pattern)

    def _discover_from_elf(self, elf_parser: "ElfParser") -> List[TestItem]:
        """Return empty list; ELF discovery is not supported.

        :param elf_parser: ELF parser instance (unused).
        :return: Always returns ``[]``.
        """
        return []

    def _discover_from_device(self) -> List[TestItem]:
        """Run the list command and extract test names with ``list_pattern``.

        Each output line is matched against ``config.list_pattern``.  Lines
        that do not match are silently skipped.  The ``name`` named group
        is required; ``suite`` is included when present in the pattern and
        matched.

        :return: List of :class:`~ntfc.parsers.base.TestItem` objects.
        """
        from ntfc.device.common import CmdStatus

        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=self._cfg.list_args
        )
        if result.status != CmdStatus.SUCCESS:
            return []

        items: List[TestItem] = []
        for line in result.output.splitlines():
            m = self._list_re.search(line)
            if m:
                gd = m.groupdict()
                items.append(TestItem(name=gd["name"], suite=gd.get("suite")))
        return items

    def _parse_output(self, output: str) -> Dict[str, TestResult]:
        """Parse run output into TestResult objects.

        Iterates over all matches of ``config.result_pattern`` in *output*.
        The ``status`` group value is compared to ``config.success_value``
        (case-sensitive) to determine pass/fail.

        :param output: Raw output string from the device.
        :return: Dict mapping test name to
            :class:`~ntfc.parsers.base.TestResult`.
        """
        results: Dict[str, TestResult] = {}
        for m in self._result_re.finditer(output):
            gd = m.groupdict()
            name: str = gd["name"]
            results[name] = TestResult(
                name=name,
                passed=(gd["status"] == self._cfg.success_value),
                output=output,
            )
        return results

    def run_single(self, test_name: Optional[str] = None) -> TestResult:
        """Run one test case using the ``run_args`` template.

        The ``run_args`` template is expanded with the test name before
        being passed to the binary.

        :param test_name: Test name to run.  Falls back to
            ``self._test_name`` when ``None``.
        :return: :class:`~ntfc.parsers.base.TestResult` for the executed
            test.
        """
        name = test_name if test_name is not None else self._test_name
        if not name:
            return TestResult(name="", passed=False, output="no test name")

        args = self._cfg.run_args.format(name=name)
        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=args
        )
        parsed = self._parse_output(result.output)
        if name in parsed:
            return parsed[name]
        return TestResult(name=name, passed=False, output=result.output)

    def run_all(self) -> Dict[str, TestResult]:
        """Run the binary without extra arguments and parse the output.

        :return: Dict mapping test name to
            :class:`~ntfc.parsers.base.TestResult`.
        """
        result = self._core.sendCommandReadUntilPattern(self._binary)
        self._results = self._parse_output(result.output)
        return self._results

    def run_filtered(self, filter: str) -> Dict[str, TestResult]:  # noqa: A002
        """Run the binary with the ``filter_args`` template expanded.

        :param filter: Filter string substituted into
            ``config.filter_args``.
        :return: Dict mapping test name to
            :class:`~ntfc.parsers.base.TestResult`.
        """
        args = self._cfg.filter_args.format(filter=filter)
        result = self._core.sendCommandReadUntilPattern(
            self._binary, args=args
        )
        self._results = self._parse_output(result.output)
        return self._results
