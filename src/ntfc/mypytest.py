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

"""NTFC plugin for pytest."""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import pytest
from pluggy import HookimplMarker

from ntfc.device.getdev import get_device
from ntfc.logger import logger
from ntfc.product import Product
from ntfc.testfilter import FilterTest

if TYPE_CHECKING:
    from config import EnvConfig
    from ntfc.device.common import DeviceCommon

# required for plugin
hookimpl = HookimplMarker("pytest")

###############################################################################
# Class: _PytestConfigPlugin
###############################################################################


class _PytestConfigPlugin:
    """Everything you would have put in pytest.ini and conftest.py."""

    def __init__(self, config: "EnvConfig") -> None:
        """Initialize custom pytest plugin.

        :param config: configuration instance
        """
        self._config = config

        self._filter = FilterTest(config)

        self._skipped_items = []

    def _device_reboot(self) -> None:
        """Reboot the device if crashed."""
        pytest.product.reboot()

    def _generate_coredump_file(self, reason) -> None:
        """Generate coredump file.

        :param reason:
        """
        # not supported yet

    def pytest_configure(self, config) -> None:
        """Everything you would have put in pytest.ini.

        :param config: pytest config
        """
        # logging config
        config.option.log_cli = True
        config.option.log_cli_level = "INFO"

        config.option.log_file = "pytest.debug.log"
        config.option.log_file_level = "DEBUG"
        config.option.log_file_date_format = "%Y-%m-%d %H:%M:%S"

        # timeout config
        config.option.timeout = 90000
        config.option.timeout_method = "thread"

        # custom markers (equivalent of markers= section)
        markers = [
            "monkey: Mark test to use the monkey plugin",
            "stability: Tests for stability verification",
            "performance: Tests for performance evaluation",
            "cmd_check: Check if specified commands are enabled",
            "dep_config: Check if macros are enabled in .config file",
            "extra_opts: Additional parameters for testing",
            "config_value_check: Validate complex configuration strings",
        ]

        for m in markers:
            config.addinivalue_line("markers", m)

    @property
    def skipped_items(self) -> list:
        """Get skipped items."""
        return self._skipped_items

    def pytest_collection_modifyitems(self, config, items) -> None:
        """Modify the `items` list after collection is completed.

        :param config:
        :param items:
        """
        collected_items = []

        for item in items:

            skip, reason = self._filter.check_test_support(item)

            if skip:
                self._skipped_items.append((item, reason))
                item.add_marker(pytest.mark.skip(reason=reason))
                continue

            # include the test if not skipped
            collected_items.append(item)

        # Update the items list to only include filtered items
        items[:] = collected_items

    def pytest_runtest_makereport(self, item, call) -> None:  # noqa: C901
        """Create a TestReport for each of the runtest phases.

        :param item:
        :param call: the CallInfo for the phase
        """
        outcome = yield
        report = outcome.get_result()
        need_reboot = False
        need_coredump = False
        need_notify = False
        reason = "failed"
        busyloop_crash_flag = False
        debug_time = 0

        logger.debug(
            f"pytest_runtest_makereport: {report.outcome}"
            f" loop {pytest.product.busyloop}  "
            f" crash {pytest.product.crash}"
            f" notalive {pytest.product.notalive}"
        )

        # Check for crashes in any phase
        if (
            pytest.product.busyloop
            or pytest.product.crash
            or pytest.product.crash
            or pytest.product.notalive
        ):
            if call.when in ("setup", "call") or (
                call.when == "teardown"
                and not hasattr(item, "_setup_call_failed")
            ):
                logger.debug(f"pytest_runtest_makereport: {call.when}")

                # Mark the report as failed due to crash
                report.outcome = "failed"

                if pytest.product.crash:
                    reason = "crash"
                    report.longrepr = (
                        f'"Device crashed" detected, during: {call.when}'
                    )
                elif pytest.product.busyloop:
                    reason = "busy_loop"
                    report.longrepr = (
                        f'"Device busy_loop" detected, during: {call.when}'
                    )
                else:
                    reason = "not_alive"
                    report.longrepr = (
                        f'"Device not alive" detected, during: {call.when}'
                    )

                # For setup phase, we need to prevent the test from running
                if call.when in ("setup", "call"):
                    item._setup_call_failed = True

                need_coredump = True
                need_reboot = True
                need_notify = True
                busyloop_crash_flag = True

        if report.outcome == "failed" and not busyloop_crash_flag:
            need_coredump = True
            reason = "failed"
            need_reboot = False

        # Notify users if test failed
        if (
            need_notify
            and hasattr(pytest, "notify")
            and hasattr(pytest, "result_dir")
        ):
            logger.info(
                f"Test {reason}, notifying developers for"
                f" on-site debugging ..."
            )
            pytest.notify.trigger_notify_with_more_info(pytest.result_dir)

            if report.outcome == "failed" and busyloop_crash_flag:
                debug_time = (
                    pytest.debug_time
                    if hasattr(pytest, "debug_time")
                    else 1800
                )
            elif report.outcome == "failed" and not busyloop_crash_flag:
                debug_time = 0

        if need_coredump:
            # Handle core dump generation if needed
            self._generate_coredump_file(reason)

        if debug_time:
            logger.info(f"Waiting {debug_time}s ...")
            time.sleep(debug_time)

        if need_reboot:
            logger.info(f"Reboot device, reason: {report.longrepr}")
            self._device_reboot()


###############################################################################
# Class: _RunnerPlugin
###############################################################################


class _RunnerPlugin:
    def __init__(self, nologs: bool = False) -> None:
        """Initialize custom pytest test runner plugin."""
        self._logs = {}
        self._nologs = nologs

    def _collect_device_logs_teardown(self) -> None:
        """Teardown for device log."""
        # stop device log collector
        if self._nologs:
            return

        pytest.product.device.stop_log_collect()

        # close files
        self._logs["console"].close()

    def _collect_device_logs(self, request) -> None:
        """Initiate device log writing into a new test file."""
        if self._nologs:
            return

        testname = request.node.name

        # open log files
        tmp = os.path.join(pytest.result_dir, testname + ".console.txt")
        self._logs["console"] = open(tmp, "a")

        # start device log collector
        pytest.product.device.start_log_collect(self._logs)

    @pytest.fixture(scope="function", autouse=True)
    def prepare_test(self, request) -> None:
        """Prepare test case."""
        # initialize log collector
        self._collect_device_logs(request)
        # register log collector teardown
        request.addfinalizer(self._collect_device_logs_teardown)

    @pytest.fixture
    def switch_to_core(self) -> None:
        pass

    @pytest.fixture
    def core(self) -> None:
        pass


###############################################################################
# Class: _CollectorPlugin
###############################################################################


class _CollectorPlugin:
    def __init__(self) -> None:
        """Initialize custom pytest collector plugin."""
        self.collected_items = []
        self.skipped_items = []
        self.parsed_items = []

    @property
    def collected(self) -> list:
        """Get collected items."""
        return self.collected_items

    @property
    def skipped(self) -> list:
        """Get skipped items."""
        return self.skipped_items

    @property
    def parsed(self) -> list:
        """Get collected items in parsed format."""
        return self.parsed_items

    def pytest_runtestloop(self, session) -> bool:
        """Prevent tests from running.

        Returning True stops test execution.
        """
        return True

    def pytest_collection_finish(self, session) -> None:
        """Pytest collection finish callback."""
        self.collected_items.extend(session.items)

        # extract useful data from items
        for item in session.items:
            path, lineno, name = item.location
            abs_path = os.path.abspath(path)
            directory = os.path.dirname(abs_path)
            module = os.path.splitext(os.path.basename(path))[0]

            ci = _CollectedItem(
                directory, module, name, abs_path, lineno, item.nodeid
            )
            self.parsed_items.append(ci)


###############################################################################
# Class: _CollectedItem
###############################################################################


class _CollectedItem:
    def __init__(
        self,
        directory: str,
        module: str,
        name: str,
        path: str,
        line: int,
        nodeid: str,
    ) -> None:
        """Initialzie collection item."""
        self._directory = directory
        self._module = module
        self._name = name
        self._path = path
        self._line = line
        self._nodeid = nodeid

    def __str__(self) -> str:
        """Get collected item string representation."""
        _str = "CollectedItem: " + self.nodeid
        return _str

    @property
    def directory(self) -> str:
        """Get collected item directory."""
        return self._directory

    @property
    def module(self) -> str:
        """Get collected item module."""
        return self._module

    @property
    def name(self) -> str:
        """Get collected item name."""
        return self._name

    @property
    def path(self) -> str:
        """Get collected item file."""
        return self._path

    @property
    def line(self) -> int:
        """Get collected item line."""
        return self._line

    @property
    def nodeid(self) -> str:
        """Get collected item node ID."""
        return self._nodeid


###############################################################################
# Class: MyPytest
###############################################################################


class MyPytest:
    """Custom wrapper for pytest."""

    def __init__(
        self,
        config: "EnvConfig",
        ignorepath: str = None,
        exit_on_fail: bool = False,
        verbose: bool = False,
        device: Optional[List["DeviceCommon"]] = None,
    ) -> None:
        """Initialize pytest wrapper.

        :param config: configuration instance
        :param exit_on_fail: exit on first test fail if set to True
        :param verbose: verbose output if set to True
        """
        self._config = config
        self._opt = []
        self._plugins = []

        if exit_on_fail:
            self._opt.append("-x")

        if verbose:
            self._opt.append("-qq")

        # ignore tests
        self.ignore_tests(ignorepath)

        # configure plugin
        hookimpl_marker = hookimpl(hookwrapper=True)
        hookimpl_marker(
            _PytestConfigPlugin.__dict__["pytest_runtest_makereport"]
        )
        self._ptconfig = _PytestConfigPlugin(config)

        # add our custom pytest plugin
        self._plugins.append(self._ptconfig)

        # inject some objects into pytest module
        pytest.products = self._create_products(config, device)
        pytest.product = self._get_product(product=0)
        pytest.task = config.product_get(product=0)

    def _create_products(
        self, config: "EnvConfig", device: "DeviceCommon"
    ) -> list:
        """Create products according to configuration."""
        tmp = []
        for i in range(len(config.product)):
            if not device or not device[i]:
                dev = get_device(config.product[i])
            else:
                dev = device[i]

            p = Product(dev, config.product[i])
            tmp.append(p)

        return tmp

    def _get_product(self, product: int = 0) -> dict:
        """Get product configuration."""
        return pytest.products[product]

    def _run(self, extra_opt: list, extra_plugins: list) -> int:
        """Run pytest.

        :param extra_opt:
        :param extra_plugins:
        """
        # get default options and plugins
        opt = self._opt[:]
        plugins = self._plugins[:]

        # extra options and plugins
        opt.extend(extra_opt)
        plugins.extend(extra_plugins)

        # override tox.ini configuration from package root
        opt.extend(["--override-ini", "addopts="])

        # run pytest in collection-only mode with our custom plugin
        return pytest.main(opt, plugins=plugins)

    def _device_start(self) -> None:
        """Start device to test."""
        pytest.product.device.start()

        # finish product initialization
        pytest.product.init()

    def ignore_tests(self, path: str) -> None:
        """Ignore tests specified in $CWD/ignore.txt file."""
        try:
            logger.info(f"ignore file {path}")
            path = Path(path)

            with open(path) as f:
                for line in f:
                    if line[0] == "-" and line[1] == "-":
                        self._opt.append(line[:-1])
        except TypeError:
            pass

        except FileNotFoundError:
            logger.info("no ignore file")
            pass

    def runner(self, testpath: str, result: dir, nologs: bool = False) -> int:
        """Run tests.

        :param testpath: path to test directory
        :param result: result output configuration
        """
        opt = [testpath]

        if not nologs:
            # create result directory
            result_dir = result.get("resdir", "./result")
            time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            pytest.result_dir = os.path.join(result_dir, time_now)
            os.makedirs(pytest.result_dir, exist_ok=True)

            # additional reports
            if result.get("html"):
                path = os.path.join(pytest.result_dir, "report.html")
                opt.append(f"--html={path}")
            if result.get("xml"):
                path = os.path.join(pytest.result_dir, "report.xml")
                opt.append(f"--junitxml={path}")
            if result.get("json"):
                path = os.path.join(pytest.result_dir, "report.json")
                opt.append(f"--json={path}")

        # run pytest with our custom test plugin
        runner = _RunnerPlugin(nologs)

        # start device before test start
        self._device_start()

        return self._run(opt, [runner])

    def collect(self, testpath) -> list:
        """Collect tests.

        :param testpath:
        """
        collector = _CollectorPlugin()

        # run pytest with our custom collector plugin
        self._run([testpath], [collector])

        # return parsed items and skipped
        return collector.parsed, self._ptconfig.skipped_items
