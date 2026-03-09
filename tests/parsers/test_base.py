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

"""Tests for ntfc.parsers.base."""

from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import MagicMock, patch

from ntfc.parsers.base import AbstractTestParser
from ntfc.parsers.base import TestItem as _Item
from ntfc.parsers.base import TestResult as _Result

###############################################################################
# Concrete stub
###############################################################################


class ConcreteParser(AbstractTestParser):
    """Minimal concrete implementation used only in tests."""

    def __init__(
        self,
        core,
        binary,
        test_name=None,
        elf_items=None,
        device_items=None,
    ):
        super().__init__(core, binary, test_name)
        self._elf_items_val = elf_items if elf_items is not None else []
        self._device_items_val = (
            device_items if device_items is not None else []
        )

    def _discover_from_elf(self, elf_parser) -> List[_Item]:
        return self._elf_items_val

    def _discover_from_device(self) -> List[_Item]:
        return self._device_items_val

    def run_single(self, test_name=None) -> _Result:
        return _Result(name=test_name or "", passed=True)

    def run_all(self) -> Dict[str, _Result]:
        return {}

    def run_filtered(self, filter) -> Dict[str, _Result]:  # noqa: A002
        return {}


def _make_core(elf_path: str = "") -> SimpleNamespace:
    conf = SimpleNamespace(elf_path=elf_path)
    return SimpleNamespace(conf=conf)


def test_testitem_name_only():
    item = _Item(name="test_foo")
    assert item.name == "test_foo"
    assert item.suite is None


def test_testitem_with_suite():
    item = _Item(name="Suite.test_foo", suite="Suite")
    assert item.suite == "Suite"


def test_testresult_minimal():
    r = _Result(name="test_foo", passed=True)
    assert r.passed is True
    assert r.output == ""
    assert r.duration is None


def test_testresult_full():
    r = _Result(name="t", passed=False, output="err", duration=1.5)
    assert r.passed is False
    assert r.output == "err"
    assert r.duration == 1.5


def test_concrete_parser_stub_methods():
    core = _make_core()
    p = ConcreteParser(core, "bin")
    result = p.run_single("test_foo")
    assert result.name == "test_foo"
    assert p.run_all() == {}
    assert p.run_filtered("*") == {}


def test_parser_init_and_test_name():
    core = _make_core()
    p = ConcreteParser(core, "my_binary", test_name="test_foo")
    assert p.test_name == "test_foo"


def test_parser_test_name_none():
    core = _make_core()
    p = ConcreteParser(core, "my_binary")
    assert p.test_name is None


def test_get_tests_no_elf_path():
    core = _make_core(elf_path="")
    items = [_Item(name="test_a"), _Item(name="test_b")]
    p = ConcreteParser(core, "bin", device_items=items)
    result = p.get_tests()
    assert result == items


def test_get_tests_elf_hits(tmp_path):
    elf_file = tmp_path / "nuttx"
    elf_file.write_bytes(b"\x7fELF" + b"\x00" * 60)

    core = _make_core(elf_path=str(elf_file))
    elf_items = [_Item(name="elf_test")]
    p = ConcreteParser(core, "bin", elf_items=elf_items)

    with patch("ntfc.lib.elf.elf_parser.ElfParser") as mock_elf:
        mock_elf.return_value = MagicMock()
        result = p.get_tests()

    assert result == elf_items


def test_get_tests_elf_empty_falls_back_to_device(tmp_path):
    elf_file = tmp_path / "nuttx"
    elf_file.write_bytes(b"\x7fELF" + b"\x00" * 60)

    core = _make_core(elf_path=str(elf_file))
    device_items = [_Item(name="dev_test")]
    p = ConcreteParser(core, "bin", elf_items=[], device_items=device_items)

    with patch("ntfc.lib.elf.elf_parser.ElfParser") as mock_elf:
        mock_elf.return_value = MagicMock()
        result = p.get_tests()

    assert result == device_items


def test_get_tests_elf_attribute_error_falls_back_to_device():
    core = _make_core(elf_path="/non/existent/nuttx")
    device_items = [_Item(name="dev_test")]
    p = ConcreteParser(core, "bin", device_items=device_items)

    with patch(
        "ntfc.lib.elf.elf_parser.ElfParser",
        side_effect=AttributeError("bad elf"),
    ):
        result = p.get_tests()

    assert result == device_items


def test_get_tests_filter_applied():
    core = _make_core(elf_path="")
    items = [
        _Item(name="test_foo"),
        _Item(name="test_bar"),
        _Item(name="other"),
    ]
    p = ConcreteParser(core, "bin", device_items=items)
    result = p.get_tests(filter="test_*")
    assert len(result) == 2
    assert all(i.name.startswith("test_") for i in result)


def test_get_tests_filter_none_returns_all():
    core = _make_core(elf_path="")
    items = [_Item(name="a"), _Item(name="b")]
    p = ConcreteParser(core, "bin", device_items=items)
    result = p.get_tests(filter=None)
    assert result == items


def test_get_result_found():
    core = _make_core()
    p = ConcreteParser(core, "bin")
    p._results["test_foo"] = _Result(name="test_foo", passed=True)
    assert p.get_result("test_foo") is not None
    assert p.get_result("test_foo").passed is True


def test_get_result_not_found():
    core = _make_core()
    p = ConcreteParser(core, "bin")
    assert p.get_result("missing") is None
