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

from unittest.mock import patch

import pytest

from ntfc.device.state import CrashType, DeviceState, DeviceStateManager


class TestCrashType:
    def test_all_crash_types_exist(self):
        types = {t.name for t in CrashType}
        assert types == {"UNKNOWN", "ASSERTION", "SEGFAULT", "PANIC"}

    def test_types_are_unique(self):
        values = [t.value for t in CrashType]
        assert len(values) == len(set(values))


class TestDeviceState:
    def test_all_states_exist(self):
        states = {s.name for s in DeviceState}
        assert states == {
            "NORMAL",
            "BUSY_LOOP",
            "CRASHED",
            "UNHEALTHY",
        }

    def test_states_are_unique(self):
        values = [s.value for s in DeviceState]
        assert len(values) == len(set(values))


class TestDeviceStateManagerInit:
    def test_starts_normal(self):
        mgr = DeviceStateManager()
        assert mgr.get_current_state() is DeviceState.NORMAL
        assert mgr.is_healthy() is True
        assert mgr.is_crashed() is False
        assert mgr.is_busy_loop() is False
        assert mgr.is_unhealthy() is False

    def test_initial_crash_type_unknown(self):
        mgr = DeviceStateManager()
        assert mgr.get_crash_type() is CrashType.UNKNOWN


class TestDeviceStateManagerTransitions:
    def test_set_crashed(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("panic")
        assert mgr.is_crashed() is True
        assert mgr.is_unhealthy() is True
        assert mgr.is_healthy() is False

    def test_set_busy_loop(self):
        mgr = DeviceStateManager()
        mgr.set_busy_loop("no output")
        assert mgr.is_busy_loop() is True
        assert mgr.is_unhealthy() is True

    def test_set_unhealthy(self):
        mgr = DeviceStateManager()
        mgr.set_unhealthy("flood")
        assert mgr.is_unhealthy() is True
        assert mgr.is_crashed() is False
        assert mgr.is_busy_loop() is False

    def test_set_normal(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("x")
        mgr.set_normal("recovered")
        assert mgr.is_healthy() is True
        assert mgr.is_unhealthy() is False

    def test_set_crashed_with_crash_type(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("oops", crash_type=CrashType.ASSERTION)
        assert mgr.get_crash_type() is CrashType.ASSERTION

    def test_set_crashed_segfault_type(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("seg", crash_type=CrashType.SEGFAULT)
        assert mgr.get_crash_type() is CrashType.SEGFAULT

    def test_set_crashed_panic_type(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("panic", crash_type=CrashType.PANIC)
        assert mgr.get_crash_type() is CrashType.PANIC

    def test_set_crashed_default_crash_type_unknown(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("x")
        assert mgr.get_crash_type() is CrashType.UNKNOWN

    def test_reset_all_states(self):
        mgr = DeviceStateManager()
        mgr.set_crashed("x", crash_type=CrashType.PANIC)
        mgr.reset_all_states()
        assert mgr.is_healthy() is True
        assert mgr.is_crashed() is False
        assert mgr.get_crash_type() is CrashType.UNKNOWN


class TestDeviceStateManagerIsUnhealthy:
    @pytest.mark.parametrize(
        "setter,expected",
        [
            ("set_crashed", True),
            ("set_busy_loop", True),
            ("set_unhealthy", True),
            ("set_normal", False),
        ],
    )
    def test_is_unhealthy_per_state(self, setter, expected):
        mgr = DeviceStateManager()
        getattr(mgr, setter)("reason")
        assert mgr.is_unhealthy() is expected


class TestDeviceStateManagerActivity:
    def test_no_activity_returns_false(self):
        mgr = DeviceStateManager(busyloop_threshold=1.0)
        assert mgr.check_busy_loop_timeout() is False

    def test_recent_activity_returns_false(self):
        mgr = DeviceStateManager(busyloop_threshold=60.0)
        mgr.update_activity()
        assert mgr.check_busy_loop_timeout() is False

    def test_exceeded_threshold_returns_true(self):
        mgr = DeviceStateManager(busyloop_threshold=60.0)
        mgr.update_activity()
        base = mgr._last_activity_time
        with patch("ntfc.device.state.time") as mock_time:
            mock_time.time.return_value = base + 61.0
            result = mgr.check_busy_loop_timeout()
        assert result is True
        assert mgr.is_busy_loop() is True

    def test_reset_clears_activity_time(self):
        mgr = DeviceStateManager(busyloop_threshold=1.0)
        mgr.update_activity()
        assert mgr._last_activity_time is not None
        mgr.reset_all_states()
        assert mgr._last_activity_time is None


_SIGNATURES: dict = {
    CrashType.ASSERTION: [b"Assertion failed"],
    CrashType.SEGFAULT: [b"up_dump_register"],
    CrashType.PANIC: [b"dump_tasks"],
}


class TestDeviceStateManagerCrashDetection:
    def test_detect_crash_type_assertion(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr._detect_crash_type(b"Assertion failed at file.c:42")
        assert result is CrashType.ASSERTION

    def test_detect_crash_type_segfault(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr._detect_crash_type(b"up_dump_register: EAX=0x0")
        assert result is CrashType.SEGFAULT

    def test_detect_crash_type_panic(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr._detect_crash_type(b"dump_tasks: PID NAME")
        assert result is CrashType.PANIC

    def test_detect_crash_type_none(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr._detect_crash_type(b"normal output, no crash here")
        assert result is None

    def test_detect_crash_type_empty_output(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        assert mgr._detect_crash_type(b"") is None

    def test_detect_crash_type_no_signatures(self):
        mgr = DeviceStateManager()
        assert mgr._detect_crash_type(b"Assertion failed") is None

    def test_check_crash_assertion(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr.check_crash(b"Assertion failed at file.c:10")
        assert result is True
        assert mgr.is_crashed() is True
        assert mgr.get_crash_type() is CrashType.ASSERTION

    def test_check_crash_no_match(self):
        mgr = DeviceStateManager(crash_signatures=_SIGNATURES)
        result = mgr.check_crash(b"all good, running normally")
        assert result is False
        assert mgr.is_crashed() is False

    def test_check_crash_no_signatures(self):
        mgr = DeviceStateManager()
        result = mgr.check_crash(b"Assertion failed")
        assert result is False

    def test_check_crash_duplicate_skips_callback(self):
        calls: list = []
        mgr = DeviceStateManager(
            crash_signatures=_SIGNATURES,
            on_state_change=lambda old, new, reason: calls.append(
                (old, new, reason)
            ),
        )
        mgr.check_crash(b"Assertion failed at a.c:1")
        mgr.check_crash(b"Assertion failed at b.c:2")
        assert len(calls) == 1


class TestDeviceStateManagerCallback:
    def test_callback_called_on_transition(self):
        calls = []

        def cb(old, new, reason):
            calls.append((old, new))

        mgr = DeviceStateManager(on_state_change=cb)
        mgr.set_crashed("oops")
        assert calls == [(DeviceState.NORMAL, DeviceState.CRASHED)]

    def test_callback_not_called_on_duplicate(self):
        calls = []

        def cb(old, new, reason):
            calls.append((old, new))

        mgr = DeviceStateManager(on_state_change=cb)
        mgr.set_crashed("first")
        mgr.set_crashed("second")  # duplicate, skipped
        assert len(calls) == 1

    def test_callback_exception_does_not_propagate(self):
        def bad_cb(old, new, reason):
            raise RuntimeError("boom")

        mgr = DeviceStateManager(on_state_change=bad_cb)
        mgr.set_crashed("x")  # must not raise
        assert mgr.is_crashed() is True

    def test_no_callback_no_error(self):
        mgr = DeviceStateManager(on_state_change=None)
        mgr.set_crashed("x")  # must not raise
        assert mgr.is_crashed() is True
