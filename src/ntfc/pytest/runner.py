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

"""NTFC runner plugin for pytest."""

import os
from typing import TYPE_CHECKING, Any, Dict

import pytest

from ntfc.logger import logger

if TYPE_CHECKING:
    from ntfc.pytest.mypytest import MyPytest

###############################################################################
# Class: RunnerPlugin
###############################################################################


class RunnerPlugin:
    """Pytest runner plugin that is called we we run test command."""

    def __init__(self, nologs: bool = False) -> None:
        """Initialize custom pytest test runner plugin."""
        self._logs: Dict[str, Dict[str, Any]] = {}
        self._nologs = nologs

    def _collect_device_logs_teardown(self) -> None:
        """Teardown for device log."""
        # stop device log collector
        if self._nologs:
            return

        for product in pytest.products:
            product.stop_log_collect()

            for core in product.cores:
                # close files
                self._logs[product.name][core]["console"].close()

    def _collect_device_logs(self, request: Any) -> None:
        """Initiate device log writing into a new test file."""
        if self._nologs:
            return

        testname = request.node.name

        # prepare log files
        for product in pytest.products:
            name = product.name
            product_dir = os.path.join(pytest.result_dir, name)

            for core in product.cores:
                core_dir = os.path.join(product_dir, core)

                if name not in self._logs:
                    self._logs[name] = {}

                if core not in self._logs[name]:
                    os.makedirs(core_dir, exist_ok=True)
                    self._logs[name][core] = {}

                # open log files
                tmp = os.path.join(core_dir, testname + ".console.txt")
                self._logs[name][core]["console"] = open(
                    tmp, "a", encoding="utf-8"
                )

        # start logging for all products
        for product in pytest.products:
            name = product.name
            # start device log collector
            product.start_log_collect(self._logs[name])

    @pytest.fixture(scope="function", autouse=True)  # type: ignore
    def prepare_test(self, request: Any) -> None:
        """Prepare test case."""
        # initialize log collector
        self._collect_device_logs(request)
        # register log collector teardown
        request.addfinalizer(self._collect_device_logs_teardown)

    @pytest.fixture  # type: ignore
    def switch_to_core(self) -> None:
        """Switch to core."""

    @pytest.fixture  # type: ignore
    def core(self) -> None:
        """Get active core."""


###############################################################################
# Test Run Functions
###############################################################################


def test_run(pt: "MyPytest", ctx: Any) -> Any:
    """Run tests."""
    assert ctx.testpath is not None
    assert ctx.result is not None

    # Initialize pytest and apply module filter before running tests
    pt._init_pytest(ctx.testpath)

    # Apply module filter if specified
    if ctx.modules:
        if not hasattr(pytest, "cfgtest"):
            pytest.cfgtest = {}
        if "module" not in pytest.cfgtest:
            pytest.cfgtest["module"] = {}
        pytest.cfgtest["module"]["include_module"] = ctx.modules
        logger.info(f"Running tests from modules: {ctx.modules}")

    # Run tests without re-initializing (to preserve module filter)
    return pt.runner(
        ctx.testpath,
        ctx.result if isinstance(ctx.result, dict) else {},
        ctx.nologs,
        None,
        ctx.loops,
        reinit=False,
    )


def select_tests_run(pt: "MyPytest", ctx: Any) -> None:
    """Select and run individual tests by index."""
    assert ctx.testpath is not None
    assert ctx.select_individual_tests is not None

    # First collect to get test list
    col = pt.collect(ctx.testpath)

    # Validate indexes
    invalid_indexes = [
        i for i in ctx.select_individual_tests if i < 1 or i > len(col.items)
    ]
    if invalid_indexes:
        logger.error(f"❌ Invalid test indexes: {invalid_indexes}")
        logger.error(f"❌ Valid range: 1-{len(col.items)}")
        return

    # Get selected tests
    selected_tests = [col.items[i - 1] for i in ctx.select_individual_tests]

    # Display selected tests
    print("\n" + "=" * 100)
    print(f"  🚀 RUNNING {len(selected_tests)} SELECTED TEST(S)")
    if ctx.loops > 1:
        print(f"  🔄 Loops: {ctx.loops}")
    print("=" * 100)

    # Create table for selected tests
    from prettytable import PrettyTable

    table = PrettyTable()
    table.field_names = ["Idx", "Module", "Test Case"]
    table.align["Idx"] = "r"
    table.align["Module"] = "l"
    table.align["Test Case"] = "l"
    table.max_width["Module"] = 40
    table.max_width["Test Case"] = 50

    # Custom border style
    table.horizontal_char = "─"
    table.vertical_char = "│"
    table.junction_char = "┼"

    for idx, test in zip(ctx.select_individual_tests, selected_tests):
        table.add_row([idx, test.module2, test.name])

    print(table)
    print("=" * 100 + "\n")

    # Convert selected tests to pytest node IDs
    selected_nodeids = [item.nodeid for item in selected_tests]

    # Update test collection to only run selected tests
    pt.runner(
        ctx.testpath,
        ctx.result if isinstance(ctx.result, dict) else {},
        ctx.nologs,
        selected_tests=selected_nodeids,
        loops=ctx.loops,
    )
