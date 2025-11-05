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

"""Get device from a given name."""

from typing import TYPE_CHECKING

from .qemu import DeviceQemu
from .sim import DeviceSim

if TYPE_CHECKING:
    from .common import DeviceCommon
    from .envconfig import ProductConfig

###############################################################################
# Function: get_device
###############################################################################


def get_device(conf: "ProductConfig", cpu: int = 0) -> "DeviceCommon":
    """Get device from a given name."""
    devname = conf.core(cpu).get("device", None)

    if not devname:
        raise ValueError("Unspecified device")

    if devname == "sim":
        device = DeviceSim(conf)
    elif devname == "qemu":
        device = DeviceQemu(conf)
    else:
        raise ValueError("unsupported device")

    return device
