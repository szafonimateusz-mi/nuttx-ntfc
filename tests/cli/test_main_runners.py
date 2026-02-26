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
from ntfc.products import ProductsHandler


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
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
        "all",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
        "collected",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
        "skipped",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
        "silent",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_collect_debug(runner):

    args = [
        "--debug",
        "--verbose",
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect/test_test1.py",
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


def test_main_build(runner, monkeypatch):

    def fake_run_command(cmd, check, env):
        return

    monkeypatch.setattr("subprocess.run", fake_run_command)

    args = [
        "build",
        "--confpath=./tests/resources/nuttx/sim/config_build.yaml",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    # nothing to build
    args = [
        "build",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "build",
        "--confpath=./tests/resources/nuttx/sim/config_build.yaml",
        "--no-flash",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_test_simple(runner, monkeypatch):
    monkeypatch.setattr(
        "ntfc.pytest.mypytest.MyPytest._device_start",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ProductsHandler,
        "notalive",
        property(lambda _self: False),
    )

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--nologs",
        "--exitonfail",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_test_debug(runner, monkeypatch):
    monkeypatch.setattr(
        "ntfc.pytest.mypytest.MyPytest._device_start",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ProductsHandler,
        "notalive",
        property(lambda _self: False),
    )

    args = [
        "--debug",
        "--verbose",
        "collect",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "--debug",
        "--verbose",
        "test",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
        "--loops=2",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_test_rebuild_default_and_override(runner, monkeypatch):
    seen = []

    def fake_load_config_files(ctx):
        seen.append(ctx.rebuild)
        return (
            {
                "config": {"cwd": "./", "loops": 1},
                "product": {"name": "p", "cores": {"core0": {"name": "c"}}},
            },
            {},
        )

    class DummyPytest:
        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(
        "ntfc.cli.main.load_config_files", fake_load_config_files
    )
    monkeypatch.setattr("ntfc.cli.main.MyPytest", DummyPytest)
    monkeypatch.setattr(
        "ntfc.cli.main.collect_run", lambda *_args, **_kwargs: None
    )

    args = [
        "test",
        "--collect-only",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--collect-only",
        "--no-rebuild",
        "--confpath=./tests/resources/nuttx/sim/config.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    assert seen == [True, False]


def test_main_test_modules(runner, monkeypatch):
    monkeypatch.setattr(
        "ntfc.pytest.mypytest.MyPytest._device_start",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ProductsHandler,
        "notalive",
        property(lambda _self: False),
    )

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--list-modules",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--modules=test_Test1",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--modules=test_Test1,test_Test2",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_test_tests(runner, monkeypatch):
    monkeypatch.setattr(
        "ntfc.pytest.mypytest.MyPytest._device_start",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ProductsHandler,
        "notalive",
        property(lambda _self: False),
    )

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--list-tests",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--index=100",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--index=1",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_simple.yaml",
        "--testpath=./tests/resources/tests_dirs",
        "--index=1",
        "--loops=2",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


@pytest.mark.skip("not ready for CI")
def test_main_build_test(runner, monkeypatch):  # pragma: no cover

    def fake_run_command1(pt, ctx):
        return 0

    monkeypatch.setattr("ntfc.cli.main.tests_run", fake_run_command1)

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_build.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    def fake_run_command2(pt, ctx):
        return 1

    monkeypatch.setattr("ntfc.cli.main.tests_run", fake_run_command2)

    args = [
        "test",
        "--confpath=./tests/resources/nuttx/sim/config_build.yaml",
        "--testpath=./tests/resources/tests_collect",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 1
