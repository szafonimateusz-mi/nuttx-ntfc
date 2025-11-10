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

import os
import pty
import select
import threading

import pytest
import serial

from ntfc.device.serial import DeviceSerial
from ntfc.envconfig import ProductConfig


@pytest.fixture
def serial_pair():
    fd1, fd2 = pty.openpty()
    fd2_name = os.ttyname(fd2)
    return fd1, fd2_name


g_fake_device_retval = b""


def fake_device_thread(fd, stop):
    # read garbage
    # data = os.read(fd, 100)

    while not stop.is_set():
        try:
            rlist, _, _ = select.select([fd], [], [], 0.2)
            if rlist:
                data = os.read(fd, 100)
                if data:
                    os.write(fd, g_fake_device_retval)
        except OSError:
            break


@pytest.fixture
def serial_config():
    config = {
        "cores": {
            "main_core": {
                "name": "main",
                "device": "serial",
                "exec_path": "",
                "exec_args": "",
                "conf_path": "",
                "elf_path": "",
            }
        }
    }

    return ProductConfig(config)


def test_device_sim_init(serial_config, serial_pair):

    ser = DeviceSerial(serial_config)

    # no path and args
    with pytest.raises(serial.serialutil.SerialException):
        serial_config.core()["exec_path"] = ""
        serial_config.core()["exec_args"] = ""
        ser.start()

    # no boot
    with pytest.raises(TimeoutError):
        serial_config.core()["exec_path"] = serial_pair[1]
        serial_config.core()["exec_args"] = ""
        ser.start()

    stop = threading.Event()
    device_thread = threading.Thread(
        target=fake_device_thread, args=(serial_pair[0], stop)
    )
    device_thread.start()

    global g_fake_device_retval
    g_fake_device_retval = b"\n\rnsh>"
    ser.start()

    stop.set()
    device_thread.join(timeout=1)
