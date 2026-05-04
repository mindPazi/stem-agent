from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.config import AVAILABLE_TOOLS, DEFAULT_CONFIG, AgentConfig, FewShotExample


def test_default_config_fields():
    cfg = DEFAULT_CONFIG
    assert cfg.approach == "direct"
    assert cfg.temperature == 0.0
    assert cfg.model == "gpt-4o-mini"
    assert cfg.enabled_tools == []


def test_clone_is_deep_copy():
    cfg = AgentConfig(enabled_tools=["read_file"])
    clone = cfg.clone()
    clone.enabled_tools.append("run_tests")
    assert cfg.enabled_tools == ["read_file"]


def test_to_dict_roundtrip():
    cfg = AgentConfig(approach="cot", temperature=0.5)
    d = cfg.to_dict()
    assert d["approach"] == "cot"
    assert d["temperature"] == 0.5


def test_yaml_roundtrip():
    cfg = AgentConfig(
        approach="react",
        max_iterations=5,
        enabled_tools=["read_file", "run_tests"],
    )
    yaml_str = cfg.to_yaml()
    assert "react" in yaml_str

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        cfg.save(path)
        loaded = AgentConfig.from_yaml(path)
    assert loaded.approach == "react"
    assert loaded.max_iterations == 5
    assert loaded.enabled_tools == ["read_file", "run_tests"]


def test_few_shot_examples_roundtrip():
    ex = FewShotExample(
        buggy_code="x = 1 + 1",
        test_error="AssertionError",
        reasoning="The bug is ...",
        fix="x = 2",
        source_task="task_001",
    )
    cfg = AgentConfig(few_shot_examples=[ex])

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        cfg.save(path)
        loaded = AgentConfig.from_yaml(path)

    assert len(loaded.few_shot_examples) == 1
    assert loaded.few_shot_examples[0].source_task == "task_001"


def test_equality():
    a = AgentConfig(approach="cot")
    b = AgentConfig(approach="cot")
    c = AgentConfig(approach="react")
    assert a == b
    assert a != c


def test_available_tools_list():
    assert "read_file" in AVAILABLE_TOOLS
    assert "run_tests" in AVAILABLE_TOOLS
    assert len(AVAILABLE_TOOLS) == 7
