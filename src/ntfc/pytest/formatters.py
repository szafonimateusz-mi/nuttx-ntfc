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

"""Pytest formatters for listing tests and modules."""

from typing import TYPE_CHECKING, Any, Dict, List

import pytest
from prettytable import PrettyTable

from ntfc.logger import logger

if TYPE_CHECKING:
    from ntfc.pytest.mypytest import MyPytest


###############################################################################
# List Functions
###############################################################################


def list_modules_run(pt: "MyPytest", ctx: Any) -> None:
    """List all available test modules."""
    assert ctx.testpath is not None
    col = pt.collect(ctx.testpath)

    # Group tests by module
    modules: Dict[str, List[str]] = {}
    for item in col.allitems:
        module = item.module2
        if module not in modules:
            modules[module] = []
        modules[module].append(f"{item.directory}/{item.name}")

    # Create table with elegant styling
    table = PrettyTable()
    table.field_names = ["#", "Module Name", "Tests", "Directory"]
    table.align["#"] = "r"
    table.align["Module Name"] = "l"
    table.align["Tests"] = "r"
    table.align["Directory"] = "l"

    # Custom border style
    table.horizontal_char = "─"
    table.vertical_char = "│"
    table.junction_char = "┼"

    # Add rows
    for idx, (module, tests) in enumerate(sorted(modules.items()), 1):
        # Get the directory path from first item
        first_item = next(
            (item for item in col.allitems if item.module2 == module), None
        )
        path = first_item.directory if first_item else "N/A"
        # Shorten path for better display
        if "/nuttx-testing/" in path:
            short_path = path.split("/nuttx-testing/")[1]
        else:
            short_path = path
        table.add_row([idx, module, len(tests), short_path])

    print("\n" + "=" * 100)
    print("  📦 AVAILABLE TEST MODULES")
    print("=" * 100)
    print(table)
    print(
        f"💡 Summary: {len(modules)} modules | {len(col.allitems)} total tests"
    )
    print("=" * 100 + "\n")


def list_tests_run(pt: "MyPytest", ctx: Any) -> None:
    """List all available tests with indexes."""
    assert ctx.testpath is not None

    # First initialize pytest to load ntfc.yaml
    pt._init_pytest(ctx.testpath)

    # Then apply module filter
    if ctx.modules:
        # Update pytest.cfgtest to filter by modules
        if not hasattr(pytest, "cfgtest"):
            pytest.cfgtest = {}
        # Merge with existing cfgtest (if any)
        if "module" not in pytest.cfgtest:
            pytest.cfgtest["module"] = {}
        pytest.cfgtest["module"]["include_module"] = ctx.modules

    # Now collect tests without re-initializing
    col = pt.collect(ctx.testpath, reinit=False)

    # Create table with elegant styling
    table = PrettyTable()
    table.field_names = ["Idx", "Module", "Test Case", "File"]
    table.align["Idx"] = "r"
    table.align["Module"] = "l"
    table.align["Test Case"] = "l"
    table.align["File"] = "l"

    # Custom border style
    table.horizontal_char = "─"
    table.vertical_char = "│"
    table.junction_char = "┼"

    # Set column widths
    table.max_width["Module"] = 35
    table.max_width["Test Case"] = 45
    table.max_width["File"] = 25

    # Add rows
    for idx, item in enumerate(col.items, 1):
        module = item.module2
        test_name = item.name
        filename = item.path.split("/")[-1]
        table.add_row([idx, module, test_name, filename])

    print("\n" + "=" * 120)
    print("  📋 AVAILABLE TEST CASES")
    print("=" * 120)
    print(table)

    # Print summary with emoji
    if len(col.skipped) > 0:
        print(
            f"💡 Summary: {len(col.items)} collected | {len(col.skipped)} skipped"
        )
    else:
        print(f"💡 Summary: {len(col.items)} collected tests")
    print("=" * 120 + "\n")
