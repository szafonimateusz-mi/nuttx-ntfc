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

"""Tests for NTFC signal plugin."""

import signal
import sys
import time
from types import SimpleNamespace

import pytest

from ntfc.pytest.signal_plugin import SignalPlugin


def test_sigusr1_handler_without_product(capsys):
    plugin = SignalPlugin()
    pytest.product = None

    plugin._sigusr1_handler(0, None)
    out = capsys.readouterr().out
    assert "[ntfc] signal SIGUSR1" in out
    assert "pytest.product not available" in out


def test_sigusr1_handler_with_product(capsys):
    plugin = SignalPlugin()
    product = SimpleNamespace(
        sendCommand=lambda *_args, **_kwargs: "ps-output"
    )
    pytest.product = product

    plugin._sigusr1_handler(0, None)
    out = capsys.readouterr().out
    assert "executing device 'ps' command" in out
    assert "ps-output" in out


def test_sigusr1_handler_send_command_error(capsys):
    plugin = SignalPlugin()

    def raise_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    pytest.product = SimpleNamespace(sendCommand=raise_error)

    plugin._sigusr1_handler(0, None)
    out = capsys.readouterr().out
    assert "ps command failed" in out


def test_sigusr2_handler(capsys):
    plugin = SignalPlugin()
    called = {"count": 0}

    def force_panic():
        called["count"] += 1
        return True

    pytest.product = SimpleNamespace(force_panic=force_panic)

    plugin._sigusr2_handler(0, None)
    out = capsys.readouterr().out
    assert "[ntfc] signal SIGUSR2" in out
    assert "[ntfc] Force Panic" in out
    assert called["count"] == 1


def test_sigquit_handler_calls_previous(monkeypatch, capsys):
    plugin = SignalPlugin()
    called = {"count": 0}

    def prev(_signum, _frame):
        called["count"] += 1

    plugin._previous[signal.SIGQUIT] = prev  # type: ignore[name-defined]

    monkeypatch.setattr(
        plugin, "_dump_system_info", lambda: None, raising=True
    )
    monkeypatch.setattr(
        plugin, "_dump_process_info", lambda: None, raising=True
    )
    monkeypatch.setattr(
        plugin, "_dump_all_threads", lambda: None, raising=True
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.faulthandler.dump_traceback",
        lambda *args, **kwargs: None,
        raising=True,
    )

    plugin._sigquit_handler(signal.SIGQUIT, None)
    out = capsys.readouterr().out
    assert "[ntfc] signal SIGQUIT" in out
    assert called["count"] == 1


def test_sigquit_handler_no_previous_and_faulthandler_error(
    monkeypatch, capsys
):
    plugin = SignalPlugin()
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.faulthandler.dump_traceback",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        raising=True,
    )
    monkeypatch.setattr(
        plugin, "_dump_system_info", lambda: None, raising=True
    )
    monkeypatch.setattr(
        plugin, "_dump_process_info", lambda: None, raising=True
    )
    monkeypatch.setattr(
        plugin, "_dump_all_threads", lambda: None, raising=True
    )

    plugin._sigquit_handler(signal.SIGQUIT, None)
    out = capsys.readouterr().out
    assert "[ntfc] debug dump completed." in out


def test_format_helpers():
    plugin = SignalPlugin()

    def sample(a, b):
        local = "value"
        frame = sys._getframe()
        info = plugin._format_frame_info(frame, level=1)
        assert "Frame [CURRENT]" in info
        assert "Variables" in info
        assert "Arguments" in info
        assert "local=" in info
        assert local == "value"

    sample(1, "x")


def test_format_local_vars_sensitive_and_truncation():
    plugin = SignalPlugin()
    plugin._max_variables_per_frame = 1

    fake_frame = SimpleNamespace(
        f_locals={
            "password": "secret",
            "extra": "value",
        }
    )
    output = plugin._format_local_vars(fake_frame, is_main=True)
    assert any("REDACTED" in item for item in output)
    assert any("...(more variables)" in item for item in output)


def test_format_local_vars_bad_repr():
    plugin = SignalPlugin()
    plugin._max_variables_per_frame = 5

    class BadRepr:
        def __repr__(self):
            raise RuntimeError("nope")

    fake_frame = SimpleNamespace(f_locals={"obj": BadRepr(), "extra": "value"})
    output = plugin._format_local_vars(fake_frame, is_main=True)
    assert any("non-displayable" in item for item in output)


def test_format_arguments_handles_repr_error():
    plugin = SignalPlugin()

    class BadRepr:
        def __repr__(self):
            raise RuntimeError("nope")

    fake_code = SimpleNamespace(co_argcount=1, co_varnames=("arg",))
    fake_frame = SimpleNamespace(f_code=fake_code, f_locals={"arg": BadRepr()})
    args = plugin._format_arguments(fake_frame)
    assert any("non-displayable" in item for item in args)


def test_format_arguments_missing_arg():
    plugin = SignalPlugin()
    fake_code = SimpleNamespace(co_argcount=1, co_varnames=("arg",))
    fake_frame = SimpleNamespace(f_code=fake_code, f_locals={"x": 1})
    args = plugin._format_arguments(fake_frame)
    assert args == []


def test_format_frame_info_stack_continues():
    plugin = SignalPlugin()
    plugin._max_stack_depth = 0
    info = plugin._format_frame_info(sys._getframe(), level=0)
    assert "stack continues beyond" in info


def test_format_frame_info_open_error():
    plugin = SignalPlugin()
    fake_code = SimpleNamespace(
        co_name="fake",
        co_filename="missing-file",
        co_argcount=0,
        co_varnames=(),
    )
    fake_frame = SimpleNamespace(
        f_code=fake_code, f_lineno=1, f_back=None, f_locals={}
    )
    info = plugin._format_frame_info(fake_frame, level=0)
    assert "Frame [CURRENT]" in info


def test_format_frame_info_line_out_of_range():
    plugin = SignalPlugin()
    fake_code = SimpleNamespace(
        co_name="fake",
        co_filename=__file__,
        co_argcount=0,
        co_varnames=(),
    )
    fake_frame = SimpleNamespace(
        f_code=fake_code, f_lineno=100000, f_back=None, f_locals={}
    )
    info = plugin._format_frame_info(fake_frame, level=0)
    assert "File:" in info


def test_dump_system_and_process_info(monkeypatch, capsys):
    class DummyProc:
        pid = 123

        def status(self):
            return "running"

        def create_time(self):
            return time.time() - 5

        def memory_info(self):
            return SimpleNamespace(rss=1024 * 1024)

        def threads(self):
            return [1, 2]

        def num_fds(self):
            return 10

        def children(self):
            return []

    dummy = SimpleNamespace(
        Process=lambda: DummyProc(),
        virtual_memory=lambda: SimpleNamespace(percent=50.0),
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.psutil", dummy, raising=True
    )

    plugin = SignalPlugin()
    plugin._dump_system_info()
    plugin._dump_process_info()

    err = capsys.readouterr().err
    assert "System Information" in err
    assert "Process Information" in err


def test_dump_all_threads(capsys):
    plugin = SignalPlugin()
    plugin._dump_all_threads()
    err = capsys.readouterr().err
    assert "Thread Dump" in err


def test_dump_all_threads_without_enumerate(monkeypatch, capsys):
    plugin = SignalPlugin()
    frame = sys._getframe()
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.sys._current_frames",
        lambda: {123: frame},
        raising=True,
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.threading.main_thread",
        lambda: SimpleNamespace(ident=123),
        raising=True,
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.threading.enumerate",
        lambda: [],
        raising=True,
    )

    plugin._dump_all_threads()
    err = capsys.readouterr().err
    assert "Thread Dump" in err


def test_dump_all_threads_without_match(monkeypatch, capsys):
    plugin = SignalPlugin()
    frame = sys._getframe()
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.sys._current_frames",
        lambda: {123: frame},
        raising=True,
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.threading.main_thread",
        lambda: SimpleNamespace(ident=123),
        raising=True,
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.threading.enumerate",
        lambda: [SimpleNamespace(ident=999, name="Other")],
        raising=True,
    )

    plugin._dump_all_threads()
    err = capsys.readouterr().err
    assert "Thread Dump" in err


def test_dump_process_info_num_fds_error(monkeypatch, capsys):
    class DummyProc:
        pid = 123

        def status(self):
            return "running"

        def create_time(self):
            return time.time() - 5

        def memory_info(self):
            return SimpleNamespace(rss=1024 * 1024)

        def threads(self):
            return [1, 2]

        def num_fds(self):
            raise OSError("no fds")

        def children(self):
            return [SimpleNamespace(pid=456)]

    dummy = SimpleNamespace(Process=lambda: DummyProc())
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.psutil", dummy, raising=True
    )

    plugin = SignalPlugin()
    plugin._dump_process_info()
    err = capsys.readouterr().err
    assert "Children" in err


def test_dump_system_info_virtual_memory_error(monkeypatch, capsys):
    dummy = SimpleNamespace(
        virtual_memory=lambda: (_ for _ in ()).throw(RuntimeError("no mem"))
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.psutil", dummy, raising=True
    )
    plugin = SignalPlugin()
    plugin._dump_system_info()
    err = capsys.readouterr().err
    assert "System Information" in err


def test_install_restore_handlers(monkeypatch):
    plugin = SignalPlugin()
    handlers = {}

    def fake_signal(sig, handler):
        prev = handlers.get(sig)
        handlers[sig] = handler
        return prev

    def fake_getsignal(sig):
        return handlers.get(sig)

    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.signal.signal", fake_signal, raising=True
    )
    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.signal.getsignal",
        fake_getsignal,
        raising=True,
    )

    plugin._install()
    assert plugin._installed is True

    plugin._restore()
    assert plugin._installed is False


def test_install_not_main_thread(monkeypatch, capsys):
    plugin = SignalPlugin()

    class DummyThread:
        pass

    monkeypatch.setattr(
        "ntfc.pytest.signal_plugin.threading.current_thread",
        lambda: DummyThread(),
        raising=True,
    )
    plugin._install()
    out = capsys.readouterr().out
    assert "not in main thread" in out


def test_install_without_signal_attributes(monkeypatch):
    plugin = SignalPlugin()
    monkeypatch.delattr(signal, "SIGUSR1", raising=False)
    monkeypatch.delattr(signal, "SIGUSR2", raising=False)
    monkeypatch.delattr(signal, "SIGQUIT", raising=False)
    plugin._install()
    assert plugin._installed is True


def test_restore_when_not_installed():
    plugin = SignalPlugin()
    plugin._restore()
