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

"""Heartbeat monitoring for device health detection."""

import threading
import time
from typing import TYPE_CHECKING, Callable, Optional

from ntfc.log.logger import logger

if TYPE_CHECKING:
    from .common import CmdReturn
    from .state import DeviceState

_StateChangeCallback = Callable[["DeviceState", "DeviceState", str], None]


###############################################################################
# Class: HeartbeatMonitor
###############################################################################


class HeartbeatMonitor:
    """Heartbeat monitoring for device busyloop detection.

    Active detection mechanism that periodically sends echo commands to
    verify the device can respond. Detects scenarios where the device
    keeps flooding logs but cannot process commands.

    :param on_state_change: Optional callback invoked on state transitions.
        Signature: ``(old, new, reason) -> None``.
    """

    # Minimum heartbeat interval to prevent device overload (30 seconds)
    _MIN_HEARTBEAT_INTERVAL = 30.0

    def __init__(
        self,
        on_state_change: Optional[_StateChangeCallback] = None,
    ) -> None:
        """Initialize :class:`HeartbeatMonitor`.

        :param on_state_change: Optional state-change callback.
            Signature: ``(old, new, reason) -> None``.
        """
        self._on_state_change = on_state_change

        # Heartbeat monitoring configuration
        self._heartbeat_enabled = False
        self._heartbeat_interval = 60.0  # Check every 60s
        self._heartbeat_timeout = 10  # Heartbeat command timeout
        self._heartbeat_threshold = 3  # 3 consecutive failures = busyloop
        self._heartbeat_failures = 0
        self._last_heartbeat_time = time.time()

        # Thread support for automatic heartbeat checking
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()
        self._in_command = (
            False  # Flag to skip heartbeat during command execution
        )
        self._device: Optional[object] = None  # Device reference for heartbeat
        self._lock = threading.Lock()

        # Callback for state transitions
        self._set_state: Optional[Callable[[str], None]] = None
        self._is_healthy_fn: Optional[Callable[[], bool]] = None

    def set_state_callbacks(
        self,
        set_busy_loop: Callable[[str], None],
        is_healthy: Callable[[], bool],
    ) -> None:
        """Register state transition callbacks.

        :param set_busy_loop: Function to call when busyloop is detected.
        :param is_healthy: Function to check if device is healthy.
        """
        self._set_state = set_busy_loop
        self._is_healthy_fn = is_healthy

    def set_device(self, device: object) -> None:
        """Set device reference for heartbeat monitoring.

        :param device: Device object that implements
            send_cmd_read_until_pattern
        """
        self._device = device

    def get_failure_count(self) -> int:  # pragma: no cover
        """Return current heartbeat failure count.

        :return: Number of consecutive heartbeat failures.
        """
        with self._lock:
            return self._heartbeat_failures

    def reset_failures(self) -> None:
        """Reset heartbeat failure count."""
        with self._lock:
            self._heartbeat_failures = 0

    def update_activity(self) -> None:
        """Record device activity and reset heartbeat failure count."""
        with self._lock:
            self._heartbeat_failures = 0

    def mark_command_start(self) -> None:
        """Mark that a command is being executed.

        This prevents heartbeat checks from interfering with command execution.
        """
        with self._lock:
            self._in_command = True

    def mark_command_end(self) -> None:
        """Mark that command execution has finished.

        This allows heartbeat checks to resume and resets activity time.
        """
        with self._lock:
            self._in_command = False
            self._heartbeat_failures = 0

    def enable_heartbeat(
        self, interval: float = 60, threshold: int = 3
    ) -> None:
        """Enable heartbeat detection.

        :param interval: Heartbeat check interval (seconds, minimum 30)
        :param threshold: Failure threshold (consecutive failures for busyloop)
        :raises ValueError: If interval is less than minimum (30 seconds)
        """
        # Validate interval to prevent device overload
        if interval < self._MIN_HEARTBEAT_INTERVAL:
            raise ValueError(  # pragma: no cover
                f"Heartbeat interval must be at least "
                f"{self._MIN_HEARTBEAT_INTERVAL}s (got {interval}s). "
                "Shorter intervals cause device overload and command "
                "conflicts."
            )

        self._heartbeat_enabled = True
        self._heartbeat_interval = interval
        self._heartbeat_threshold = threshold
        self._heartbeat_failures = 0
        logger.info(
            f"Heartbeat monitoring enabled: interval={interval}s, "
            f"threshold={threshold}"
        )

        # Start background monitoring thread
        self._start_monitor_thread()

    def disable_heartbeat(self) -> None:
        """Disable heartbeat detection."""
        self._heartbeat_enabled = False
        logger.info("Heartbeat monitoring disabled")

        # Stop background monitoring thread
        self._stop_monitor_thread()

    def _start_monitor_thread(self) -> None:
        """Start background monitoring thread."""
        if (
            self._monitor_thread is not None
            and self._monitor_thread.is_alive()
        ):
            logger.debug("Monitor thread already running")
            return

        self._monitor_stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="HeartbeatMonitor"
        )
        self._monitor_thread.start()
        logger.info("Heartbeat monitor thread started")

    def _stop_monitor_thread(self) -> None:
        """Stop background monitoring thread."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            logger.debug("Monitor thread not running")
            return

        self._monitor_stop_event.set()
        self._monitor_thread.join(timeout=5.0)

        if self._monitor_thread.is_alive():
            logger.warning("Monitor thread did not stop gracefully")
        else:
            logger.info("Heartbeat monitor thread stopped")

        self._monitor_thread = None

    def _monitor_loop(self) -> None:
        """Background monitoring loop.

        This runs in a separate thread and periodically checks device state.
        """
        logger.debug("Monitor loop started")

        while not self._monitor_stop_event.is_set():
            try:
                # Check if heartbeat is still enabled
                if not self._heartbeat_enabled:
                    break

                # Check if it's time for heartbeat check
                if self._should_check_heartbeat():
                    logger.debug("Performing scheduled heartbeat check")
                    self._check_heartbeat()

                # Sleep for a short interval (check every second)
                self._monitor_stop_event.wait(timeout=1.0)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                # Continue running despite errors
                time.sleep(1.0)

        logger.debug("Monitor loop exited")

    def _should_check_heartbeat(self) -> bool:
        """Check if heartbeat check should be performed.

        Skips heartbeat check when:
        - Device is not open
        - Device is in unhealthy state (crashed/busyloop)
        - Device is in interactive mode
        - Device is executing another command (locked)

        :return: True if check is needed
        """
        with self._lock:
            # Skip heartbeat if command is being executed (locked)
            if self._in_command:
                return False

            # Check time interval
            elapsed = time.time() - self._last_heartbeat_time
            if elapsed < self._heartbeat_interval:
                return False

            # Check if device is open
            if self._device is not None and hasattr(self._device, "_open"):
                if not self._device._open:
                    logger.debug("Device not open, skipping heartbeat")
                    return False

            # Check if device is in unhealthy state
            if self._is_healthy_fn is not None and not self._is_healthy_fn():
                logger.debug("Device in unhealthy state, skipping heartbeat")
                return False

            # Check if device is in interactive mode
            if self._device is not None and hasattr(
                self._device, "_interactive_mode"
            ):
                if self._device._interactive_mode:
                    logger.debug(
                        "Device in interactive mode, skipping heartbeat"
                    )
                    return False

            return True

    def _check_heartbeat(self) -> bool:
        """Execute heartbeat check (active detection).

        Sends a simple echo command to check if device can respond normally.
        This detects busyloop scenarios where device keeps logging but
        cannot respond to commands.

        :return: True if heartbeat is normal, False if failed
        """
        if self._device is None:
            logger.warning("Device not set, cannot perform heartbeat check")
            return True

        self._last_heartbeat_time = time.time()

        # Mark command start to prevent conflicts
        self.mark_command_start()
        try:
            return self._send_heartbeat_command()
        finally:
            # Clear command flag (don't use mark_command_end as it resets
            # heartbeat_failures)
            with self._lock:
                self._in_command = False
                self._last_heartbeat_time = time.time()

    def _send_heartbeat_command(self) -> bool:
        """Send heartbeat command and check response.

        :return: True if heartbeat passed, False if threshold reached
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cmd = f"echo '[heartbeat {timestamp}]'".encode()
        pattern = f"heartbeat {timestamp}".encode()

        logger.debug(f"Sending heartbeat: {cmd!r}")

        try:
            # Import here to avoid circular dependency
            from .common import CmdStatus  # noqa: F811

            result: "CmdReturn" = self._device.send_cmd_read_until_pattern(  # type: ignore[union-attr]  # noqa: E501
                cmd, pattern, timeout=self._heartbeat_timeout
            )

            if result.status == CmdStatus.SUCCESS:
                with self._lock:
                    self._heartbeat_failures = 0
                logger.debug("Heartbeat check passed")
                return True
            else:
                return self._handle_heartbeat_failure(f"{result.status}")

        except Exception as e:
            return self._handle_heartbeat_failure(f"exception: {e}")

    def _handle_heartbeat_failure(self, error: str) -> bool:
        """Handle heartbeat check failure.

        :param error: Error message describing the failure
        :return: True if below threshold, False if threshold reached
        """
        with self._lock:
            self._heartbeat_failures += 1
            failures = self._heartbeat_failures
            threshold = self._heartbeat_threshold

        logger.warning(
            f"Heartbeat check failed ({failures}/{threshold}): {error}"
        )

        if failures >= threshold:
            logger.error(
                f"Heartbeat failed {failures} times, "
                "device is likely in busyloop (keeps logging but "
                "not responding)"
            )
            if self._set_state is not None:
                self._set_state(f"Heartbeat failed {failures} times")
            return False

        return True
