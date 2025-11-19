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

"""Module containing the Click types."""

from typing import Any

import click

############################################################################
# Decorator: testenv_options
############################################################################


# common test env options
_testenv_options = (
    click.option(
        "--testpath",
        type=click.Path(resolve_path=False),
        default="./external/nuttx-testing",
        help="Path to test cases. Can be also set with environment"
        " variable NTFC_TESTPATH. Default: ./external/nuttx-testing",
        envvar="NTFC_TESTPATH",
    ),
    click.option(
        "--confpath",
        type=click.Path(resolve_path=False),
        default="./external/config.yaml",
        help="Path to test configuration file. Can be also set with "
        "environment variable NTFC_CONFPATH. "
        "Default: ./external/config.yaml",
        envvar="NTFC_CONFPATH",
    ),
    click.option(
        "--ignorefile",
        type=click.Path(resolve_path=False),
        default="./external/ignore.txt",
        help="Path to file with test ignore rules."
        "Default: ./external/ignore.txt",
    ),
)


def cli_testenv_options(fn: Any) -> Any:
    """Decorate command with common test env options decorator."""
    for decorator in reversed(_testenv_options):
        fn = decorator(fn)
    return fn
