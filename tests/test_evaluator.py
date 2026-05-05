from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.agent import AgentResult, Task
from src.evaluator import TaskResult, compute_pass_at_1, load_tasks_from_dir, run_tests_safely


BUGGY_FIX = "def add(a, b):\n    return a - b\n"
CORRECT_FIX = "def add(a, b):\n    return a + b\n"
TEST_CODE = "from solution import add\ndef test_add():\n    assert add(1, 2) == 3\n"


@pytest.fixture()
def task_dir(tmp_path: Path) -> Path:
    (tmp_path / "buggy.py").write_text(BUGGY_FIX, encoding="utf-8")
    (tmp_path / "test_suite.py").write_text(TEST_CODE, encoding="utf-8")
    import json
    meta = {"task_id": "task_001", "category": "logic_error", "difficulty": "easy",
            "description": "test", "source": "test"}
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def test_run_tests_safely_pass(task_dir: Path):
    result = run_tests_safely(str(task_dir), CORRECT_FIX)
    assert result.passed is True


def test_run_tests_safely_fail(task_dir: Path):
    result = run_tests_safely(str(task_dir), BUGGY_FIX)
    assert result.passed is False


def test_run_tests_safely_duration(task_dir: Path):
    result = run_tests_safely(str(task_dir), CORRECT_FIX)
    assert result.duration_s >= 0


def test_compute_pass_at_1():
    results = {
        "t1": TaskResult("t1", True, "", "", 0.1),
        "t2": TaskResult("t2", False, "", "", 0.1),
        "t3": TaskResult("t3", True, "", "", 0.1),
    }
    assert compute_pass_at_1(results) == pytest.approx(2 / 3)


def test_compute_pass_at_1_empty():
    assert compute_pass_at_1({}) == 0.0


def test_compute_pass_at_1_all_pass():
    results = {f"t{i}": TaskResult(f"t{i}", True, "", "", 0.0) for i in range(5)}
    assert compute_pass_at_1(results) == 1.0


def test_load_tasks_from_dir(tmp_path: Path):
    # Create a proper task_001 sub-directory
    import json
    task_subdir = tmp_path / "task_001"
    task_subdir.mkdir()
    (task_subdir / "buggy.py").write_text(BUGGY_FIX, encoding="utf-8")
    (task_subdir / "test_suite.py").write_text(TEST_CODE, encoding="utf-8")
    meta = {"task_id": "task_001", "category": "logic_error", "difficulty": "easy",
            "description": "test", "source": "test"}
    (task_subdir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    tasks = load_tasks_from_dir(tmp_path)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_id == "task_001"
    assert "add" in t.buggy_code
    assert TEST_CODE in t.test_suite_code
