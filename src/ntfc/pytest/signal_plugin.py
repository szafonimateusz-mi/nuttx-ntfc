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

"""Pytest plugin for handling user signals during NTFC runs."""

import datetime
import faulthandler
import os
import signal
import sys
import threading
import time
import traceback
import types
from typing import Dict, List, Optional, cast

import psutil  # type: ignore[import-untyped]
import pytest
from pluggy import HookimplMarker

hookimpl = HookimplMarker("pytest")

# Variable names that should have their values redacted in stack dumps.
_SENSITIVE_PATTERNS = frozenset(
    ["password", "token", "secret", "key", "auth", "credential"]
)


class SignalPlugin:
    """Debug signal plugin for NTFC pytest runs.

    Handles:
    - SIGUSR1: Execute device 'ps' command and print output.
    - SIGUSR2: Placeholder for force panic workflow.
    - SIGQUIT: Comprehensive debug dump (faulthandler + system/process info
      + per-thread stacks with locals).
    """

    def __init__(self) -> None:
        """Initialize signal plugin state."""
        self._installed = False
        self._previous: Dict[signal.Signals, Optional[signal.Handlers]] = {}
        self._max_stack_depth = 10
        self._max_variables_per_frame = 15

    def _supported_signals(self) -> List[signal.Signals]:
        """Return supported user signals for this platform."""
        supported: List[signal.Signals] = []
        for name in ("SIGUSR1", "SIGUSR2", "SIGQUIT"):
            sig = getattr(signal, name, None)
            if sig is not None:
                supported.append(sig)
        return supported

    def _sigusr1_handler(
        self, signum: int, frame: Optional[types.FrameType]
    ) -> None:
        """Handle SIGUSR1 by running 'ps' on the device."""
        del signum, frame
        print("[ntfc] signal SIGUSR1", flush=True)
        print("[ntfc] executing device 'ps' command", flush=True)

        if not hasattr(pytest, "product") or not pytest.product:
            print("[ntfc] pytest.product not available", flush=True)
            return

        try:
            result = pytest.product.sendCommand("ps", timeout=5)
            print("[ntfc] device 'ps' output:", flush=True)
            print(result, flush=True)
        except Exception as exc:
            print(f"[ntfc] ps command failed: {exc}", flush=True)
            traceback.print_exc()

    def _sigusr2_handler(
        self, signum: int, frame: Optional[types.FrameType]
    ) -> None:
        """Handle SIGUSR2 by forcing a panic on the product."""
        del signum, frame
        print("[ntfc] signal SIGUSR2", flush=True)
        print("[ntfc] Force Panic", flush=True)

        pytest.product.force_panic()

    def _sigquit_handler(
        self, signum: int, frame: Optional[types.FrameType]
    ) -> None:
        """Handle SIGQUIT with a comprehensive debug dump."""
        print("[ntfc] signal SIGQUIT", flush=True)
        print("[ntfc] starting debug dump", flush=True)
        print("\nPYTHON FAULTHANDLER STACK TRACE:", flush=True)
        print("-" * 60, flush=True)
        try:
            faulthandler.dump_traceback(all_threads=True, file=sys.stderr)
        except Exception:
            traceback.print_exc()
        print("-" * 60, flush=True)

        self._dump_system_info()
        self._dump_process_info()
        self._dump_all_threads()
        print("\n[ntfc] debug dump completed.", flush=True)

        prev = self._previous.get(signal.SIGQUIT)
        if callable(prev):
            prev(signum, frame)

    def _format_local_vars(
        self, frame: types.FrameType, is_main: bool
    ) -> List[str]:
        """Format local variables for a frame, with redaction."""
        local_vars: List[str] = []
        for name, value in frame.f_locals.items():
            if name.startswith("__"):
                continue
            if not is_main and name == "self":
                continue

            sensitive = any(s in name.lower() for s in _SENSITIVE_PATTERNS)
            try:
                value_str = repr(value)
                if sensitive:
                    value_str = f"<REDACTED_{type(value).__name__}>"
                elif len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                local_vars.append(f"{name}={value_str}")
            except Exception:
                local_vars.append(f"{name}=<non-displayable>")

            if len(local_vars) >= self._max_variables_per_frame:
                local_vars.append("...(more variables)")
                break
        return local_vars

    def _format_arguments(self, frame: types.FrameType) -> List[str]:
        """Format function arguments for a frame."""
        arg_count = frame.f_code.co_argcount
        if not (arg_count > 0 and frame.f_locals):
            return []

        args: List[str] = []
        varnames = frame.f_code.co_varnames[:arg_count]
        for arg_name in varnames:
            if arg_name in frame.f_locals:
                try:
                    arg_val = frame.f_locals[arg_name]
                    arg_str = repr(arg_val)
                    if len(arg_str) > 60:
                        arg_str = arg_str[:60] + "..."
                    args.append(f"{arg_name}={arg_str}")
                except Exception:
                    args.append(f"{arg_name}=<non-displayable>")
        return args

    def _format_frame_info(
        self, frame: Optional[types.FrameType], level: int = 0
    ) -> str:
        """Format a frame and its call stack for diagnostics."""
        info: List[str] = []
        current = frame
        depth = 0

        while current is not None and depth < self._max_stack_depth:
            indent = "  " * (level + depth)
            is_main = depth == 0

            if depth > 0:
                info.append(f"{indent}{'─' * 50}")

            tag = "[CURRENT]" if is_main else f"[{depth}]"
            info.append(f"{indent}Frame {tag}: {current.f_code.co_name}")
            info.append(
                f"{indent}  File: "
                f"{current.f_code.co_filename}:{current.f_lineno}"
            )

            try:
                with open(
                    current.f_code.co_filename,
                    "r",
                    encoding="utf-8",
                ) as fh:
                    lines = fh.readlines()
                    if 0 < current.f_lineno <= len(lines):
                        src = lines[current.f_lineno - 1].strip()
                        info.append(f"{indent}  Code: {src}")
            except Exception:
                pass

            local_vars = self._format_local_vars(current, is_main)
            if local_vars:
                info.append(
                    f"{indent}  Variables " f"({len(current.f_locals)} total):"
                )
                for var in local_vars:
                    info.append(f"{indent}    {var}")

            args = self._format_arguments(current)
            if args:
                info.append(f"{indent}  Arguments: {', '.join(args)}")

            current = current.f_back
            depth += 1

        if current is not None:
            final_indent = "  " * (level + depth)
            info.append(
                f"{final_indent}...(stack continues beyond "
                f"max_depth={self._max_stack_depth})"
            )

        return "\n".join(info)

    def _dump_all_threads(self) -> None:
        """Dump all threads with stack traces."""
        frames = sys._current_frames()
        main_tid = threading.main_thread().ident
        print(
            f"\nThread Dump ({len(frames)} threads):",
            file=sys.stderr,
        )
        for tid, frame in frames.items():
            label = "MainThread" if tid == main_tid else f"Thread-{tid}"
            for t in threading.enumerate():
                if t.ident == tid:
                    label = t.name
                    break

            print(f"\n  {label} (ID: {tid})", file=sys.stderr)
            print("-" * 60, file=sys.stderr)
            print(
                self._format_frame_info(frame, level=2),
                file=sys.stderr,
            )

    def _dump_process_info(self) -> None:
        """Dump process resource usage."""
        proc = psutil.Process()
        print("\nProcess Information:", file=sys.stderr)
        print(f"  PID: {proc.pid}", file=sys.stderr)
        print(f"  Status: {proc.status()}", file=sys.stderr)
        uptime = datetime.timedelta(
            seconds=int(time.time() - proc.create_time())
        )
        print(f"  Uptime: {uptime}", file=sys.stderr)
        mem_mb = proc.memory_info().rss / 1024 / 1024
        print(f"  Memory: {mem_mb:.1f} MB", file=sys.stderr)
        print(f"  Threads: {len(proc.threads())}", file=sys.stderr)
        try:
            print(
                f"  File descriptors: {proc.num_fds()}",
                file=sys.stderr,
            )
        except (AttributeError, OSError):
            pass
        children = proc.children()
        if children:
            print(
                f"  Children: {[c.pid for c in children]}",
                file=sys.stderr,
            )

    def _dump_system_info(self) -> None:
        """Dump system-level information."""
        print("\nSystem Information:", file=sys.stderr)
        print(
            f"  Time: {datetime.datetime.now()}",
            file=sys.stderr,
        )
        print(f"  Python: {sys.version}", file=sys.stderr)
        print(f"  CWD: {os.getcwd()}", file=sys.stderr)
        try:
            mem = psutil.virtual_memory()
        except Exception:
            return
        print(
            f"  System memory: {mem.percent}% used",
            file=sys.stderr,
        )

    def _install(self) -> None:
        """Install signal handlers (main thread only)."""
        if self._installed:
            return
        if threading.current_thread() is not threading.main_thread():
            print(
                "[ntfc] signal handlers not installed: not in main thread",
                flush=True,
            )
            return
        for sig in self._supported_signals():
            self._previous[sig] = cast(
                "Optional[signal.Handlers]", signal.getsignal(sig)
            )
        if hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, self._sigusr1_handler)
        if hasattr(signal, "SIGUSR2"):
            signal.signal(signal.SIGUSR2, self._sigusr2_handler)
        if hasattr(signal, "SIGQUIT"):
            signal.signal(signal.SIGQUIT, self._sigquit_handler)
        self._installed = True

    def _restore(self) -> None:
        """Restore previous signal handlers."""
        if not self._installed:
            return
        for signum, previous in self._previous.items():
            signal.signal(signum, previous)
        self._previous.clear()
        self._installed = False

    @hookimpl
    def pytest_sessionstart(self) -> None:
        """Pytest hook: install signal handlers at session start."""
        self._install()

    @hookimpl
    def pytest_sessionfinish(self) -> None:
        """Pytest hook: restore signal handlers at session finish."""
        self._restore()

    @hookimpl
    def pytest_configure(self, config: object) -> None:
        """Pytest hook: install signal handlers early."""
        self._install()
