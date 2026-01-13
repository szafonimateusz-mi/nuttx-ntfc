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

"""NTFC collector plugin for pytest."""

import os
from typing import TYPE_CHECKING, List, Tuple

import pytest

from ntfc.pytest.collecteditem import CollectedItem
from ntfc.testfilter import FilterTest

if TYPE_CHECKING:
    from ntfc.envconfig import EnvConfig

###############################################################################
# Class: CollectorPlugin
###############################################################################


class CollectorPlugin:
    """Custom Pytest collector plugin."""

    def __init__(self, config: "EnvConfig", collectonly: bool = True) -> None:
        """Initialize custom pytest collector plugin."""
        self._config = config
        self._filter = FilterTest(config)

        self._all_items: List[CollectedItem] = []
        self._filtered_items: List[CollectedItem] = []
        self._collectonly = collectonly

        self._skipped_items: List[Tuple[pytest.Item, str]] = []

    def _collected_item(self, item: pytest.Item) -> CollectedItem:
        """Create collected item."""
        path, lineno, name = item.location
        lineno = lineno or 0
        abs_path = os.path.abspath(item.path)
        directory = os.path.dirname(abs_path)
        module = abs_path.replace(pytest.testroot, "")
        root = module.replace(pytest.testroot, "")

        ci = CollectedItem(
            directory,
            module,
            name,
            abs_path,
            lineno,
            item.nodeid,
            pytest.ntfcyaml.get("module", "Unknown_"),
            root,
        )

        return ci

    @property
    def skipped_items(self) -> List[Tuple[pytest.Item, str]]:
        """Get skipped items."""
        return self._skipped_items

    @property
    def filtered(self) -> List[CollectedItem]:
        """Get filtered items."""
        return self._filtered_items

    @property
    def allitems(self) -> List[CollectedItem]:
        """Get all items before filtration."""
        return self._all_items

    def pytest_runtestloop(self, session: pytest.Session) -> bool:
        """Run test loop.

        Do not run tests if we are in collect only mode.
        """
        if session.testsfailed:  # pragma: no cover
            raise session.Interrupted("error during collection")

        # do not run test cases when in collect only mode
        if self._collectonly:
            return True

        loops = self._config.common.get("loops", 1)
        for _ in range(loops):
            if loops > 1:
                print("\n\n" + "=" * 100)
                print("Loop:", _)
                print("=" * 100)

            for i, item in enumerate(session.items):
                nextitem = (
                    session.items[i + 1]
                    if i + 1 < len(session.items)
                    else None
                )
                item.config.hook.pytest_runtest_protocol(
                    item=item, nextitem=nextitem
                )
                if session.shouldfail:  # pragma: no cover
                    raise session.Failed(session.shouldfail)
                if session.shouldstop:  # pragma: no cover
                    raise session.Interrupted(session.shouldstop)

        return True

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        """Pytest collection finish callback."""

    def pytest_collection_modifyitems(
        self,
        config: pytest.Config,
        items: list[pytest.Item],  # pylint: disable=unused-argument
    ) -> None:
        """Modify the `items` list after collection is completed.

        :param config:
        :param items:
        """
        tmp: List[pytest.Item] = []

        module = pytest.cfgtest.get("module", {})
        include_module = module.get("include_module", [])
        exclude_module = module.get("exclude_module", [])
        # order_module = module.get("order", [])

        for item in items:

            # get collected data and attach to item
            ci = self._collected_item(item)
            item._collected = ci
            # add to all items
            self._all_items.append(ci)

            skip, reason = self._filter.check_test_support(item)

            if skip:
                skip_reason: str = reason or "unknown reason"
                self._skipped_items.append((item, skip_reason))
                item.add_marker(pytest.mark.skip(reason=skip_reason))
                continue

            # check if we match to include_module
            if include_module:
                if ci.module2 not in include_module:
                    reason = "not in include_module"
                    self._skipped_items.append((item, reason))
                    item.add_marker(pytest.mark.skip(reason=reason))
                    continue

            # excluded modules
            if ci.module2 in exclude_module:
                reason = "excluded module"
                self._skipped_items.append((item, reason))
                item.add_marker(pytest.mark.skip(reason=reason))
                continue

            # include the test if not skipped
            self._filtered_items.append(ci)
            tmp.append(item)

        # TODO: force modules order

        # overwrite items
        items[:] = tmp
