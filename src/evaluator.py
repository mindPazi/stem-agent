from __future__ import annotations

import concurrent.futures
import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .agent import AgentResult, BugFixAgent, Task

logger = logging.getLogger(__name__)

DEFAULT_BUGSINPY_ROOT = Path("C:/tmp/BugsInPy")


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


def _run_tests_bugsinpy(task: Task, agent_fix: str) -> TestResult:
    """Apply JSON edits and run BugsInPy tests via WSL."""
    from .bugsinpy_runner import evaluate_bugsinpy_fix

    repo_dir = getattr(task, "repo_dir", task.task_dir)
    t0 = time.perf_counter()
    result = evaluate_bugsinpy_fix(
        bugsinpy_root=DEFAULT_BUGSINPY_ROOT,
        repo_dir=Path(repo_dir),
        raw_fix=agent_fix,
        timeout=300,
    )
    duration = time.perf_counter() - t0
    return TestResult(
        passed=result.get("passed", False),
        stdout=result.get("test_output", ""),
        stderr=result.get("apply_error", ""),
        duration_s=duration,
    )


def _recheckout_bugsinpy_task(task: Task) -> None:
    """Re-checkout the buggy version so edits from a prior agent don't persist."""
    from .bugsinpy_loader import fast_recheckout

    project = getattr(task, "project", "")
    bug_id = getattr(task, "bug_id", "")
    if not project or not bug_id:
        return
    repo_dir = fast_recheckout(project, bug_id)
    if hasattr(task, "repo_dir"):
        task.repo_dir = str(repo_dir)
    task.task_dir = str(repo_dir)


def evaluate_task(agent: BugFixAgent, task: Task) -> TaskResult:
    logger.info("Evaluating %s (kind=%s)", task.task_id, getattr(task, "kind", "synthetic"))
    if getattr(task, "kind", "synthetic") == "bugsinpy":
        _recheckout_bugsinpy_task(task)
        from .bugsinpy_runner import compile_and_test

        repo_dir = Path(getattr(task, "repo_dir", task.task_dir))
        _, failing_output = compile_and_test(DEFAULT_BUGSINPY_ROOT, repo_dir)
        if hasattr(task, "test_output"):
            task.test_output = failing_output

    agent_result = agent.fix(task)

    if getattr(task, "kind", "synthetic") == "bugsinpy":
        test_result = _run_tests_bugsinpy(task, agent_result.fix)
    else:
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


def evaluate_split(
    agent: BugFixAgent,
    tasks: list[Task],
    max_workers: int = 1,
) -> dict[str, TaskResult]:
    """Evaluate agent on a list of tasks, optionally in parallel."""
    if max_workers <= 1:
        return {task.task_id: evaluate_task(agent, task) for task in tasks}

    results: dict[str, TaskResult] = {}

    def _eval_one(task: Task) -> tuple[str, TaskResult]:
        return task.task_id, evaluate_task(agent, task)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_eval_one, task): task.task_id for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            tid = futures[future]
            try:
                task_id, result = future.result()
                results[task_id] = result
            except Exception as exc:
                logger.error("Evaluation of %s failed: %s", tid, exc)
                results[tid] = TaskResult(
                    task_id=tid,
                    passed=False,
                    stdout="",
                    stderr=str(exc),
                    duration_s=0.0,
                )
    return results


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
        test_suite_path = task_dir / "test_suite.py"
        if not meta_path.exists() or not buggy_path.exists() or not test_suite_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        tasks.append(Task(
            task_id=meta["task_id"],
            task_dir=str(task_dir),
            buggy_code=buggy_path.read_text(encoding="utf-8"),
            description=meta.get("description", ""),
            test_suite_code=test_suite_path.read_text(encoding="utf-8"),
            category=meta.get("category", ""),
            difficulty=meta.get("difficulty", ""),
        ))
    return tasks
