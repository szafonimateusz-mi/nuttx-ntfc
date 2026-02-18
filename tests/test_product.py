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

from unittest.mock import MagicMock

import pytest

from ntfc.product import Product


def test_product_init_inval(envconfig_dummy):

    with pytest.raises(TypeError):
        _ = Product(None)

    with pytest.raises(TypeError):
        _ = Product(1)


def test_product_properties(envconfig_dummy):

    p = Product(envconfig_dummy.product[0])
    assert p.__str__() == "Product: product-dummy"
    assert p.name == "product-dummy"

    def dummy_reboot(timeout):
        return True

    p._cores.core(0)._device.reboot = dummy_reboot
    p._cores.core(0)._cur_core = "test"

    assert p.sendCommand("test")
    assert p.sendCommandReadUntilPattern("test")
    assert p.sendCtrlCmd("C") is None
    assert p.reboot()
    p._cores.force_panic = MagicMock(return_value=True)
    assert p.force_panic() is True
    p._cores.force_panic.assert_called_with(30)
    assert p.cur_core == "test"
    assert p.core(0) is not None
