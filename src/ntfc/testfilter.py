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

"""Test cases filter."""

from typing import List, Tuple

from ntfc.logger import logger

###############################################################################
# Class: FilterTest
###############################################################################


class FilterTest:
    """This class implements test filtration depending on the configuration."""

    def __init__(self, config) -> None:
        """Initialize test filter."""
        self._config = config

    def extract_test_requirements(self, item) -> Tuple[List, List, List]:
        """Extract test requirements from markers.

        :param item: Pytest test item object

        :return: Tuple of (command_checks, config_dependencies, extra_options)
        """
        cmd_checks = []
        dep_configs = []
        extra_opts = []

        for marker in item.iter_markers(name="cmd_check"):
            cmd_checks.extend(marker.args)

        for marker in item.iter_markers(name="dep_config"):
            dep_configs.extend(marker.args)

        for marker in item.iter_markers(name="extra_opts"):
            extra_opts.extend(marker.args)

        return cmd_checks, dep_configs, extra_opts

    def check_test_support(self, item) -> Tuple[bool, str]:
        """Check if a given test is supported.

        :param item: Pytest test item object

        :return: Tuple of (skip_test, skip_reason)
        """
        cmd, dep, extra = self.extract_test_requirements(item)

        skip = False
        reason = None

        # check Kconfig value
        for d in dep:
            if self._config.kv_check(d) is False:
                skip = True
                reason = f"Required config '{d}' not enabled"
                break

        # command available in ELF
        if skip is False:
            for c in cmd:
                if self._config.cmd_check(c) is False:
                    skip = True
                    reason = f"Required symbol '{c}' not found in ELF"
                    break

        # check extra parameters
        if skip is False:
            for e in extra:
                if self._config.extra_check(e) is False:
                    skip = True
                    reason = f"Extra parameter '{e}' not found"
                    break

        if not skip:
            logger.debug(f"OK: {cmd} {dep} {extra}")
        else:
            logger.debug(f"SKIP: {cmd} {dep} {extra}")

        return skip, reason
