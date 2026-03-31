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

import time

import pytest

from ntfc.parallel import run_parallel


def test_run_parallel_empty_returns_empty_list() -> None:
    assert run_parallel([], lambda item: item) == []


def test_run_parallel_preserves_input_order() -> None:
    items = [1, 2, 3]

    def worker(item: int) -> int:
        # Delay inversely to item value to force out-of-order completion.
        time.sleep((4 - item) * 0.01)
        return item * 10

    assert run_parallel(items, worker) == [10, 20, 30]


def test_run_parallel_propagates_worker_exception() -> None:
    def worker(item: int) -> int:
        if item == 2:
            raise ValueError("boom")
        return item

    with pytest.raises(ValueError, match="boom"):
        run_parallel([1, 2, 3], worker)
