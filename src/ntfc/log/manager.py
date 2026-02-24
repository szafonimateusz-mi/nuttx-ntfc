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

"""NTFC log management module."""

import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml  # type: ignore

from ntfc.log.logger import logger

###############################################################################
# Class: LogManager
###############################################################################

_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


class LogManager:
    """Manages log storage, directory resolution, and automatic cleanup.

    Reads configuration from a YAML file and provides the results
    directory path.  Automatic cleanup evaluates all configured rules
    simultaneously and removes the union of matching sessions.
    The session directory naming format is also centralised here.
    """

    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "log.yaml"
    )
    SESSION_FORMAT = "%Y-%m-%d_%H-%M-%S"

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize LogManager.

        :param config_path: Path to log YAML configuration file.
            Defaults to ``log.yaml`` in the ntfc package root when *None*.
        """
        self._config = self._load_config(
            config_path or self.DEFAULT_CONFIG_PATH
        )

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load log YAML config; return empty dict when file is absent.

        :param path: Path to the YAML configuration file.
        :return: Parsed configuration dictionary.
        """
        if not os.path.exists(path):
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def results_dir(self) -> str:
        """Return configured results directory.

        :return: Path to the directory where test sessions are stored.
        """
        value = self._config.get("log", {}).get("results_dir", "./result")
        return str(value)

    @property
    def max_age_days(self) -> Optional[int]:
        """Return maximum age in days for session directories.

        :return: Maximum age in days, or *None* when age cleanup is disabled.
        """
        value = self._config.get("log", {}).get("max_age_days")
        return int(value) if value is not None else None

    @property
    def max_count(self) -> Optional[int]:
        """Return maximum number of session directories to keep.

        :return: Session count limit, or *None* when count cleanup is disabled.
        """
        value = self._config.get("log", {}).get("max_count")
        return int(value) if value is not None else None

    @property
    def max_size_mb(self) -> Optional[float]:
        """Return maximum total size in megabytes for the results directory.

        :return: Size limit in MB, or *None* when size cleanup is disabled.
        """
        value = self._config.get("log", {}).get("max_size_mb")
        return float(value) if value is not None else None

    def _session_dirs(self) -> List[Tuple[float, str]]:
        """Return session directories sorted by modification time.

        Oldest directories come first.  Only directories whose names match
        the session timestamp pattern ``YYYY-MM-DD_HH-MM-SS`` are included.

        :return: List of ``(mtime, path)`` tuples sorted ascending by mtime.
        """
        entries = []
        try:
            names = os.listdir(self.results_dir)
        except OSError:  # pragma: no cover
            return []

        for name in names:
            if not _SESSION_RE.match(name):
                continue
            full = os.path.join(self.results_dir, name)
            if not os.path.isdir(full):
                continue
            entries.append((os.path.getmtime(full), full))

        entries.sort(key=lambda t: t[0])
        return entries

    def _dir_size_mb(self, path: str) -> float:
        """Return total size of a directory tree in megabytes.

        :param path: Root directory to measure.
        :return: Size in MB.
        """
        total = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for fname in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fname))
                except OSError:  # pragma: no cover
                    pass
        return total / (1024 * 1024)

    def _compute_removals(self, sessions: List[Tuple[float, str]]) -> Set[str]:
        """Compute session paths to remove based on all configured rules.

        Each rule (age, count, size) is evaluated independently.
        The returned set is the union of all rules' results.

        :param sessions: List of ``(mtime, path)`` tuples sorted ascending.
        :return: Set of session directory paths to remove.
        """
        to_remove: Set[str] = set()

        # Age-based rule: mark sessions older than max_age_days
        if self.max_age_days is not None:
            cutoff = datetime.now(tz=timezone.utc).timestamp() - (
                self.max_age_days * 86400
            )
            for mtime, path in sessions:
                if mtime < cutoff:
                    to_remove.add(path)

        # Count-based rule: keep only the max_count latest sessions
        if self.max_count is not None and len(sessions) > self.max_count:
            for _, path in sessions[: len(sessions) - self.max_count]:
                to_remove.add(path)

        # Size-based rule: mark oldest sessions until total is within limit
        if self.max_size_mb is not None:
            sizes = {path: self._dir_size_mb(path) for _, path in sessions}
            total = sum(sizes.values())
            for _, path in sessions:
                if total <= self.max_size_mb:
                    break
                to_remove.add(path)
                total -= sizes[path]

        return to_remove

    def new_session_dir(self) -> str:
        """Create and return a new timestamped session directory.

        The directory name is formatted with :attr:`SESSION_FORMAT` and
        created under :attr:`results_dir`.

        :return: Absolute path to the newly created session directory.
        """
        name = datetime.now().strftime(self.SESSION_FORMAT)
        path = os.path.join(self.results_dir, name)
        os.makedirs(path, exist_ok=True)
        return path

    def cleanup(self) -> None:
        """Remove sessions that violate any configured cleanup rule.

        All rules (age, count, size) are evaluated simultaneously and
        their results are merged before any directory is removed.
        Does nothing when the results directory does not exist yet.
        """
        if not os.path.isdir(self.results_dir):
            return
        sessions = self._session_dirs()
        to_remove = self._compute_removals(sessions)
        for _, path in sessions:
            if path in to_remove:
                logger.info(f"[LogManager] Removing session: {path}")
                shutil.rmtree(path, ignore_errors=True)
