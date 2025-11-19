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

import pytest  # type: ignore
from click.testing import CliRunner

from ntfc.cli.main import main


@pytest.fixture
def runner(mocker):
    return CliRunner()


def test_main(runner):
    result = runner.invoke(main)
    assert result.exit_code == 2

    args = ["--help"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["--help", "collect"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["--help", "test"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_collect(runner):
    args = [
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "--debug",
        "--verbose",
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_test(runner):
    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "--debug",
        "--verbose",
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
