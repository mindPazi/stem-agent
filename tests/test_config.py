from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.config import (
    APPROACHES,
    AVAILABLE_TOOLS,
    DEFAULT_CONFIG,
    DEFAULT_MODEL,
    OUTPUT_FORMATS,
    TOOL_USE_STRATEGIES,
    AgentConfig,
    FewShotExample,
)


def test_default_config_fields():
    cfg = DEFAULT_CONFIG
    assert cfg.approach == "direct"
    assert cfg.temperature == 0.0
    assert cfg.model == DEFAULT_MODEL
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


def test_config_declares_valid_choice_sets():
    assert "direct" in APPROACHES
    assert "full_file" in OUTPUT_FORMATS
    assert "never" in TOOL_USE_STRATEGIES


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("approach", "unknown_approach", "Invalid approach"),
        ("output_format", "markdown", "Invalid output_format"),
        ("tool_use_strategy", "sometimes", "Invalid tool_use_strategy"),
        ("max_iterations", 0, "max_iterations"),
        ("temperature", 1.1, "temperature"),
    ],
)
def test_config_rejects_invalid_values(field: str, value: object, message: str):
    with pytest.raises(ValueError, match=message):
        AgentConfig(**{field: value})


def test_config_rejects_unknown_tools():
    with pytest.raises(ValueError, match="Unknown enabled_tools"):
        AgentConfig(enabled_tools=["read_file", "not_a_tool"])


def test_config_rejects_duplicate_tools():
    with pytest.raises(ValueError, match="duplicates"):
        AgentConfig(enabled_tools=["read_file", "read_file"])
