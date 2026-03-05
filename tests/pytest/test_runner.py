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

from ntfc.pytest.runner import RunnerPlugin


def test_test_pytestrunnerplugin_init():
    _ = RunnerPlugin(False)
    _ = RunnerPlugin(True)


def test_pytest_sessionfinish_no_result_dir():
    """Test pytest_sessionfinish when result_dir not available."""
    import pytest as pytest_module

    plugin = RunnerPlugin(False)

    # Save original values
    old_products = getattr(pytest_module, "products", None)
    old_result_dir = getattr(pytest_module, "result_dir", None)

    # Mock pytest without result_dir
    pytest_module.products = []
    pytest_module.result_dir = None

    try:
        # Should not raise exception when result_dir is None
        # (tests line 119 check)
        plugin.pytest_sessionfinish()
    finally:
        # Restore original values
        if old_products is not None:
            pytest_module.products = old_products
        else:
            del pytest_module.products  # pragma: no cover
        if old_result_dir is not None:
            pytest_module.result_dir = old_result_dir
        else:
            del pytest_module.result_dir  # pragma: no cover


def test_pytest_sessionfinish_empty_products():
    """Test pytest_sessionfinish with empty products list."""
    import pytest as pytest_module

    plugin = RunnerPlugin(False)

    # Save original values
    old_products = getattr(pytest_module, "products", None)
    old_result_dir = getattr(pytest_module, "result_dir", None)

    # Mock pytest with empty products list
    pytest_module.products = []
    pytest_module.result_dir = "/tmp/test"

    try:
        # Should not raise exception with empty products
        # (covers line 106->120: for loop with empty list)
        plugin.pytest_sessionfinish()
    finally:
        # Restore original values
        if old_products is not None:
            pytest_module.products = old_products
        else:
            del pytest_module.products  # pragma: no cover
        if old_result_dir is not None:
            pytest_module.result_dir = old_result_dir
        else:
            del pytest_module.result_dir  # pragma: no cover
