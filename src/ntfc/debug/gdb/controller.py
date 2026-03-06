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

"""GDB controller for automated coredump generation."""

import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ntfc.log.logger import logger

if TYPE_CHECKING:
    from ntfc.debug.config import GdbConfig


###############################################################################
# Class: GdbController
###############################################################################


class GdbController:
    """Controls a GDB subprocess for remote debugging and coredump generation.

    Launches GDB in non-interactive (``-q``) mode, attaches to a remote
    target specified by :attr:`~ntfc.debug.config.GdbConfig.target`, and
    exposes :meth:`generate_coredump` to write a core file.

    :param elf_path: Path to the ELF binary loaded by GDB.
    :param cfg: GDB section of the product debug configuration.
    """

    def __init__(self, elf_path: Path, cfg: "GdbConfig") -> None:
        """Initialize :class:`GdbController`.

        :param elf_path: Path to the ELF binary.
        :param cfg: GDB configuration object.
        """
        self._elf_path = elf_path
        self._cfg = cfg
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._reader: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._gcore_done = threading.Event()
        self._last_corefile: Optional[Path] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self, timeout: float = 30.0) -> bool:  # noqa: A003
        """Start GDB and attach to the configured remote target.

        Spawns ``gdb -q <elf_path>``, waits for the GDB prompt, then sends
        ``target remote <cfg.target>``.

        :param timeout: Seconds to wait for the GDB prompt before giving up.
        :return: ``True`` on success, ``False`` on timeout or process exit.
        """
        self._ready.clear()
        self._process = subprocess.Popen(
            ["gdb", "-q", str(self._elf_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

        if not self._ready.wait(timeout=timeout):
            logger.warning("gdb: timed out waiting for prompt")
            self._terminate()
            return False

        if self._process.returncode is not None:
            logger.warning("gdb: process exited before prompt")
            return False

        if self._cfg.target:
            self._send(f"target remote {self._cfg.target}\n")

        return True

    def close(self) -> None:
        """Quit GDB and clean up the subprocess and reader thread."""
        self._send("quit\n")
        if self._process is not None:
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._terminate()
        if self._reader is not None:
            self._reader.join(timeout=5.0)

    def generate_coredump(
        self, output_dir: Path, prefix: str, timeout: float = 300.0
    ) -> Optional[Path]:
        """Send a ``gcore`` command and wait for the file to be written.

        :param output_dir: Directory where the corefile is placed.
        :param prefix: Filename stem for the generated corefile.
        :param timeout: Seconds to wait for ``gcore`` to finish.
        :return: :class:`~pathlib.Path` to the corefile, or ``None`` on
            failure or timeout.
        """
        with self._lock:
            self._gcore_done.clear()
            self._last_corefile = None

        corefile = output_dir / f"{prefix}.core"
        self._send(f"gcore {corefile}\n")

        if not self._gcore_done.wait(timeout=timeout):
            logger.warning("gdb: timed out waiting for gcore")
            return None

        with self._lock:
            return self._last_corefile

    def is_running(self) -> bool:
        """Return ``True`` if the GDB process is alive.

        :return: ``True`` when the process exists and has not yet terminated.
        """
        return self._process is not None and self._process.returncode is None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _send(self, command: str) -> None:
        r"""Write *command* to GDB's stdin.

        No-ops silently when the process is not running.

        :param command: Raw GDB command string (should end with ``\n``).
        """
        if self._process is None or self._process.stdin is None:
            return
        try:
            self._process.stdin.write(command.encode())
            self._process.stdin.flush()
        except OSError as exc:
            logger.debug("gdb: stdin write failed: %s", exc)

    def _terminate(self) -> None:
        """Forcibly terminate the GDB process."""
        if self._process is not None:  # pragma: no branch
            self._process.terminate()

    def _read_stdout(self) -> None:
        """Background thread: parse GDB stdout and set synchronisation events.

        Recognises:

        * ``(gdb)`` / ``Type "help"`` — sets :attr:`_ready`
        * ``Saved corefile`` — parses path, sets :attr:`_gcore_done`
        * EOF — sets both events to unblock any waiters
        """
        if (
            self._process is None or self._process.stdout is None
        ):  # pragma: no cover
            self._ready.set()
            self._gcore_done.set()
            return

        for raw_line in self._process.stdout:
            line = raw_line.decode(errors="replace").rstrip()
            logger.debug("gdb< %s", line)

            if "(gdb)" in line or 'Type "help"' in line:
                self._ready.set()

            if "Saved corefile" in line:
                parts = line.split()
                corefile_path = Path(parts[-1])
                with self._lock:
                    self._last_corefile = corefile_path
                self._gcore_done.set()

        # EOF — unblock any waiters so they can observe the failure
        self._ready.set()  # pragma: no cover
        self._gcore_done.set()  # pragma: no cover
