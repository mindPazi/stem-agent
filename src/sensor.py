from __future__ import annotations

import concurrent.futures
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .mutator import MUTATION_OPERATORS

if TYPE_CHECKING:
    from .agent import Task
    from .llm_client import LLMClient

logger = logging.getLogger(__name__)

_OPERATOR_LIST = list(MUTATION_OPERATORS)


@dataclass
class SensorReport:
    # Bug category distribution in calibration set
    category_counts: dict[str, int]

    # Per-category pass rate on calibration set (0.0–1.0)
    category_performance: dict[str, float]

    # Free-text patterns extracted by LLM from failed tasks
    failure_patterns: list[str]

    # Free-text patterns from successful tasks
    success_patterns: list[str]

    # Mutation operator names suggested by the analysis
    suggested_mutations: list[str]

    # Sensor analysis may inspect fixed.py only for calibration diagnostics.
    analysis_scope: str = "calibration_only"
    reference_fixes_used: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> SensorReport:
        data = dict(data)
        data.setdefault("analysis_scope", "calibration_only")
        data.setdefault("reference_fixes_used", True)
        return cls(**data)

    @classmethod
    def load(cls, path: Path) -> SensorReport:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


class Sensor:
    """
    Runs once on calibration results to extract failure signals and suggest
    mutation directions for the differentiation loop.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def analyze(
        self,
        calibration_tasks: list[Task],
        results: dict[str, bool],           # task_id -> passed
        agent_fixes: dict[str, str],         # task_id -> agent's proposed fix (may be empty)
    ) -> SensorReport:
        """
        Analyze calibration results and return a SensorReport.

        LLM is called for each *failed* task to extract why it failed.
        The output is a static report; the Sensor does not re-run during
        differentiation.
        """
        # ── Category statistics ──────────────────────────────────────────────
        category_counts: dict[str, int] = {}
        category_pass: dict[str, list[bool]] = {}

        for task in calibration_tasks:
            cat = task.category or "other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
            category_pass.setdefault(cat, []).append(results.get(task.task_id, False))

        category_performance: dict[str, float] = {
            cat: sum(passes) / len(passes)
            for cat, passes in category_pass.items()
        }

        # ── Per-task LLM analysis ────────────────────────────────────────────
        failed_tasks = [t for t in calibration_tasks if not results.get(t.task_id, False)]
        passed_tasks = [t for t in calibration_tasks if results.get(t.task_id, False)]
        reference_fixes_used = any((Path(t.task_dir) / "fixed.py").exists() for t in calibration_tasks)

        logger.info(
            "Sensor: %d calibration tasks (%d failed, %d passed). "
            "Running LLM analysis on failed tasks.",
            len(calibration_tasks),
            len(failed_tasks),
            len(passed_tasks),
        )

        failure_analyses: list[dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(failed_tasks) or 1)) as pool:
            futures = {
                pool.submit(self._analyze_failure, task, agent_fixes.get(task.task_id, "")): task
                for task in failed_tasks
            }
            for future in concurrent.futures.as_completed(futures):
                analysis = future.result()
                if analysis:
                    failure_analyses.append(analysis)

        # ── Aggregate patterns ────────────────────────────────────────────────
        failure_patterns = list({a["pattern"] for a in failure_analyses if a.get("pattern")})
        success_patterns = self._analyze_successes(passed_tasks)

        # ── Generate mutation suggestions ─────────────────────────────────────
        suggested_mutations = self._suggest_mutations(
            failure_analyses, category_performance, failure_patterns
        )

        report = SensorReport(
            category_counts=category_counts,
            category_performance=category_performance,
            failure_patterns=failure_patterns,
            success_patterns=success_patterns,
            suggested_mutations=suggested_mutations,
            reference_fixes_used=reference_fixes_used,
        )
        logger.info(
            "Sensor report: %d failure patterns, %d suggested mutations: %s",
            len(failure_patterns),
            len(suggested_mutations),
            suggested_mutations,
        )
        return report

    # ── Private helpers ───────────────────────────────────────────────────────

    def _analyze_failure(self, task: Task, agent_fix: str) -> dict:
        """Ask the LLM why the agent failed on this task."""
        fixed_path = Path(task.task_dir) / "fixed.py"
        correct_fix = fixed_path.read_text(encoding="utf-8") if fixed_path.exists() else ""
        test_output = getattr(task, "test_output", "")

        prompt = (
            f"A Python bug-fixing agent failed on this task.\n\n"
            f"Category: {task.category}\n"
            f"Description: {task.description}\n\n"
            f"Failing test output:\n```\n{test_output[:1000] or '(not available)'}\n```\n\n"
            f"Buggy code:\n```python\n{task.buggy_code[:600]}\n```\n\n"
            f"Agent's fix (WRONG):\n```python\n{agent_fix[:400] or '(agent produced no valid fix)'}\n```\n\n"
            + (
                f"Correct fix:\n```python\n{correct_fix[:400]}\n```\n\n"
                if correct_fix else ""
            )
            + "In 1-2 sentences: what specific pattern caused the agent to fail? "
            "Be concrete (e.g., 'agent ignored boundary condition', 'agent changed wrong variable')."
        )

        try:
            resp = self.llm.chat(
                [
                    {"role": "system", "content": "You are a concise code-debugging analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            return {"task_id": task.task_id, "category": task.category, "pattern": resp.content.strip()}
        except Exception as e:
            logger.warning("LLM analysis failed for %s: %s", task.task_id, e)
            return {}

    def _analyze_successes(self, passed_tasks: list[Task]) -> list[str]:
        """Extract 2-3 success patterns from passed tasks via one LLM call."""
        if not passed_tasks:
            return []

        task_descs = "\n".join(
            f"- {t.task_id} ({t.category}): {t.description}" for t in passed_tasks[:10]
        )
        prompt = (
            f"A Python bug-fixing agent successfully solved these tasks:\n{task_descs}\n\n"
            "List 2-3 concrete patterns that made these tasks easy for the agent. "
            "Be specific (e.g., 'clear error message pointed to the exact line'). "
            "Return as a JSON array of strings."
        )
        try:
            resp = self.llm.chat(
                [
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            content = resp.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except Exception as e:
            logger.warning("Success pattern analysis failed: %s", e)
            return []

    def _suggest_mutations(
        self,
        failure_analyses: list[dict],
        category_performance: dict[str, float],
        failure_patterns: list[str],
    ) -> list[str]:
        """Ask LLM to suggest mutation operators based on observed failures."""
        if not failure_analyses and not failure_patterns:
            return []

        worst_cats = sorted(category_performance, key=category_performance.get)[:3]
        patterns_text = "\n".join(f"- {p}" for p in failure_patterns[:10])

        operator_list_str = "\n".join(f"  - {op}" for op in _OPERATOR_LIST)

        prompt = (
            f"A Python bug-fixing agent showed these failure patterns on a calibration set:\n"
            f"{patterns_text}\n\n"
            f"Worst-performing bug categories: {worst_cats}\n\n"
            f"Available mutation operators:\n{operator_list_str}\n\n"
            "Select 3-6 operator names from the list above that would most likely address "
            "the observed failures.  Return ONLY a JSON array of operator name strings, "
            "e.g. [\"add_exemplar\", \"specialize_for_category\"]."
        )

        try:
            resp = self.llm.chat(
                [
                    {"role": "system", "content": "Return valid JSON only. Use exactly the operator names provided."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            suggestions = json.loads(content)
            # Validate: only keep known operator names
            valid = [s for s in suggestions if s in _OPERATOR_LIST]
            return valid
        except Exception as e:
            logger.warning("Mutation suggestion failed: %s", e)
            # Fallback: heuristic suggestions based on worst categories
            fallback = ["specialize_for_category", "add_constraint"]
            if any(c in ("off_by_one", "boundary") for c in worst_cats):
                fallback.append("add_exemplar")
            return fallback
