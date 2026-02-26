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

import pytest

from ntfc.debug.config import CoredumpConfig, DebugConfig, GdbConfig


class TestCoredumpConfig:
    def test_defaults(self):
        cfg = CoredumpConfig({})
        assert cfg.enable is False
        assert cfg.collection_type == "auto"
        assert cfg.limit == 5

    def test_full_config(self):
        cfg = CoredumpConfig({"enable": True, "type": "gdb", "limit": 10})
        assert cfg.enable is True
        assert cfg.collection_type == "gdb"
        assert cfg.limit == 10

    def test_all_valid_types(self):
        for t in ("auto", "gdb", "fastboot", "ymodem"):
            cfg = CoredumpConfig({"type": t})
            assert cfg.collection_type == t

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid coredump type"):
            CoredumpConfig({"type": "invalid"})

    def test_enable_false(self):
        cfg = CoredumpConfig({"enable": False})
        assert cfg.enable is False

    def test_limit_zero(self):
        cfg = CoredumpConfig({"limit": 0})
        assert cfg.limit == 0


class TestGdbConfig:
    def test_defaults(self):
        cfg = GdbConfig({})
        assert cfg.enable is False
        assert cfg.force_panic is False

    def test_full_config(self):
        cfg = GdbConfig({"enable": True, "force_panic": True})
        assert cfg.enable is True
        assert cfg.force_panic is True

    def test_enable_only(self):
        cfg = GdbConfig({"enable": True})
        assert cfg.enable is True
        assert cfg.force_panic is False

    def test_force_panic_only(self):
        cfg = GdbConfig({"force_panic": True})
        assert cfg.enable is False
        assert cfg.force_panic is True


class TestDebugConfig:
    def test_defaults_empty(self):
        cfg = DebugConfig({})
        assert cfg.coredump.enable is False
        assert cfg.coredump.collection_type == "auto"
        assert cfg.coredump.limit == 5
        assert cfg.gdb.enable is False
        assert cfg.gdb.force_panic is False

    def test_full_config(self):
        cfg = DebugConfig(
            {
                "coredump": {
                    "enable": True,
                    "type": "fastboot",
                    "limit": 3,
                },
                "gdb": {
                    "enable": True,
                    "force_panic": True,
                },
            }
        )
        assert cfg.coredump.enable is True
        assert cfg.coredump.collection_type == "fastboot"
        assert cfg.coredump.limit == 3
        assert cfg.gdb.enable is True
        assert cfg.gdb.force_panic is True

    def test_coredump_only(self):
        cfg = DebugConfig({"coredump": {"enable": True}})
        assert cfg.coredump.enable is True
        assert cfg.gdb.enable is False

    def test_gdb_only(self):
        cfg = DebugConfig({"gdb": {"enable": True}})
        assert cfg.coredump.enable is False
        assert cfg.gdb.enable is True

    def test_invalid_coredump_type_propagates(self):
        with pytest.raises(ValueError, match="Invalid coredump type"):
            DebugConfig({"coredump": {"type": "unknown"}})
