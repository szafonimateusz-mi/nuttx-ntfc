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

"""OS abstraction."""

from abc import ABC, abstractmethod
from typing import List

###############################################################################
# Class: OSCommon
###############################################################################


class OSCommon(ABC):
    """OS abstraction common."""

    @property
    @abstractmethod
    def prompt(self) -> bytes:
        """Get prompt."""

    @property
    @abstractmethod
    def no_cmd(self) -> str:
        """Get command not found string."""

    @property
    @abstractmethod
    def help_cmd(self) -> bytes:
        """Get help command."""

    @property
    @abstractmethod
    def poweroff_cmd(self) -> bytes:
        """Get poweroff command."""

    @property
    @abstractmethod
    def reboot_cmd(self) -> bytes:
        """Get reboot command."""

    @property
    @abstractmethod
    def uname_cmd(self) -> bytes:
        """Get uname command."""

    @property
    @abstractmethod
    def crash_keys(self) -> List[bytes]:
        """Get keys related to OS crash."""
