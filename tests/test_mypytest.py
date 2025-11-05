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

from ntfc.mypytest import MyPytest, _CollectedItem


def test_collector_collected_item():
    c = _CollectedItem("a", "b", "c", "d", "e", "f")

    assert c.directory == "a"
    assert c.module == "b"
    assert c.name == "c"
    assert c.path == "d"
    assert c.line == "e"
    assert c.nodeid == "f"


def test_collector_collect_file(config_dummy, device_dummy):

    p = MyPytest(config_dummy, device=[device_dummy])
    path = "./tests/resources/tests_collect/test_test1.py"
    items, skipped = p.collect(path)

    assert len(skipped) == 0

    assert items[0].name == "test_test1_simple_1"
    assert items[1].name == "test_test1_simple_2"


def test_collector_collect_dir(config_dummy, device_dummy):

    p = MyPytest(config_dummy, device=[device_dummy])
    path = "./tests/resources/tests_collect"
    items, skipped = p.collect(path)

    assert len(skipped) == 0

    assert len(items) == 7
    assert items[0].name == "test_test1_simple_1"
    assert items[1].name == "test_test1_simple_2"
    assert items[2].name == "test_test2_simple_1"
    assert items[3].name == "test_test2_simple_2"
    assert items[4].name == "test_test3_simple_1"
    assert items[5].name == "test_test3_simple_2"
    assert items[6].name == "test_test3_simple_3"


def test_runner_run_exitcode(config_dummy, device_dummy):

    p = MyPytest(config_dummy, device=[device_dummy])

    path = "./tests/resources/tests_exitcode/test_success.py"
    assert p.runner(path, {}) == 0

    path = "./tests/resources/tests_exitcode/test_fail.py"
    assert p.runner(path, {}) == 1

    path = "./tests/resources/tests_exitcode/test_empty.py"
    assert p.runner(path, {}) == 5

    # test directory - should fail due to test_fail.py
    path = "./tests/resources/tests_exitcode/"
    assert p.runner(path, {}) == 1
