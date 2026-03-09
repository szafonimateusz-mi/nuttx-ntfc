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

"""Command status and return types."""

from dataclasses import astuple, dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import re

###############################################################################
# Class: CmdStatus
###############################################################################


class CmdStatus(IntEnum):
    """Command status."""

    SUCCESS = 0
    NOTFOUND = -1
    TIMEOUT = -2
    FAILED = -3

    def __str__(self) -> str:
        """Return enum string."""
        return self.name


###############################################################################
# Class: CmdReturn
###############################################################################


@dataclass
class CmdReturn:
    """Command return data."""

    status: CmdStatus
    rematch: "Optional[re.Match[Any]]" = None
    output: str = ""

    def valid_match(self) -> bool:
        """Check if RE match is valid."""
        return bool((self.status == CmdStatus.SUCCESS) and self.rematch)

    def __iter__(self) -> Any:
        """Make the dataclass instance iterable."""
        yield from astuple(self)
