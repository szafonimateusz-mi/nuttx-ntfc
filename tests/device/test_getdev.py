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

from ntfc.device.getdev import get_device


def test_getdev_get_device(config_dummy):

    config_dummy.product_get(0)["cores"]["main_core"]["device"] = ""

    with pytest.raises(ValueError):
        get_device(config_dummy.product[0])

    config_dummy.product_get(0)["cores"]["main_core"]["device"] = "dummy"

    with pytest.raises(ValueError):
        get_device(config_dummy.product[0])

    config_dummy.product_get(0)["cores"]["main_core"]["device"] = "sim"

    _ = get_device(config_dummy.product[0])

    config_dummy.product_get(0)["cores"]["main_core"]["device"] = "qemu"

    _ = get_device(config_dummy.product[0])

    config_dummy.product_get(0)["cores"]["main_core"]["device"] = "serial"

    _ = get_device(config_dummy.product[0])
