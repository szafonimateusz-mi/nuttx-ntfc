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

"""Tests for NTFC log manager module."""

import os
import re
import tempfile
from datetime import datetime, timezone

import yaml  # type: ignore

from ntfc.log.manager import LogManager

###############################################################################
# Helpers
###############################################################################


def _write_log_yaml(tmpdir: str, **log_fields: object) -> str:
    """Write a log.yaml config file and return its path.

    :param tmpdir: Destination directory for the config file.
    :param log_fields: Key-value pairs placed under the ``log`` key.
    :return: Absolute path to the written YAML file.
    """
    path = os.path.join(tmpdir, "log.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump({"log": dict(log_fields)}, f)
    return path


def _make_session(results_dir: str, name: str, mtime: float = 0) -> str:
    """Create a timestamped session directory.

    :param results_dir: Parent results directory.
    :param name: Session directory name (``YYYY-MM-DD_HH-MM-SS``).
    :param mtime: If non-zero, override mtime with this POSIX timestamp.
    :return: Absolute path to the created session directory.
    """
    path = os.path.join(results_dir, name)
    os.makedirs(path, exist_ok=True)
    if mtime:
        os.utime(path, (mtime, mtime))
    return path


def _write_data(path: str, size_bytes: int) -> None:
    """Write a binary file of the given size into *path*.

    :param path: Directory in which to create the file.
    :param size_bytes: Number of bytes to write.
    """
    with open(os.path.join(path, "data.bin"), "wb") as f:
        f.write(b"x" * size_bytes)


###############################################################################
# Tests: config loading and properties
###############################################################################


def test_results_dir_default_when_config_absent() -> None:
    """Default ``./result`` returned when config file does not exist."""
    lm = LogManager("/nonexistent/path/log.yaml")
    assert lm.results_dir == "./result"


def test_results_dir_from_config() -> None:
    """``results_dir`` returns value specified in YAML config."""
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, results_dir="/tmp/myresults")
        lm = LogManager(path)
        assert lm.results_dir == "/tmp/myresults"


def test_max_age_days_none_when_absent() -> None:
    """``max_age_days`` is *None* when not present in config."""
    lm = LogManager("/nonexistent/path/log.yaml")
    assert lm.max_age_days is None


def test_max_age_days_from_config() -> None:
    """``max_age_days`` returns integer value from YAML config."""
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_age_days=7)
        lm = LogManager(path)
        assert lm.max_age_days == 7


def test_max_count_none_when_absent() -> None:
    """``max_count`` is *None* when not present in config."""
    lm = LogManager("/nonexistent/path/log.yaml")
    assert lm.max_count is None


def test_max_count_from_config() -> None:
    """``max_count`` returns integer value from YAML config."""
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_count=50)
        lm = LogManager(path)
        assert lm.max_count == 50


def test_max_size_mb_none_when_absent() -> None:
    """``max_size_mb`` is *None* when not present in config."""
    lm = LogManager("/nonexistent/path/log.yaml")
    assert lm.max_size_mb is None


def test_max_size_mb_from_config() -> None:
    """``max_size_mb`` returns numeric value from YAML config."""
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_size_mb=500.0)
        lm = LogManager(path)
        assert lm.max_size_mb == 500.0


def test_load_config_empty_yaml() -> None:
    """Empty YAML file yields default ``results_dir``."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        f.write("")
        config_path = f.name
    try:
        lm = LogManager(config_path)
        assert lm.results_dir == "./result"
    finally:
        os.unlink(config_path)


def test_default_config_path_when_none() -> None:
    """``LogManager()`` with no argument uses ``DEFAULT_CONFIG_PATH``."""
    # log.yaml ships inside the ntfc package directory
    lm = LogManager()
    assert lm.results_dir == "./result"
    assert lm.max_age_days == 30
    assert lm.max_count == 100
    assert lm.max_size_mb == 50.0


###############################################################################
# Tests: _session_dirs
###############################################################################


def test_session_dirs_empty_when_no_sessions() -> None:
    """``_session_dirs`` returns empty list when no matching entries exist."""
    with tempfile.TemporaryDirectory() as results_dir:
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            assert lm._session_dirs() == []


def test_session_dirs_ignores_non_matching_entries() -> None:
    """``_session_dirs`` skips dirs and files that don't match the pattern."""
    with tempfile.TemporaryDirectory() as results_dir:
        # non-matching directory and regular file
        os.makedirs(os.path.join(results_dir, "logs"))
        open(os.path.join(results_dir, "readme.txt"), "w").close()
        # wrong format dir
        os.makedirs(os.path.join(results_dir, "2024_01_01_10_00_00"))
        # session-pattern name that is a *file*, not a directory (covers
        # the os.path.isdir guard inside _session_dirs)
        open(os.path.join(results_dir, "2024-01-03_10-00-00"), "w").close()
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            assert lm._session_dirs() == []


def test_session_dirs_sorted_oldest_first() -> None:
    """``_session_dirs`` returns entries sorted ascending by mtime."""
    with tempfile.TemporaryDirectory() as results_dir:
        d1 = _make_session(results_dir, "2024-01-01_10-00-00", mtime=1000.0)
        d2 = _make_session(results_dir, "2024-01-02_10-00-00", mtime=2000.0)
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            dirs = lm._session_dirs()
            assert len(dirs) == 2
            assert dirs[0][1] == d1
            assert dirs[1][1] == d2


###############################################################################
# Tests: _dir_size_mb
###############################################################################


def test_dir_size_mb() -> None:
    """``_dir_size_mb`` returns the correct size in megabytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "file.bin")
        with open(filepath, "wb") as f:
            f.write(b"x" * 1024 * 1024)  # exactly 1 MB
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=tmpdir)
            lm = LogManager(path)
            assert abs(lm._dir_size_mb(tmpdir) - 1.0) < 0.01


###############################################################################
# Tests: _compute_removals
###############################################################################


def test_compute_removals_all_rules_none() -> None:
    """``_compute_removals`` returns empty set when no rules are configured."""
    sessions = [(1000.0, "/r/2024-01-01_10-00-00")]
    lm = LogManager("/nonexistent/log.yaml")
    assert lm._compute_removals(sessions) == set()


def test_compute_removals_age_marks_old_preserves_recent() -> None:
    """Age rule marks old sessions and preserves recent ones."""
    old_mtime = datetime.now(tz=timezone.utc).timestamp() - (40 * 86400)
    recent_mtime = datetime.now(tz=timezone.utc).timestamp() - (5 * 86400)
    old_path = "/results/2024-01-01_00-00-00"
    recent_path = "/results/2024-06-01_00-00-00"
    sessions = [(old_mtime, old_path), (recent_mtime, recent_path)]
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_age_days=30)
        lm = LogManager(path)
        to_remove = lm._compute_removals(sessions)
        assert old_path in to_remove
        assert recent_path not in to_remove


def test_compute_removals_count_marks_excess() -> None:
    """Count rule marks oldest sessions beyond the configured limit."""
    sessions = [
        (1000.0, "/r/2024-01-01_10-00-00"),
        (2000.0, "/r/2024-01-02_10-00-00"),
        (3000.0, "/r/2024-01-03_10-00-00"),
    ]
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_count=2)
        lm = LogManager(path)
        to_remove = lm._compute_removals(sessions)
        assert "/r/2024-01-01_10-00-00" in to_remove
        assert "/r/2024-01-02_10-00-00" not in to_remove
        assert "/r/2024-01-03_10-00-00" not in to_remove


def test_compute_removals_count_within_limit() -> None:
    """Count rule is skipped when session count is at or below the limit."""
    sessions = [
        (1000.0, "/r/2024-01-01_10-00-00"),
        (2000.0, "/r/2024-01-02_10-00-00"),
    ]
    with tempfile.TemporaryDirectory() as cfgdir:
        path = _write_log_yaml(cfgdir, max_count=3)
        lm = LogManager(path)
        assert lm._compute_removals(sessions) == set()


def test_compute_removals_size_marks_oldest() -> None:
    """Size rule marks oldest sessions until total fits within the limit."""
    with tempfile.TemporaryDirectory() as results_dir:
        d1 = _make_session(results_dir, "2024-01-01_10-00-00", mtime=1000.0)
        d2 = _make_session(results_dir, "2024-01-02_10-00-00", mtime=2000.0)
        _write_data(d1, 1024 * 1024)  # 1 MB
        _write_data(d2, 1024 * 1024)  # 1 MB  (total 2 MB > 1.5 MB limit)
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(
                cfgdir, results_dir=results_dir, max_size_mb=1.5
            )
            lm = LogManager(path)
            sessions = [(1000.0, d1), (2000.0, d2)]
            to_remove = lm._compute_removals(sessions)
            assert d1 in to_remove
            assert d2 not in to_remove


def test_compute_removals_size_marks_all_sessions() -> None:
    """Size rule marks every session when all together still exceed limit."""
    with tempfile.TemporaryDirectory() as results_dir:
        d1 = _make_session(results_dir, "2024-01-01_10-00-00", mtime=1000.0)
        d2 = _make_session(results_dir, "2024-01-02_10-00-00", mtime=2000.0)
        _write_data(d1, 1024 * 1024)  # 1 MB
        _write_data(d2, 1024 * 1024)  # 1 MB  (2 MB total > 0.5 MB limit)
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(
                cfgdir, results_dir=results_dir, max_size_mb=0.5
            )
            lm = LogManager(path)
            sessions = [(1000.0, d1), (2000.0, d2)]
            to_remove = lm._compute_removals(sessions)
            assert d1 in to_remove
            assert d2 in to_remove


def test_compute_removals_size_within_limit() -> None:
    """Size rule marks nothing when total size is within the limit."""
    with tempfile.TemporaryDirectory() as results_dir:
        d1 = _make_session(results_dir, "2024-01-01_10-00-00")
        _write_data(d1, 512 * 1024)  # 0.5 MB  (under 10 MB limit)
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(
                cfgdir, results_dir=results_dir, max_size_mb=10.0
            )
            lm = LogManager(path)
            sessions = [(1000.0, d1)]
            assert lm._compute_removals(sessions) == set()


def test_compute_removals_all_rules_combined() -> None:
    """All three rules contribute independently to the removal set."""
    with tempfile.TemporaryDirectory() as results_dir:
        old_mtime = datetime.now(tz=timezone.utc).timestamp() - (40 * 86400)
        # d1: old (age rule marks it) and oldest (count + size mark it too)
        d1 = _make_session(results_dir, "2024-01-01_10-00-00", mtime=old_mtime)
        # d2: recent but marked by size rule only
        d2 = _make_session(results_dir, "2024-01-02_10-00-00", mtime=2000.0)
        # d3: recent, preserved by all rules
        d3 = _make_session(results_dir, "2024-01-03_10-00-00")
        for d in (d1, d2, d3):
            _write_data(d, 1024 * 1024)  # 1 MB each  (3 MB total)
        with tempfile.TemporaryDirectory() as cfgdir:
            # age=30d marks d1; count=2 marks d1; size=1.5MB marks d1 + d2
            path = _write_log_yaml(
                cfgdir,
                results_dir=results_dir,
                max_age_days=30,
                max_count=2,
                max_size_mb=1.5,
            )
            lm = LogManager(path)
            sessions = lm._session_dirs()
            to_remove = lm._compute_removals(sessions)
            assert d1 in to_remove
            assert d2 in to_remove  # size rule alone marks this one
            assert d3 not in to_remove


###############################################################################
# Tests: cleanup
###############################################################################


def test_cleanup_noop_when_results_dir_absent() -> None:
    """``cleanup()`` does nothing when ``results_dir`` does not exist."""
    with tempfile.TemporaryDirectory() as cfgdir:
        nonexistent = os.path.join(cfgdir, "no_such_results_dir")
        path = _write_log_yaml(cfgdir, results_dir=nonexistent)
        lm = LogManager(path)
        lm.cleanup()  # must not raise


def test_cleanup_removes_and_keeps_sessions() -> None:
    """``cleanup()`` removes marked sessions and preserves the rest."""
    with tempfile.TemporaryDirectory() as results_dir:
        # 3 sessions: oldest will be removed by count rule, others kept
        d1 = _make_session(results_dir, "2024-01-01_10-00-00", mtime=1000.0)
        d2 = _make_session(results_dir, "2024-01-02_10-00-00", mtime=2000.0)
        d3 = _make_session(results_dir, "2024-01-03_10-00-00")
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(
                cfgdir, results_dir=results_dir, max_count=2
            )
            lm = LogManager(path)
            lm.cleanup()
            assert not os.path.exists(d1)  # oldest removed
            assert os.path.exists(d2)
            assert os.path.exists(d3)


###############################################################################
# Tests: new_session_dir
###############################################################################


_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def test_new_session_dir_creates_directory() -> None:
    """``new_session_dir`` creates a directory under ``results_dir``."""
    with tempfile.TemporaryDirectory() as results_dir:
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            session_path = lm.new_session_dir()
            assert os.path.isdir(session_path)


def test_new_session_dir_name_matches_format() -> None:
    """Directory name created by ``new_session_dir`` matches SESSION_FORMAT."""
    with tempfile.TemporaryDirectory() as results_dir:
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            session_path = lm.new_session_dir()
            name = os.path.basename(session_path)
            assert _SESSION_RE.match(name) is not None


def test_new_session_dir_under_results_dir() -> None:
    """``new_session_dir`` creates the directory under ``results_dir``."""
    with tempfile.TemporaryDirectory() as results_dir:
        with tempfile.TemporaryDirectory() as cfgdir:
            path = _write_log_yaml(cfgdir, results_dir=results_dir)
            lm = LogManager(path)
            session_path = lm.new_session_dir()
            assert os.path.dirname(session_path) == results_dir
