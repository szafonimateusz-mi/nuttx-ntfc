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

"""Parallel execution utilities for handlers."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, TypeVar

from ntfc.log.logger import logger

T = TypeVar("T")


def run_parallel(
    items: List[T],
    attr_name: str,
    *args: Any,
    **kwargs: Any,
) -> List[Any]:
    """Run a method/property on all items in parallel.

    Supports both methods (with args) and properties (no args).

    :param items: List of objects to execute on
    :param attr_name: Name of method or property to call
    :param args: Positional arguments to pass to the method
    :param kwargs: Keyword arguments to pass to the method
    :return: List of results in original order
    """

    def worker(index_item: tuple[int, T]) -> tuple[int, Any]:
        """Call method/property on item and return indexed result.

        :param index_item: Tuple of (index, item)
        :return: Tuple of (index, result) for ordering preservation
        """
        index, item = index_item
        try:
            attr = getattr(item, attr_name)
            # Handle both properties and methods
            if callable(attr):
                result = attr(*args, **kwargs)
            else:
                result = attr
            return (index, result)
        except Exception as e:  # pragma: no cover
            logger.error(
                f"Exception in parallel call to {attr_name} "
                f"for item {item}: {e}"
            )
            return (index, None)

    # Execute all workers in parallel
    with ThreadPoolExecutor(max_workers=len(items)) as executor:
        indexed_items = list(enumerate(items))
        futures = [executor.submit(worker, item) for item in indexed_items]

        # Collect results in original order
        results: List[Any] = [None] * len(items)
        for future in futures:
            index, result = future.result()
            results[index] = result

    return results
