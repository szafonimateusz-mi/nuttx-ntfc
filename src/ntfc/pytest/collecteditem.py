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

"""Collected test item."""

###############################################################################
# Class: CollectedItem
###############################################################################


class CollectedItem:
    """Collected test item."""

    def __init__(
        self,
        directory: str,
        module: str,
        name: str,
        path: str,
        line: int,
        nodeid: str,
        modname: str,
        root: str,
    ) -> None:
        """Initialzie collection item."""
        self._directory = directory
        self._module = module
        self._name = name
        self._path = path
        self._line = line
        self._nodeid = nodeid
        self._nodeid_abs = self._path + "::" + self._nodeid.split("::")[1]

        tmp = "_".join(part.capitalize() for part in root.split("/")[:-1])
        if tmp and tmp[0] != "_":
            tmp = "_" + tmp

        self._module2 = modname + tmp

    def __str__(self) -> str:
        """Get collected item string representation."""
        _str = "CollectedItem: " + self.name
        return _str

    @property
    def module2(self) -> str:
        """Get collected module name (short version)."""
        return self._module2

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

    @property
    def nodeid_abs(self) -> str:
        """Get collected item node ID with absolute path."""
        return self._nodeid_abs
