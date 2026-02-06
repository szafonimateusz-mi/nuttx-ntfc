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
import yaml

from ntfc.envconfig import EnvConfig


def test_envconfig_common():

    conf = None
    with open("./tests/resources/nuttx/sim/config.yaml", "r") as f:
        conf = yaml.safe_load(f)

    env = EnvConfig(conf)

    # check device options
    assert env.common["cwd"] == "./"


def test_envconfig_product():

    with pytest.raises(TypeError):
        _ = EnvConfig(["1", "2"])

    conf = None
    with open("./tests/resources/nuttx/sim/config.yaml", "r") as f:
        conf = yaml.safe_load(f)

    env = EnvConfig(conf)

    assert env.core()["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    assert env.core()["elf_path"] == "./tests/resources/nuttx/sim/nuttx"

    assert (
        env.core(cpu=0)["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    )
    assert (
        env.core(cpu=1)["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    )

    with pytest.raises(KeyError):
        _ = env.core(cpu=2)["conf_path"]

    assert env.core(cpu=0)["elf_path"] == "./tests/resources/nuttx/sim/nuttx"
    assert env.core(cpu=1)["elf_path"] == "./tests/resources/nuttx/sim/nuttx"

    with pytest.raises(KeyError):
        _ = env.core(cpu=2)["elf_path"]

    assert env.core(cpu=0)["name"] == "main"
    assert env.core(cpu=1)["name"] == "core1"

    with pytest.raises(KeyError):
        _ = env.core(cpu=2)["name"]

    assert env.core(cpu=0)["device"] == "sim"
    assert env.core(cpu=1)["device"] == "sim"

    assert env.core(product=1)["name"] == "product1-main"
    assert env.core(product=1, cpu=0)["name"] == "product1-main"
    assert env.core(product=1, cpu=1)["name"] == "product1-core1"
    assert env.core(product=1, cpu=2) == {}
    assert env.core(product=1, cpu=3) == {}

    assert env.core(product=2)["name"] == "product2-main"
    assert env.core(product=2, cpu=0)["name"] == "product2-main"
    assert env.core(product=2, cpu=2) == {}
    assert env.core(product=2, cpu=3) == {}

    assert env.core(product=3, cpu=0) == {}
    assert env.core(product=3, cpu=1) == {}
    assert env.core(product=3, cpu=2) == {}
    assert env.core(product=3, cpu=3) == {}

    assert env.core(product=4, cpu=0) == {}
    assert env.core(product=4, cpu=1) == {}
    assert env.core(product=4, cpu=2) == {}
    assert env.core(product=4, cpu=3) == {}

    assert env.config is not None
    assert env.config["config"] is not None
    assert env.config["product"] is not None

    # check kconfig options
    assert env.kv_check("dummy") is False
    assert env.kv_check("CONFIG_ALLOW_BSD_COMPONENTS") is False
    assert env.kv_check("CONFIG_DEFAULT_SMALL") is False
    assert env.kv_check("CONFIG_HOST_LINUX") is True
    assert env.kv_check("CONFIG_APPS_DIR") == "../apps"
    assert env.kv_check("CONFIG_BASE_DEFCONFIG") == "sim/nsh"
    assert env.kv_check("CONFIG_BUILD_FLAT") is True

    # check available commands in elf
    assert env.cmd_check("dummy") is False
    assert env.cmd_check("dummy_main") is False
    assert env.cmd_check("dummy2_main") is False
    assert env.cmd_check("hello") is False
    assert env.cmd_check("hello_main") is True
    assert env.cmd_check("ostest") is False
    assert env.cmd_check("ostest_main") is True

    # get product
    assert env.product_get(0) is not None
    assert env.product_get(1) is not None
    assert env.product_get(2) is not None
    assert env.product_get(4) is None


def test_envconfig_extra_check(envconfig_dummy):
    """Test extra_check method for run_in_core option."""

    # Test with run_in_core in extra options
    assert envconfig_dummy.extra_check("run_in_core=cpu1") is True

    # Test without run_in_core
    assert envconfig_dummy.extra_check("some_other_option") is False

    # Test with empty string
    assert envconfig_dummy.extra_check("") is False
