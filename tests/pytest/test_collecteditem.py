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

from ntfc.pytest.collecteditem import CollectedItem


def test_collector_collected_item():
    c = CollectedItem("a", "b", "c", "d", "e", "f::f", "U", "/aaa/bbb/ccc.py")

    assert c.directory == "a"
    assert c.module == "b"
    assert c.name == "c"
    assert c.path == "d"
    assert c.line == "e"
    assert c.nodeid == "f::f"
    assert c.nodeid_abs == "d::f"
    assert c.module2 == "U_Aaa_Bbb"

    print(c)
