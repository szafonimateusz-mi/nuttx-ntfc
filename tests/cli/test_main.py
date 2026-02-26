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

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from ntfc.cli.main import load_config_files, update_nested_dict


class MockEnvironment:
    """Mock Click environment for testing."""

    def __init__(self, confpath: str):
        self.confpath = confpath
        self.loops = 1
        self.verbose = False
        self.jsonconf = None
        self.rebuild = False
        self.flash = False


def test_load_config_files_single_file():
    """Test loading a single YAML file."""
    yaml_file = "./tests/resources/nuttx/sim/config.yaml"

    ctx = MockEnvironment(yaml_file)
    conf, conf_json = load_config_files(ctx)

    assert conf is not None
    assert "config" in conf
    assert "product" in conf
    assert conf["config"]["loops"] == 1


def test_load_config_files_directory():
    """Test loading and merging YAML files from a directory."""
    config_dir = "./tests/resources/yaml_configs"

    ctx = MockEnvironment(config_dir)
    conf, conf_json = load_config_files(ctx)

    assert conf is not None
    assert "config" in conf
    assert "product" in conf

    # Check files were merged in alphabetical order
    assert conf["config"]["name"] == "base_config"
    # Overridden in 03-overrides.yaml
    assert conf["config"]["debug"] is True
    # Added in 02-multicore.yaml
    assert conf["product"]["cores"]["core1"]["name"] == "cpu1"


def test_load_config_files_directory_with_invalid_yaml():
    """Test that invalid YAML files are skipped gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create valid file
        valid_yaml = Path(tmpdir) / "01-valid.yaml"
        with open(valid_yaml, "w") as f:
            yaml.safe_dump(
                {
                    "config": {"valid": True},
                    "product": {
                        "name": "test",
                        "cores": {"core0": {"name": "main"}},
                    },
                },
                f,
            )

        # Create invalid file that will be skipped
        invalid_yaml = Path(tmpdir) / "02-invalid.yaml"
        with open(invalid_yaml, "w") as f:
            f.write("invalid: yaml: [")

        ctx = MockEnvironment(tmpdir)
        conf, conf_json = load_config_files(ctx)

        # Valid files should be loaded, invalid skipped
        assert conf["config"]["valid"] is True


def test_update_nested_dict():
    """Test merging of nested dictionaries."""
    dict1 = {
        "config": {"debug": False, "timeout": 30},
        "level1": {"level2": {"value": "old", "keep": "preserved"}},
    }
    dict2 = {
        "config": {"debug": True, "verbose": True},
        "level1": {"level2": {"value": "new"}, "new_key": "added"},
    }

    result = update_nested_dict(dict1, dict2)

    # Original values preserved if not overridden
    assert result["config"]["timeout"] == 30
    # Overridden values
    assert result["config"]["debug"] is True
    # New values added
    assert result["config"]["verbose"] is True
    # Deep nesting preserved and merged
    assert result["level1"]["level2"]["value"] == "new"
    assert result["level1"]["level2"]["keep"] == "preserved"
    assert result["level1"]["new_key"] == "added"


def test_load_config_files_empty_directory():
    """Test loading from directory with no valid YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MockEnvironment(tmpdir)
        with pytest.raises(IOError):
            load_config_files(ctx)


def test_load_config_files_json_args_override_and_add():
    """JSON session args override YAML config values and add new ones."""
    yaml_file = "./tests/resources/nuttx/sim/config.yaml"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmpjson:
        json.dump(
            {
                "module": {},
                "args": {
                    "timeout": 321,
                    "new_option": "from_json",
                    "loops": 7,
                    "kv": {"CONFIG_FOO": "y"},
                },
            },
            tmpjson,
        )
        json_path = tmpjson.name

    try:
        ctx = MockEnvironment(yaml_file)
        ctx.jsonconf = json_path
        conf, conf_json = load_config_files(ctx)

        assert conf_json["args"]["timeout"] == 321
        assert conf["config"]["timeout"] == 321
        assert conf["config"]["new_option"] == "from_json"
        assert conf["config"]["loops"] == 7
        assert conf["config"]["kv"] == {"CONFIG_FOO": "y"}
    finally:
        Path(json_path).unlink()


def test_load_config_files_json_args_ignored_if_not_object():
    """Non-object JSON args does not modify YAML config."""
    yaml_file = "./tests/resources/nuttx/sim/config.yaml"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmpjson:
        json.dump({"args": ["timeout", 100]}, tmpjson)
        json_path = tmpjson.name

    try:
        ctx = MockEnvironment(yaml_file)
        ctx.jsonconf = json_path
        conf, _conf_json = load_config_files(ctx)

        assert conf["config"]["loops"] == 1
        assert "timeout" not in conf["config"]
    finally:
        Path(json_path).unlink()
