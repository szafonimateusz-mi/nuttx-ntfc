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

from ntfc.envconfig import EnvConfig, ProductConfig


def test_product_config():

    conf = {
        "name": "product",
        "cores": {
            "main_core": {
                "name": "dummy",
                "device": "sim",
                "elf_path": "./tests/resources/nuttx/sim/config.yaml",
                "uptime": 1,
            },
            "core1": {
                "name": "dummy2",
                "device": "sim2",
                "elf_path": "./tests/resources/nuttx/sim/config.yaml",
                "uptime": 1,
            },
        },
    }

    p = ProductConfig(conf)

    assert p.core(0)["name"] == "dummy"
    assert p.core(0)["device"] == "sim"
    assert p.core(1)["name"] == "dummy2"
    assert p.core(1)["device"] == "sim2"


def test_envconfig_common():

    env = EnvConfig("./tests/resources/nuttx/sim/config.yaml")

    # check device options
    assert env.device["cwd"] == "./"


def test_envconfig_product():

    env = EnvConfig("./tests/resources/nuttx/sim/config.yaml")

    assert env.core()["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    assert env.core()["elf_path"] == "./tests/resources/nuttx/sim/nuttx"

    assert (
        env.core(cpu=0)["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    )
    assert (
        env.core(cpu=1)["conf_path"] == "./tests/resources/nuttx/sim/kv_config"
    )
    assert env.core(cpu=2)["conf_path"] == ""
    assert env.core(cpu=3)["conf_path"] == ""

    assert env.core(cpu=0)["elf_path"] == "./tests/resources/nuttx/sim/nuttx"
    assert env.core(cpu=1)["elf_path"] == "./tests/resources/nuttx/sim/nuttx"
    assert env.core(cpu=2)["elf_path"] == ""
    assert env.core(cpu=3)["elf_path"] == ""

    assert env.core(cpu=0)["name"] == "main"
    assert env.core(cpu=1)["name"] == "core1"
    assert env.core(cpu=2)["name"] == ""
    assert env.core(cpu=3)["name"] == ""

    assert env.core(cpu=0)["device"] == "sim"
    assert env.core(cpu=1)["device"] == "sim"
    assert env.core(cpu=2)["device"] == ""
    assert env.core(cpu=3)["device"] == ""

    assert env.core(product=1)["name"] == "product1-main"
    assert env.core(product=1, cpu=0)["name"] == "product1-main"
    assert env.core(product=1, cpu=1)["name"] == "product1-core1"
    assert env.core(product=1, cpu=2) == ""
    assert env.core(product=1, cpu=3) == ""

    assert env.core(product=2)["name"] == "product2-main"
    assert env.core(product=2, cpu=0)["name"] == "product2-main"
    assert env.core(product=2, cpu=1)["name"] == ""
    assert env.core(product=2, cpu=2) == ""
    assert env.core(product=2, cpu=3) == ""

    assert env.core(product=3, cpu=0) == ""
    assert env.core(product=3, cpu=1) == ""
    assert env.core(product=3, cpu=2) == ""
    assert env.core(product=3, cpu=3) == ""

    assert env.core(product=4, cpu=0) == ""
    assert env.core(product=4, cpu=1) == ""
    assert env.core(product=4, cpu=2) == ""
    assert env.core(product=4, cpu=3) == ""

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
