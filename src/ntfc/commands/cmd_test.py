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

"""Module containing NTFC test command."""

import importlib.util
from typing import Any, Tuple

import click

from ntfc.cli.clitypes import cli_testenv_options
from ntfc.cli.environment import Environment, pass_environment

HAS_PYTEST_HTML = importlib.util.find_spec("pytest_html") is not None
HAS_PYTEST_JSON = importlib.util.find_spec("pytest_json") is not None

###############################################################################
# Command: cmd_test
###############################################################################


@click.command(name="test")
@cli_testenv_options
@pass_environment
@click.option(
    "-c",
    "--modules",
    type=str,
    help='Execute specific test module(s). Use quotes for multiple: -c "module1 module2" or -c module1,module2',
)
@click.option(
    "-i",
    "--index",
    "select_individual_tests",
    multiple=True,
    type=int,
    help="Select and execute individual tests by index. Use with -l to see indexes.",
)
@click.option(
    "--loops",
    type=int,
    default=1,
    help="Number of times to run each test case. Default: 1.",
)
@click.option(
    "-l",
    "--list-tests",
    is_flag=True,
    default=False,
    help="List all available test cases with their indexes.",
)
@click.option(
    "--list-modules",
    is_flag=True,
    default=False,
    help="List all available test modules.",
)
@click.option(
    "--flash",
    is_flag=True,
    default=False,
    help="Flash image. Default: False",
)
@click.option(
    "--jsonconf",
    type=click.Path(resolve_path=False),
    default="",
    help="Path to test session configuration file. Default: None",
)
@click.option(
    "--nologs",
    default=False,
    is_flag=True,
)
@click.option(
    "--exitonfail/--no-exitonfail",
    default=False,
    is_flag=True,
)
@click.option(
    "--xml",
    is_flag=True,
    help="Store the XML report.",
)
@click.option(
    "--resdir",
    type=click.Path(resolve_path=False),
    default="./result",
    help="Where to store the test results. Default: ./result",
)
def cmd_test(
    ctx: Environment,
    /,  # noqa: ARG001
    testpath: str,
    confpath: str,
    rebuild: bool,
    flash: bool,
    jsonconf: str,
    nologs: bool,
    exitonfail: bool,
    modules: str,
    select_individual_tests: Tuple[int, ...],
    loops: int,
    list_tests: bool,
    list_modules: bool,
    **kwargs: Any,
) -> bool:
    """Run tests."""
    ctx.runtest = True
    ctx.testpath = testpath
    ctx.confpath = confpath
    ctx.rebuild = rebuild
    ctx.flash = flash
    ctx.jsonconf = jsonconf
    ctx.nologs = nologs
    ctx.exitonfail = exitonfail
    ctx.modules = None
    if modules:
        module_list = modules.replace(",", " ").split()
        ctx.modules = module_list if module_list else None

    ctx.select_individual_tests = (
        list(select_individual_tests) if select_individual_tests else None
    )
    ctx.loops = loops
    ctx.list_tests = list_tests
    ctx.list_modules = list_modules

    ctx.result = {}
    ctx.result["resdir"] = kwargs.get("resdir")
    ctx.result["html"] = kwargs.get("html")
    ctx.result["json"] = kwargs.get("json")
    ctx.result["xml"] = kwargs.get("xml")

    return True


# optional json output
if HAS_PYTEST_JSON:  # pragma: no cover
    cmd_test = click.option(
        "--json",
        is_flag=True,
        help="Store the JSON report.",
    )(cmd_test)

# optional html output
if HAS_PYTEST_HTML:  # pragma: no cover
    cmd_test = click.option(
        "--html",
        is_flag=True,
        help="Store the HTML report.",
    )(cmd_test)
