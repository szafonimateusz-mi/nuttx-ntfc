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

from ntfc.coreconfig import CoreConfig


def test_product_core_config():
    conf = {
        "name": "dummy",
        "device": "sim",
        "elf_path": "./tests/resources/nuttx/sim/nuttx",
        "conf_path": "./tests/resources/nuttx/sim/kv_config",
        "uptime": 1,
    }

    p = CoreConfig(conf)

    assert p.kv_check("aaa") is False
    assert p.kv_check("CONFIG_SYSTEM_NSH") is True

    assert p.cmd_check("aaa") is False
    assert p.cmd_check("hello_main") is True

    conf = {
        "name": "product",
    }

    p = CoreConfig(conf)

    with pytest.raises(AttributeError):
        p.cmd_check("aaa")

    # New behavior: kv_check returns False when no config data
    # instead of raising an exception
    assert p.kv_check("aaa") is False


def test_core_config_prompt():
    """Test CoreConfig prompt property."""
    # Test with explicit prompt in YAML config
    conf = {
        "name": "test",
        "device": "sim",
        "prompt": "custom_prompt>",
    }

    p = CoreConfig(conf)
    assert p.prompt == "custom_prompt>"

    # Test without explicit prompt, loads from config file
    conf = {
        "name": "test",
        "device": "sim",
        "conf_path": "./tests/resources/nuttx/sim/kv_config",
    }

    p = CoreConfig(conf)
    # Should load from kv_config file or return None
    assert p.prompt == "nsh> "
