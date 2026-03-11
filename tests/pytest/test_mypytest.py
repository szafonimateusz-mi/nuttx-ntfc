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

import json
from unittest.mock import patch

from ntfc.pytest.mypytest import MyPytest


def test_collector_collect_file(config_sim, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        p = MyPytest(config_sim)
        path = "./tests/resources/tests_collect/test_test1.py"
        col = p.collect(path)

        assert len(col.skipped) == 0
        assert len(col.modules) == 1

        assert col.items[0].name == "test_test1_simple_1"
        assert col.items[1].name == "test_test1_simple_2"

        p = MyPytest(config_sim)
        path = "./tests/resources/tests_collect/test_test4.py"
        col = p.collect(path)

        assert len(col.allitems) == 5
        assert len(col.skipped) == 3
        assert len(col.items) == 2
        assert len(col.modules) == 1

        assert col.skipped[0][0].location[2] == "test_test4_simple_2"
        assert col.skipped[1][0].location[2] == "test_test4_simple_4"
        assert col.skipped[2][0].location[2] == "test_test4_simple_5"

        assert col.items[0].name == "test_test4_simple_1"
        assert col.items[1].name == "test_test4_simple_3"


def test_collector_collect_dir(config_sim, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        p = MyPytest(config_sim)
        path = "./tests/resources/tests_collect"
        col = p.collect(path)

        assert len(col.allitems) == 12
        assert len(col.skipped) == 3
        assert len(col.items) == 9
        assert len(col.modules) == 1

        assert col.skipped[0][0].location[2] == "test_test4_simple_2"
        assert col.skipped[1][0].location[2] == "test_test4_simple_4"
        assert col.skipped[2][0].location[2] == "test_test4_simple_5"

        assert col.items[0].name == "test_test1_simple_1"
        assert col.items[1].name == "test_test1_simple_2"
        assert col.items[2].name == "test_test2_simple_1"
        assert col.items[3].name == "test_test2_simple_2"
        assert col.items[4].name == "test_test3_simple_1"
        assert col.items[5].name == "test_test3_simple_2"
        assert col.items[6].name == "test_test3_simple_3"
        assert col.items[7].name == "test_test4_simple_1"
        assert col.items[8].name == "test_test4_simple_3"


def test_collector_collect_manydirs(config_sim, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        p = MyPytest(config_sim)
        path = "./tests/resources/tests_dirs"
        col = p.collect(path)

        assert len(col.allitems) == 8
        assert len(col.skipped) == 0
        assert len(col.items) == 8
        assert len(col.modules) == 3
        assert "test_Test1" in col.modules
        assert "test_Test2" in col.modules
        assert "test_Test3_Test4" in col.modules


def test_runner_module_exclude(config_sim, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        path = "./tests/resources/nuttx/sim/module_exclude.json"
        with open(path, "r") as f:
            jsoncfg = json.load(f)

        p = MyPytest(config_sim, confjson=jsoncfg)
        path = "./tests/resources/tests_dirs"
        col = p.collect(path)

        assert len(col.allitems) == 8
        assert len(col.skipped) == 2
        assert len(col.items) == 6
        assert len(col.modules) == 2


def test_runner_module_include(config_sim, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        path = "./tests/resources/nuttx/sim/module_include.json"
        with open(path, "r") as f:
            jsoncfg = json.load(f)

        p = MyPytest(config_sim, confjson=jsoncfg)
        path = "./tests/resources/tests_dirs"
        col = p.collect(path)

        assert len(col.allitems) == 8
        assert len(col.skipped) == 6
        assert len(col.items) == 2
        assert len(col.modules) == 1


def test_runner_run_exitcode(config_dummy, device_dummy):

    with patch("ntfc.cores.get_device", return_value=device_dummy):

        p = MyPytest(config_dummy)

        path = "./tests/resources/tests_exitcode/test_success.py"
        assert p.runner(path, {}) == 0

        path = "./tests/resources/tests_exitcode/test_fail.py"
        assert p.runner(path, {}) == 1

        path = "./tests/resources/tests_exitcode/test_empty.py"
        assert p.runner(path, {}) == 5

        # test directory - should fail due to test_fail.py
        path = "./tests/resources/tests_exitcode/"
        assert p.runner(path, {}) == 1


def test_runner_run_device_starts_when_not_alive(
    config_dummy, device_dummy, monkeypatch
):
    """_device_start calls product.start/init when device is not yet alive."""
    with patch("ntfc.cores.get_device", return_value=device_dummy):
        # notalive=True before start(), False afterwards (tied to _open flag)
        monkeypatch.setattr(
            type(device_dummy),
            "notalive",
            property(lambda self: not self._open),
        )
        p = MyPytest(config_dummy)
        path = "./tests/resources/tests_exitcode/test_success.py"
        assert p.runner(path, {}) == 0


def test_write_session_config_file(config_dummy, tmp_path):
    p = MyPytest(config_dummy)

    p._write_session_config(str(tmp_path))

    path = tmp_path / "session.config.txt"
    assert path.is_file()

    with open(path, "r", encoding="utf-8") as f:
        merged = json.load(f)

    assert merged == config_dummy
