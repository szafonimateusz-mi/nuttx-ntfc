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

import click

from ntfc.cli.clitypes import cli_testenv_options
from ntfc.cli.environment import Environment, pass_environment

HAS_PYTEST_HTML = importlib.util.find_spec("pytest_html") is not None
HAS_PYTEST_JSON = importlib.util.find_spec("pytest_json") is not None

###############################################################################
# Command: cmd_test
###############################################################################


@click.command(name="test")
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
@cli_testenv_options
@pass_environment
def cmd_test(
    ctx: Environment,
    testpath: str,
    confpath: str,
    ignorefile: str,
    nologs: bool,
    exitonfail: bool,
    **kwargs,
) -> bool:
    """Run tests."""
    ctx.runtest = True
    ctx.testpath = testpath
    ctx.confpath = confpath
    ctx.ignorefile = ignorefile
    ctx.nologs = nologs
    ctx.exitonfail = exitonfail

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
