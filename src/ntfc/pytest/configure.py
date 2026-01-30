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

"""NTFC plugin configuration for pytest."""

import time
from typing import TYPE_CHECKING, Any

import pytest

from ntfc.logger import logger

if TYPE_CHECKING:
    from ntfc.envconfig import EnvConfig


###############################################################################
# Class: PytestConfigPlugin
###############################################################################


class PytestConfigPlugin:
    """Everything you would have put in pytest.ini and conftest.py."""

    def __init__(self, config: "EnvConfig", verbose: bool = False) -> None:
        """Initialize custom pytest plugin.

        :param config: configuration instance
        """
        self._config = config
        self._verbose = verbose

    def _device_reboot(self) -> None:
        """Reboot the device if crashed."""
        pytest.product.reboot()  # pragma: no cover

    def _generate_coredump_file(self, reason: Any) -> None:
        """Generate coredump file.

        :param reason:
        """
        # not supported yet

    def pytest_configure(self, config: pytest.Config) -> None:
        """Everything you would have put in pytest.ini.

        :param config: pytest config
        """
        # logging config
        config.option.log_cli = True

        if self._verbose:
            config.option.log_cli_level = "INFO"
        else:
            config.option.log_cli_level = "ERROR"

        config.option.log_file = "pytest.debug.log"
        config.option.log_file_level = "DEBUG"
        config.option.log_file_date_format = "%Y-%m-%d %H:%M:%S"

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

    def pytest_runtest_makereport(  # noqa: C901
        self, item: pytest.Item, call: pytest.CallInfo[None]
    ) -> Any:
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
        flood_flag = False
        debug_time = 0

        logger.debug(
            f"pytest_runtest_makereport: {report.outcome}"
            f" loop {pytest.product.busyloop}  "
            f" crash {pytest.product.crash}"
            f" flood {pytest.product.flood}"
            f" notalive {pytest.product.notalive}"
        )

        # Check for crashes in any phase
        if (
            pytest.product.busyloop
            or pytest.product.flood
            or pytest.product.crash
            or pytest.product.notalive
        ):
            if call.when in ("setup", "call") or (  # pragma: no cover
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
                elif pytest.product.flood:
                    reason = "flood"
                    report.longrepr = (
                        f'"Device flood" detected, during: {call.when}'
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

        if (
            report.outcome == "failed"
            and not busyloop_crash_flag
            and not flood_flag
        ):
            need_coredump = True
            reason = "failed"
            need_reboot = False

        # Notify users if test failed
        if (
            need_notify and hasattr(pytest, "notify") and pytest.result_dir
        ):  # pragma: no cover
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

        if debug_time:  # pragma: no cover
            logger.info(f"Waiting {debug_time}s ...")
            time.sleep(debug_time)

        if need_reboot:  # pragma: no cover
            logger.info(f"Reboot device, reason: {report.longrepr}")
            self._device_reboot()
