from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .agent import AgentResult, BugFixAgent, Task

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    passed: bool
    stdout: str
    stderr: str
    duration_s: float


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    stdout: str
    stderr: str
    duration_s: float
    agent_result: AgentResult | None = None


def run_tests_safely(task_dir: str, agent_fix: str, timeout: int = 30) -> TestResult:
    """Apply agent fix to solution.py in a temp dir, run tests, return result."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        task_path = Path(task_dir)

        shutil.copy(task_path / "test_suite.py", tmpdir / "test_suite.py")
        (tmpdir / "solution.py").write_text(agent_fix, encoding="utf-8")

        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "test_suite.py", "-v", "--tb=short", "--no-header", "-q"],
                cwd=tmpdir,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            duration = time.perf_counter() - t0
            return TestResult(
                passed=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_s=duration,
            )
        except subprocess.TimeoutExpired:
            return TestResult(passed=False, stdout="", stderr="Timeout after 30s", duration_s=timeout)
        except Exception as e:
            return TestResult(passed=False, stdout="", stderr=str(e), duration_s=0.0)


def evaluate_task(agent: BugFixAgent, task: Task) -> TaskResult:
    logger.info("Evaluating %s", task.task_id)
    agent_result = agent.fix(task)
    test_result = run_tests_safely(task.task_dir, agent_result.fix)
    logger.info(
        "%s -> %s (cost=$%.4f)",
        task.task_id,
        "PASS" if test_result.passed else "FAIL",
        agent_result.cost_usd,
    )
    return TaskResult(
        task_id=task.task_id,
        passed=test_result.passed,
        stdout=test_result.stdout,
        stderr=test_result.stderr,
        duration_s=test_result.duration_s,
        agent_result=agent_result,
    )


def evaluate_split(agent: BugFixAgent, tasks: list[Task]) -> dict[str, TaskResult]:
    return {task.task_id: evaluate_task(agent, task) for task in tasks}


def compute_pass_at_1(results: dict[str, TaskResult]) -> float:
    if not results:
        return 0.0
    return sum(r.passed for r in results.values()) / len(results)


def load_tasks_from_dir(benchmark_dir: str | Path) -> list[Task]:
    """Load all tasks from benchmark/tasks/ directory."""
    import json

    benchmark_path = Path(benchmark_dir)
    tasks = []
    for task_dir in sorted(benchmark_path.glob("task_*")):
        if not task_dir.is_dir():
            continue
        meta_path = task_dir / "metadata.json"
        buggy_path = task_dir / "buggy.py"
        if not meta_path.exists() or not buggy_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        tasks.append(Task(
            task_id=meta["task_id"],
            task_dir=str(task_dir),
            buggy_code=buggy_path.read_text(encoding="utf-8"),
            description=meta.get("description", ""),
            category=meta.get("category", ""),
            difficulty=meta.get("difficulty", ""),
        ))
    return tasks
