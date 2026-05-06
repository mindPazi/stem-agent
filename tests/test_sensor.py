from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.agent import Task
from src.mutator import MUTATION_OPERATORS
from src.sensor import Sensor, SensorReport


# ── SensorReport serialisation ────────────────────────────────────────────────


def test_sensor_report_loads_legacy_shape_with_defaults():
    report = SensorReport.from_dict(
        {
            "category_counts": {},
            "category_performance": {},
            "failure_patterns": [],
            "success_patterns": [],
            "suggested_mutations": [],
        }
    )

    assert report.analysis_scope == "calibration_only"
    assert report.reference_fixes_used is True


def test_sensor_report_to_from_dict_roundtrip():
    report = SensorReport(
        category_counts={"off_by_one": 3, "logic_error": 2},
        category_performance={"off_by_one": 0.5, "logic_error": 0.0},
        failure_patterns=["agent missed boundary"],
        success_patterns=["clear traceback"],
        suggested_mutations=["add_constraint", "specialize_for_category"],
    )
    restored = SensorReport.from_dict(report.to_dict())
    assert restored == report


def test_sensor_report_save_and_load(tmp_path):
    report = SensorReport(
        category_counts={"a": 1},
        category_performance={"a": 1.0},
        failure_patterns=[],
        success_patterns=[],
        suggested_mutations=[],
    )
    path = tmp_path / "report.json"
    report.save(path)
    assert path.exists()
    assert SensorReport.load(path) == report


# ── Mock LLM for Sensor.analyze ───────────────────────────────────────────────


@dataclass
class _MockResp:
    content: str
    cost_usd: float = 0.0
    usage: dict | None = None
    model: str = "mock"
    latency_ms: float = 0.0
    tool_calls: list | None = None


class _MockLLM:
    """Returns scripted responses; records messages for assertion."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict]] = []
        self.total_cost = 0.0

    def chat(self, messages, tools=None, model=None, temperature=0.0):
        self.calls.append(messages)
        if not self.responses:
            return _MockResp(content="")
        return _MockResp(content=self.responses.pop(0))

    def get_total_cost(self) -> float:
        return self.total_cost


@pytest.fixture
def temp_task_dir():
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp) / "task_x"
        td.mkdir()
        (td / "fixed.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        yield td


def _make_task(task_id: str, category: str, task_dir: Path) -> Task:
    return Task(
        task_id=task_id,
        task_dir=str(task_dir),
        buggy_code="def f():\n    return 0\n",
        description=f"bug in {task_id}",
        test_suite_code="",
        category=category,
        difficulty="easy",
    )


# ── Aggregation behaviour ─────────────────────────────────────────────────────


def test_sensor_aggregates_categories(temp_task_dir):
    tasks = [
        _make_task("t1", "off_by_one", temp_task_dir),
        _make_task("t2", "off_by_one", temp_task_dir),
        _make_task("t3", "logic_error", temp_task_dir),
    ]
    results = {"t1": True, "t2": False, "t3": False}

    llm = _MockLLM(
        responses=[
            "Agent forgot to subtract 1 from len(arr).",  # _analyze_failure(t2)
            "Agent confused the loop variable.",          # _analyze_failure(t3)
            '["clear traceback pointed to assertion"]',   # _analyze_successes
            '["add_constraint", "specialize_for_category"]',  # _suggest_mutations
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={"t2": "bad fix", "t3": ""})

    assert report.category_counts == {"off_by_one": 2, "logic_error": 1}
    assert report.category_performance["off_by_one"] == pytest.approx(0.5)
    assert report.category_performance["logic_error"] == pytest.approx(0.0)


def test_sensor_only_returns_known_operators(temp_task_dir):
    tasks = [_make_task("t1", "logic_error", temp_task_dir)]
    results = {"t1": False}

    llm = _MockLLM(
        responses=[
            "Agent picked wrong variable.",
            '["unrelated_thing", "add_constraint", "made_up_op"]',
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={"t1": ""})

    for op in report.suggested_mutations:
        assert op in MUTATION_OPERATORS


def test_sensor_handles_all_passing(temp_task_dir):
    tasks = [_make_task("t1", "off_by_one", temp_task_dir)]
    results = {"t1": True}

    llm = _MockLLM(responses=['["agent recognised the off-by-one pattern"]'])
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={})

    assert report.failure_patterns == []
    assert report.suggested_mutations == []  # nothing to fix


def test_sensor_handles_all_failing(temp_task_dir):
    tasks = [
        _make_task("t1", "off_by_one", temp_task_dir),
        _make_task("t2", "off_by_one", temp_task_dir),
    ]
    results = {"t1": False, "t2": False}

    llm = _MockLLM(
        responses=[
            "Bad fix 1.",
            "Bad fix 2.",
            '["add_exemplar", "add_constraint"]',
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={})

    assert report.success_patterns == []  # no passes
    for op in report.suggested_mutations:
        assert op in MUTATION_OPERATORS


def test_sensor_recovers_from_bad_json(temp_task_dir):
    tasks = [_make_task("t1", "off_by_one", temp_task_dir)]
    results = {"t1": False}

    llm = _MockLLM(
        responses=[
            "Boundary issue.",
            "this is not JSON at all",  # _suggest_mutations LLM call returns garbage
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={"t1": ""})

    # Heuristic fallback always includes specialize_for_category + add_constraint
    assert "specialize_for_category" in report.suggested_mutations


def test_sensor_strips_markdown_fences(temp_task_dir):
    tasks = [_make_task("t1", "off_by_one", temp_task_dir)]
    results = {"t1": False}

    llm = _MockLLM(
        responses=[
            "boundary failure",
            '```json\n["add_constraint"]\n```',
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={"t1": ""})

    assert "add_constraint" in report.suggested_mutations


def test_sensor_dedupes_failure_patterns(temp_task_dir):
    tasks = [
        _make_task("t1", "off_by_one", temp_task_dir),
        _make_task("t2", "off_by_one", temp_task_dir),
    ]
    results = {"t1": False, "t2": False}

    # Identical pattern from both failed tasks should collapse to one entry
    llm = _MockLLM(
        responses=[
            "Same pattern.",
            "Same pattern.",
            '["passes_were_clear"]',
            '["add_constraint"]',
        ]
    )
    sensor = Sensor(llm_client=llm)
    report = sensor.analyze(tasks, results, agent_fixes={})

    assert report.failure_patterns == ["Same pattern."]
