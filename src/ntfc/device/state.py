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

"""Device state machine for debug monitoring."""

import functools
import threading
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, TypeVar

from ntfc.device.heartbeat import HeartbeatMonitor, _SendFn
from ntfc.log.logger import logger

_F = TypeVar("_F", bound=Callable[..., Any])

_StateChangeCallback = Callable[["DeviceState", "DeviceState", str], None]


###############################################################################
# Enum: CrashType
###############################################################################


class CrashType(Enum):
    """Crash type enumeration.

    :cvar UNKNOWN: Crash type not determined.
    :cvar ASSERTION: Assertion failure.
    :cvar SEGFAULT: Segmentation fault or memory access violation.
    :cvar PANIC: Kernel panic.
    """

    UNKNOWN = auto()
    ASSERTION = auto()
    SEGFAULT = auto()
    PANIC = auto()


###############################################################################
# Enum: DeviceState
###############################################################################


class DeviceState(Enum):
    """Device state enumeration.

    :cvar NORMAL: Device is operating normally.
    :cvar BUSY_LOOP: Device is stuck in a busy loop.
    :cvar CRASHED: Device has crashed or encountered a fatal error.
    :cvar UNHEALTHY: Device is in an unhealthy state (general condition).
    """

    NORMAL = auto()
    BUSY_LOOP = auto()
    CRASHED = auto()
    UNHEALTHY = auto()


###############################################################################
# Class: DeviceStateManager
###############################################################################


class DeviceStateManager:
    """Thread-safe device state machine.

    Replaces scattered :class:`threading.Event` flags in device classes
    with a single, coherent state representation that supports optional
    change notifications and typed crash detection.

    :param busyloop_threshold: Seconds of silence before the device is
        declared to be in a busy loop.  Defaults to ``180.0``.
    :param on_state_change: Optional callback invoked on every state change.
        Signature: ``(old, new, reason) -> None``.
    :param crash_signatures: Mapping of :class:`CrashType` to byte
        patterns used by :meth:`check_crash` to classify crashes.
    """

    def __init__(
        self,
        busyloop_threshold: float = 180.0,
        on_state_change: Optional[_StateChangeCallback] = None,
        crash_signatures: Optional[Dict[CrashType, List[bytes]]] = None,
        heartbeat_send_fn: Optional[_SendFn] = None,
    ) -> None:
        """Initialize :class:`DeviceStateManager`.

        :param busyloop_threshold: Seconds of silence triggering busy loop.
        :param on_state_change: Optional state-change callback.
            Signature: ``(old, new, reason) -> None``.
        :param crash_signatures: Crash pattern map for :meth:`check_crash`.
        :param heartbeat_send_fn: Optional callable used by heartbeat checks.
        """
        self._busyloop_threshold = busyloop_threshold
        self._on_state_change = on_state_change
        self._crash_signatures: Dict[CrashType, List[bytes]] = (
            crash_signatures or {}
        )
        self._lock = threading.Lock()
        self._current_state = DeviceState.NORMAL
        self._last_activity_time: Optional[float] = None
        self._crash_type: CrashType = CrashType.UNKNOWN

        # Heartbeat monitoring (delegated to HeartbeatMonitor)
        self._heartbeat = HeartbeatMonitor(
            on_state_change=on_state_change,
            set_busy_loop=self.set_busy_loop,
            is_healthy=self.is_healthy,
            send_fn=heartbeat_send_fn,
        )

    def get_current_state(self) -> DeviceState:
        """Return the current device state (thread-safe).

        :return: Current :class:`DeviceState`.
        """
        with self._lock:
            return self._current_state

    def is_crashed(self) -> bool:
        """Return ``True`` if the device is in the crashed state."""
        return self._current_state == DeviceState.CRASHED

    def is_busy_loop(self) -> bool:
        """Return ``True`` if the device is in the busy loop state."""
        return self._current_state == DeviceState.BUSY_LOOP

    def is_healthy(self) -> bool:
        """Return ``True`` if the device is in the normal (healthy) state."""
        return self._current_state == DeviceState.NORMAL

    def is_unhealthy(self) -> bool:
        """Return ``True`` if the device is in any fault state.

        A device is considered unhealthy when its state is one of
        :attr:`~DeviceState.CRASHED`, :attr:`~DeviceState.BUSY_LOOP`, or
        :attr:`~DeviceState.UNHEALTHY`.
        """
        return self._current_state in {
            DeviceState.CRASHED,
            DeviceState.BUSY_LOOP,
            DeviceState.UNHEALTHY,
        }

    def get_crash_type(self) -> CrashType:
        """Return the crash type from the most recent crash.

        :return: :class:`CrashType` indicating the crash category, or
            :attr:`~CrashType.UNKNOWN` if not crashed or type not
            determined.
        """
        with self._lock:
            return self._crash_type

    def set_crashed(
        self,
        reason: str = "",
        crash_type: CrashType = CrashType.UNKNOWN,
    ) -> None:
        """Transition to the :attr:`~DeviceState.CRASHED` state.

        :param reason: Description of the crash.
        :param crash_type: Category of the crash.
        """
        self._transition_to(
            DeviceState.CRASHED,
            reason or "Device crashed",
            crash_type=crash_type,
        )

    def set_busy_loop(self, reason: str = "") -> None:
        """Transition to the :attr:`~DeviceState.BUSY_LOOP` state.

        :param reason: Description of why the busy loop was detected.
        """
        self._transition_to(
            DeviceState.BUSY_LOOP,
            reason or "Busy loop detected",
        )

    def set_unhealthy(self, reason: str = "") -> None:
        """Transition to the :attr:`~DeviceState.UNHEALTHY` state.

        :param reason: Description of the unhealthy condition.
        """
        self._transition_to(
            DeviceState.UNHEALTHY,
            reason or "Device unhealthy",
        )

    def set_normal(self, reason: str = "") -> None:
        """Transition to the :attr:`~DeviceState.NORMAL` state.

        :param reason: Reason for returning to normal.
        """
        self._transition_to(
            DeviceState.NORMAL,
            reason or "Device operating normally",
        )

    def reset_all_states(self) -> None:
        """Reset state to :attr:`~DeviceState.NORMAL` and clear activity timer.

        Used to reinitialise the device between test runs.
        """
        with self._lock:
            self._current_state = DeviceState.NORMAL
            self._last_activity_time = None
            self._crash_type = CrashType.UNKNOWN
        self._heartbeat.reset_failures()

    def update_activity(self) -> None:
        """Record that the device produced output.

        Call this whenever a non-empty data chunk is received from the
        device.  The timestamp is used by :meth:`check_busy_loop_timeout`.
        Also resets heartbeat failure count.
        """
        with self._lock:
            self._last_activity_time = time.time()
        self._heartbeat.update_activity()

    def mark_command_start(self) -> None:
        """Mark that a command is being executed.

        This prevents heartbeat checks from interfering with command execution.
        """
        self._heartbeat.mark_command_start()

    def mark_command_end(self) -> None:
        """Mark that command execution has finished.

        This allows heartbeat checks to resume and resets activity time.
        """
        self._heartbeat.mark_command_end()
        with self._lock:
            self._last_activity_time = time.time()

    def check_busy_loop_timeout(self) -> bool:
        """Return ``True`` and enter busy-loop state if the device went silent.

        Compares the time since :meth:`update_activity` was last called
        against ``busyloop_threshold``.  If the threshold is exceeded the
        state machine transitions to :attr:`~DeviceState.BUSY_LOOP` and
        ``True`` is returned.

        :return: ``True`` if the busy-loop threshold has been exceeded,
            ``False`` otherwise.
        """
        if self._last_activity_time is None:
            return False
        idle_time = time.time() - self._last_activity_time
        if idle_time > self._busyloop_threshold:
            self.set_busy_loop(
                reason=f"No output for {idle_time:.1f}s",
            )
            return True
        return False

    def _detect_crash_type(self, output: bytes) -> Optional[CrashType]:
        """Identify crash type from raw device output.

        Iterates over all registered crash signatures and returns the type
        of the first pattern found in *output*.  Returns ``None`` when no
        signature matches or when no signatures are registered.

        :param output: Raw bytes received from the device.
        :return: Matching :class:`CrashType`, or ``None``.
        """
        for crash_type, signatures in self._crash_signatures.items():
            for sig in signatures:
                if sig in output:
                    return crash_type
        return None

    def check_crash(self, output: bytes) -> bool:
        """Check output for crash signatures and transition to CRASHED.

        Calls :meth:`_detect_crash_type` to classify the crash, then
        transitions to :attr:`~DeviceState.CRASHED` via
        :meth:`set_crashed`.  The underlying :meth:`_transition_to` guard
        skips duplicate transitions when the device is already in the
        CRASHED state.

        :param output: Raw bytes received from the device.
        :return: ``True`` if any crash signature was found, ``False``
            otherwise.
        """
        crash_type = self._detect_crash_type(output)
        if crash_type is None:
            return False
        self.set_crashed(
            reason=f"{crash_type.name.capitalize()} detected",
            crash_type=crash_type,
        )
        return True

    def _transition_to(
        self,
        new_state: DeviceState,
        reason: str,
        crash_type: Optional[CrashType] = None,
    ) -> None:
        """Perform a guarded state transition.

        Skips the transition when already in *new_state*, except when
        *new_state* is :attr:`~DeviceState.NORMAL` (recovery is always
        processed).

        :param new_state: Destination state.
        :param reason: Human-readable reason for the transition.
        :param crash_type: When provided and transition to CRASHED succeeds,
            the crash type is stored atomically inside the lock.
        """
        with self._lock:
            old_state = self._current_state
            if old_state == new_state and new_state != DeviceState.NORMAL:
                return
            self._current_state = new_state
            if crash_type is not None:
                self._crash_type = crash_type

        logger.debug(
            "device state: %s -> %s (%s)",
            old_state.name,
            new_state.name,
            reason,
        )
        if self._on_state_change is not None:
            try:
                self._on_state_change(old_state, new_state, reason)
            except Exception as exc:
                logger.warning("state change callback raised: %s", exc)

    @staticmethod
    def mark_command(method: _F) -> _F:
        """Mark a method as a device command, skipping heartbeat checks.

        Calls :meth:`mark_command_start` before and :meth:`mark_command_end`
        after the method.
        """

        @functools.wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            self._state_mgr.mark_command_start()
            try:
                return method(self, *args, **kwargs)
            finally:
                self._state_mgr.mark_command_end()

        return wrapper  # type: ignore[return-value]

    def enable_heartbeat(
        self,
        interval: float = 60,
        threshold: int = 3,
    ) -> None:
        """Enable heartbeat detection.

        :param interval: Heartbeat check interval (seconds, minimum 30)
        :param threshold: Failure threshold (consecutive failures for busyloop)
        :raises ValueError: If interval is less than minimum (30 seconds)
        """
        self._heartbeat.enable_heartbeat(interval, threshold)

    def disable_heartbeat(self) -> None:
        """Disable heartbeat detection."""
        self._heartbeat.disable_heartbeat()
