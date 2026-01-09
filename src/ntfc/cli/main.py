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

"""Module containing the CLI logic for NTFC."""

import json
import pprint
import sys
from typing import Any, Dict

import click
import yaml  # type: ignore

from ntfc.builder import NuttXBuilder
from ntfc.cli.environment import Environment, pass_environment
from ntfc.logger import logger
from ntfc.plugins_loader import commands_list
from ntfc.pytest.collector import *
from ntfc.pytest.formatters import *
from ntfc.pytest.mypytest import MyPytest
from ntfc.pytest.runner import *

###############################################################################
# Function: main
###############################################################################


@click.group()
@click.option(
    "--debug/--no-debug",
    default=False,
    is_flag=True,
)
@click.option(
    "--verbose/--no-verbose",
    default=False,
    is_flag=True,
)
@pass_environment
def main(ctx: Environment, debug: bool, verbose: bool) -> bool:
    """VFTC - NuttX Testing Framework for Community."""
    ctx.debug = debug
    ctx.verbose = verbose

    if debug:  # pragma: no cover
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

    # handle work after all commands are parsed
    click.get_current_context().call_on_close(cli_on_close)

    # check if --help was called
    if "--help" in sys.argv[1:]:  # pragma: no cover
        ctx.helpnow = True

    return True


def print_yaml_config(config: Dict[str, Any]) -> None:
    """Print YAML configuration."""
    print("YAML config:")
    pp = pprint.PrettyPrinter()
    pp.pprint(config)


def print_json_config(config: Dict[str, Any]) -> None:
    """Print JSON configuration."""
    print("JSON config:")
    pp = pprint.PrettyPrinter()
    pp.pprint(config)


@pass_environment
def cli_on_close(ctx: Environment) -> bool:
    """Handle all work on Click close."""
    if ctx.helpnow:  # pragma: no cover
        # do nothing if help was called
        return True

    conf = None
    logger.info(f"YAML config file {ctx.confpath}")
    assert ctx.confpath is not None
    with open(ctx.confpath, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)

    conf["config"]["loops"] = ctx.loops

    conf_json = {}
    if ctx.jsonconf:  # pragma: no cover
        logger.info(f"Module config file {ctx.jsonconf}")
        with open(ctx.jsonconf, "r", encoding="utf-8") as f:
            conf_json = json.load(f)

    print_yaml_config(conf)
    print_json_config(conf_json)

    builder = NuttXBuilder(conf, ctx.rebuild)
    if builder.need_build():
        builder.build_all()
        if ctx.flash:
            builder.flash_all()

        # update config
        conf = builder.new_conf()

    # exit now when build only mode
    if ctx.runbuild:
        return True

    pt = MyPytest(conf, ctx.exitonfail, ctx.verbose, conf_json)

    # Handle --list-modules option
    if ctx.list_modules:
        list_modules_run(pt, ctx)
        return True

    # Handle --list-tests or -l option
    if ctx.list_tests:
        list_tests_run(pt, ctx)
        return True

    # Handle --index/-i option (select and run individual tests)
    if ctx.select_individual_tests:
        select_tests_run(pt, ctx)
        return True

    if ctx.runcollect:
        collect_run(pt, ctx)

    if ctx.runtest:
        ret = test_run(pt, ctx)
        if ret != 0:
            exit(1)

    return True


###############################################################################
# Function: click_final_init
###############################################################################


def click_final_init() -> None:
    """Handle final Click initialization."""
    # add interfaces
    for cmd in commands_list:
        main.add_command(cmd)


# final click initialization
click_final_init()
