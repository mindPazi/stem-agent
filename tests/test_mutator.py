from __future__ import annotations

import random

import pytest

from src.config import AVAILABLE_TOOLS, AgentConfig
from src.convergence import MutationRecord
from src.mutator import MUTATION_OPERATORS, MutationContext, Mutator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx(iteration: int = 0, history: list | None = None) -> MutationContext:
    return MutationContext(
        sensor_report=None,
        iteration=iteration,
        mutation_history=history or [],
        solved_calibration_tasks=[],
        llm_client=None,
        rng=random.Random(0),
    )


def _react_config() -> AgentConfig:
    return AgentConfig(
        approach="react",
        enabled_tools=["get_traceback"],
        tool_use_strategy="always",
        max_iterations=3,
    )


# ── Registry ──────────────────────────────────────────────────────────────────

def test_all_operators_registered():
    assert len(MUTATION_OPERATORS) == 15


def test_operator_names_are_strings():
    for name, desc in MUTATION_OPERATORS.items():
        assert isinstance(name, str)
        assert isinstance(desc, str)


# ── apply: unknown operator raises ───────────────────────────────────────────

def test_apply_unknown_operator_raises():
    mutator = Mutator()
    config = AgentConfig()
    with pytest.raises(ValueError, match="Unknown mutation operator"):
        mutator.apply(config, "nonexistent_op", _ctx())


# ── add_constraint / remove_constraint ────────────────────────────────────────

def test_add_constraint_appends_to_prompt():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(system_prompt="Fix the bug.")
    new = mutator.apply(config, "add_constraint", _ctx())
    assert new.system_prompt != config.system_prompt
    assert len(new.system_prompt) > len(config.system_prompt)


def test_add_constraint_idempotent_when_all_added():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(system_prompt="Fix the bug.")
    # Add all constraints
    for _ in range(20):  # more than len(_CONSTRAINTS)
        config = mutator.apply(config, "add_constraint", _ctx())
    # Further application should return unchanged
    new = mutator.apply(config, "add_constraint", _ctx())
    assert new.system_prompt == config.system_prompt


def test_remove_constraint_undoes_add():
    mutator = Mutator(rng=random.Random(0))
    original = AgentConfig(system_prompt="Fix the bug.")
    with_constraint = mutator.apply(original, "add_constraint", _ctx())
    assert with_constraint.system_prompt != original.system_prompt
    removed = mutator.apply(with_constraint, "remove_constraint", _ctx())
    # Prompt should shrink back (may not be identical due to whitespace)
    assert len(removed.system_prompt) < len(with_constraint.system_prompt)


def test_remove_constraint_noop_when_none_present():
    mutator = Mutator()
    config = AgentConfig(system_prompt="A completely custom prompt with no injected constraints.")
    new = mutator.apply(config, "remove_constraint", _ctx())
    assert new.system_prompt == config.system_prompt


# ── enable_tool / disable_tool ────────────────────────────────────────────────

def test_enable_tool_adds_tool():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(enabled_tools=[])
    new = mutator.apply(config, "enable_tool", _ctx())
    assert len(new.enabled_tools) == 1
    assert new.enabled_tools[0] in AVAILABLE_TOOLS


def test_enable_tool_noop_when_all_enabled():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(enabled_tools=list(AVAILABLE_TOOLS))
    new = mutator.apply(config, "enable_tool", _ctx())
    assert new.enabled_tools == config.enabled_tools


def test_disable_tool_removes_one():
    mutator = Mutator(rng=random.Random(0))
    config = _react_config()
    new = mutator.apply(config, "disable_tool", _ctx())
    assert len(new.enabled_tools) == 0


def test_disable_tool_noop_when_none_enabled():
    mutator = Mutator()
    config = AgentConfig(enabled_tools=[])
    new = mutator.apply(config, "disable_tool", _ctx())
    assert new.enabled_tools == []


def test_enable_then_disable_roundtrip():
    mutator = Mutator(rng=random.Random(42))
    config = AgentConfig(enabled_tools=[])
    with_tool = mutator.apply(config, "enable_tool", _ctx())
    assert len(with_tool.enabled_tools) == 1
    without_tool = mutator.apply(with_tool, "disable_tool", _ctx())
    assert without_tool.enabled_tools == []


# ── switch_approach ───────────────────────────────────────────────────────────

def test_switch_approach_cycles():
    mutator = Mutator()
    config = AgentConfig(approach="direct")
    cycle = []
    for _ in range(4):
        config = mutator.apply(config, "switch_approach", _ctx())
        cycle.append(config.approach)
    assert cycle == ["cot", "react", "plan_execute", "direct"]


def test_switch_to_react_adds_default_tool_if_none():
    mutator = Mutator()
    config = AgentConfig(approach="cot", enabled_tools=[])
    new = mutator.apply(config, "switch_approach", _ctx())
    assert new.approach == "react"
    assert len(new.enabled_tools) >= 1


# ── adjust_iterations ─────────────────────────────────────────────────────────

def test_adjust_iterations_only_on_react_plan():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(approach="direct", max_iterations=1)
    applicable = mutator._applicable_operators(config)
    assert "adjust_iterations" not in applicable


def test_adjust_iterations_stays_in_bounds():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(approach="react", max_iterations=1, enabled_tools=["read_file"])
    # Lower bound: clamped to 1
    results = set()
    for seed in range(20):
        mutator.rng = random.Random(seed)
        new = mutator.apply(config, "adjust_iterations", _ctx())
        results.add(new.max_iterations)
    assert all(1 <= v <= 10 for v in results)


# ── switch_output_format ──────────────────────────────────────────────────────

def test_switch_output_format_cycles():
    mutator = Mutator()
    config = AgentConfig(output_format="full_file")
    after1 = mutator.apply(config, "switch_output_format", _ctx())
    assert after1.output_format == "diff"
    after2 = mutator.apply(after1, "switch_output_format", _ctx())
    assert after2.output_format == "function_only"
    after3 = mutator.apply(after2, "switch_output_format", _ctx())
    assert after3.output_format == "full_file"


# ── adjust_temperature ────────────────────────────────────────────────────────

def test_adjust_temperature_clamps_to_zero():
    mutator = Mutator(rng=random.Random(1))  # seed that gives delta=-0.1
    config = AgentConfig(temperature=0.0)
    # Apply many times; value must never go below 0
    for _ in range(10):
        config = mutator.apply(config, "adjust_temperature", _ctx())
    assert config.temperature >= 0.0


def test_adjust_temperature_clamps_to_one():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(temperature=1.0)
    for _ in range(10):
        config = mutator.apply(config, "adjust_temperature", _ctx())
    assert config.temperature <= 1.0


# ── specialize_for_category ───────────────────────────────────────────────────

def test_specialize_for_category_adds_hint():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig(system_prompt="Fix the bug.")
    new = mutator.apply(config, "specialize_for_category", _ctx())
    assert len(new.system_prompt) > len(config.system_prompt)


def test_specialize_for_category_noop_when_all_hints_present():
    from src.mutator import _CATEGORY_HINTS
    mutator = Mutator(rng=random.Random(0))
    # Inject all hints
    config = AgentConfig(system_prompt=" ".join(_CATEGORY_HINTS.values()))
    new = mutator.apply(config, "specialize_for_category", _ctx())
    assert new.system_prompt == config.system_prompt


# ── Mutations produce valid AgentConfig objects ───────────────────────────────

def test_every_operator_returns_valid_config():
    """Every operator must return an AgentConfig that differs from input OR is unchanged."""
    mutator = Mutator(rng=random.Random(7))
    base = AgentConfig(
        approach="react",
        enabled_tools=["get_traceback", "read_file"],
        tool_use_strategy="always",
        max_iterations=3,
        temperature=0.5,
        output_format="full_file",
    )
    for op in MUTATION_OPERATORS:
        result = mutator.apply(base.clone(), op, _ctx())
        assert isinstance(result, AgentConfig), f"Operator {op} did not return AgentConfig"


# ── Anti-oscillation: recently rejected operators are excluded ────────────────

def test_recently_rejected_excludes_operators():
    history = [
        MutationRecord(
            iteration=i,
            mutation_names=["add_constraint"],
            accepted=False,
            score_before=0.5,
            score_after=0.5,
            delta=0.0,
            reason="no_improvement",
        )
        for i in range(3)
    ]
    mutator = Mutator(rng=random.Random(0))
    rejected = mutator._recently_rejected(history, window=3)
    assert "add_constraint" in rejected


# ── sample_mutations returns 1-2 operators ────────────────────────────────────

def test_sample_mutations_returns_list():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig()
    ops = mutator.sample_mutations(config, _ctx(iteration=0))
    assert isinstance(ops, list)
    assert 1 <= len(ops) <= 2


def test_sample_mutations_all_in_registry():
    mutator = Mutator(rng=random.Random(0))
    config = AgentConfig()
    for seed in range(10):
        mutator.rng = random.Random(seed)
        ops = mutator.sample_mutations(config, _ctx())
        for op in ops:
            assert op in MUTATION_OPERATORS


# ── Config immutability: apply does not mutate input ──────────────────────────

def test_apply_does_not_mutate_original():
    mutator = Mutator(rng=random.Random(0))
    original = AgentConfig(system_prompt="Original prompt.")
    original_prompt = original.system_prompt
    mutator.apply(original, "add_constraint", _ctx())
    assert original.system_prompt == original_prompt
