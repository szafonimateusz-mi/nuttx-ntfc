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

"""NTFC runner plugin for pytest."""

import os
from typing import Any, Dict

import pytest

from ntfc.log.handler import LogHandler
from ntfc.log.logger import logger
from ntfc.log.report import Reporter

###############################################################################
# Class: RunnerPlugin
###############################################################################


class RunnerPlugin:
    """Pytest runner plugin that is called we we run test command."""

    def __init__(self, nologs: bool = False) -> None:
        """Initialize custom pytest test runner plugin."""
        self._logs: Dict[str, Dict[str, LogHandler]] = {}
        self._nologs = nologs

    def _collect_device_logs_teardown(self) -> None:
        """Teardown for device log."""
        # stop device log collector
        if self._nologs:
            return

        for product in pytest.products:
            product.stop_log_collect()

            for core in product.cores:
                self._logs[product.name][core].close()

    def _collect_device_logs(self, request: Any) -> None:
        """Initiate device log writing into a new test file."""
        if self._nologs:
            return

        testname = request.node.name

        # prepare log files
        for product in pytest.products:
            name = product.name
            product_dir = os.path.join(pytest.result_dir, name)

            for core in product.cores:
                core_dir = os.path.join(product_dir, core)

                if name not in self._logs:
                    self._logs[name] = {}

                self._logs[name][core] = LogHandler(core_dir, testname)

        # start logging for all products
        for product in pytest.products:
            name = product.name
            # start device log collector
            product.start_log_collect(self._logs[name])

    @pytest.fixture(scope="function", autouse=True)  # type: ignore
    def prepare_test(self, request: Any) -> None:
        """Prepare test case."""
        # initialize log collector
        self._collect_device_logs(request)
        # register log collector teardown
        request.addfinalizer(self._collect_device_logs_teardown)

    @pytest.fixture  # type: ignore
    def switch_to_core(self) -> None:
        """Switch to core."""

    @pytest.fixture  # type: ignore
    def core(self) -> None:
        """Get active core."""

    def pytest_sessionfinish(self) -> None:
        """Generate result summary after test session finishes.

        This hook is called after all tests have completed.
        It generates result_summary.txt and result_summary.html files.
        """
        # Disable heartbeat monitoring for all devices before shutdown
        for product in pytest.products:
            for core_idx in range(len(product.cores)):
                core = product.core(core_idx)
                # Access device through ProductCore
                device = core._device
                logger.info(
                    f"Disabling heartbeat monitoring for "
                    f"{product.name} core {core_idx}"
                )
                device._state_mgr.disable_heartbeat()

        if pytest.result_dir:
            reporter = Reporter()
            reporter.generate_result_summary(pytest.result_dir)
