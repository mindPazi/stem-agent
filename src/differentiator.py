from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .agent import BugFixAgent, Task
from .config import AgentConfig
from .convergence import MutationRecord, check_convergence
from .evaluator import evaluate_split
from .mutator import MutationContext, Mutator
from .safeguard import Safeguard
from .utils import append_jsonl, load_json, load_jsonl, now_iso, save_json

if TYPE_CHECKING:
    from .llm_client import LLMClient
    from .sensor import SensorReport

logger = logging.getLogger(__name__)


@dataclass
class DifferentiationResult:
    final_config: AgentConfig
    final_score: float
    total_iterations: int
    converged: bool
    history: list[MutationRecord]
    champion_history: list[dict]
    total_cost_usd: float


class Differentiator:
    """
    Iterative mutation-and-selection loop.

    Each iteration:
      1. Sample 1-2 mutation operators.
      2. Apply them to the current champion -> challenger.
      3. Evaluate challenger on dev + vital-signs tasks.
      4. Run safeguard; reject if vital signs fail.
      5. Accept challenger as new champion only if dev score improves by > min_improvement.
      6. Check convergence; stop early if no progress in last `window` iterations.

    All decisions are logged to `log_dir/differentiation_log.jsonl`.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        mutator: Mutator,
        safeguard: Safeguard,
        tasks: dict[str, Task],
        dev_task_ids: list[str],
        vital_task_ids: list[str],
        log_dir: Path,
        sensor_report: SensorReport | None = None,
        solved_calibration_tasks: list[Task] | None = None,
        max_iterations: int = 20,
        min_improvement: float = 0.02,
        convergence_window: int = 5,
        rng: random.Random | None = None,
        dry_run: bool = False,
        max_workers: int = 1,
    ) -> None:
        self.llm = llm_client
        self.mutator = mutator
        self.safeguard = safeguard
        self.tasks = tasks
        self.dev_task_ids = dev_task_ids
        self.vital_task_ids = vital_task_ids
        self.log_dir = log_dir
        self.sensor_report = sensor_report
        self.solved_calibration_tasks = list(solved_calibration_tasks) if solved_calibration_tasks else []
        self.max_iterations = max_iterations
        self.min_improvement = min_improvement
        self.convergence_window = convergence_window
        self.rng = rng or random.Random(42)
        self.dry_run = dry_run
        self.max_workers = max_workers

        log_dir.mkdir(parents=True, exist_ok=True)

    def run(self, initial_config: AgentConfig) -> DifferentiationResult:
        """Run the full differentiation loop. Returns the final champion."""
        resumed = self._try_resume()
        if resumed:
            champion, champion_score, history, champion_history, start_iteration = resumed
            logger.info(
                "Resumed from iteration %d. Champion score: %.3f, %d history records",
                start_iteration, champion_score, len(history),
            )
        else:
            champion = initial_config.clone()
            logger.info("Evaluating initial champion on dev+vital sets…")
            self._checkpoint_label = "initial"
            champion_results = self._evaluate(champion)
            champion_score = self._dev_score(champion_results)
            history = []
            champion_history = [
                {
                    "iteration": 0,
                    "score": champion_score,
                    "config": champion.to_dict(),
                    "timestamp": now_iso(),
                }
            ]
            start_iteration = 0

        logger.info("Differentiation start. Champion score: %.3f", champion_score)

        converged = False
        for iteration in range(start_iteration, self.max_iterations):
            context = MutationContext(
                sensor_report=self.sensor_report,
                iteration=iteration,
                mutation_history=history,
                solved_calibration_tasks=self.solved_calibration_tasks,
                # Suppress LLM-driven mutations during dry-run so we don't
                # spend tokens (or hit auth errors with a stub key)
                llm_client=None if self.dry_run else self.llm,
                rng=self.rng,
            )

            mutation_names = self.mutator.sample_mutations(champion, context)
            if not mutation_names:
                logger.warning("Iteration %d: no applicable mutations, skipping", iteration)
                continue

            logger.info("Iteration %d: trying mutations %s", iteration, mutation_names)
            challenger = self.mutator.apply_mutations(champion, mutation_names, context)

            # Evaluate challenger
            self._checkpoint_label = f"iteration_{iteration}"
            challenger_results = self._evaluate(challenger)
            challenger_score = self._dev_score(challenger_results)
            delta = challenger_score - champion_score

            # Safeguard check
            vital_results = {t: challenger_results.get(t, False) for t in self.vital_task_ids}
            guard = self.safeguard.check(vital_results)

            if not guard.is_safe:
                record = MutationRecord(
                    iteration=iteration,
                    mutation_names=mutation_names,
                    accepted=False,
                    score_before=champion_score,
                    score_after=challenger_score,
                    delta=delta,
                    reason="safeguard",
                )
                history.append(record)
                self._log(record, challenger, guard.reason)
                logger.warning(
                    "Iteration %d: REJECTED (safeguard) - %s", iteration, guard.reason
                )
                continue

            # Champion selection
            if delta > self.min_improvement:
                logger.info(
                    "Iteration %d: NEW CHAMPION %.3f -> %.3f (+%.3f) via %s",
                    iteration,
                    champion_score,
                    challenger_score,
                    delta,
                    mutation_names,
                )
                old_score = champion_score
                champion = challenger
                champion_score = challenger_score
                record = MutationRecord(
                    iteration=iteration,
                    mutation_names=mutation_names,
                    accepted=True,
                    score_before=old_score,
                    score_after=champion_score,
                    delta=delta,
                    reason="accepted",
                )
                champion_history.append(
                    {
                        "iteration": iteration + 1,
                        "score": champion_score,
                        "config": champion.to_dict(),
                        "mutations": mutation_names,
                        "timestamp": now_iso(),
                    }
                )
                champion.save(self.log_dir / "champion.yaml")
                save_json(self.log_dir / "champion_history.json", champion_history)
            else:
                record = MutationRecord(
                    iteration=iteration,
                    mutation_names=mutation_names,
                    accepted=False,
                    score_before=champion_score,
                    score_after=challenger_score,
                    delta=delta,
                    reason="no_improvement",
                )
                logger.info(
                    "Iteration %d: REJECTED (no improvement, delta=%.3f) via %s",
                    iteration,
                    delta,
                    mutation_names,
                )

            history.append(record)
            self._log(record, challenger, "")

            # Convergence check
            if check_convergence(history, window=self.convergence_window, min_delta=self.min_improvement):
                logger.info("Converged at iteration %d", iteration)
                converged = True
                break

        # Save final artefacts
        save_json(self.log_dir / "champion_history.json", champion_history)
        champion.save(self.log_dir / "final_champion.yaml")

        total_cost = self.llm.get_total_cost()
        logger.info(
            "Differentiation complete. Iterations=%d, final_score=%.3f, cost=$%.4f",
            len(history),
            champion_score,
            total_cost,
        )

        return DifferentiationResult(
            final_config=champion,
            final_score=champion_score,
            total_iterations=len(history),
            converged=converged,
            history=history,
            champion_history=champion_history,
            total_cost_usd=total_cost,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _try_resume(self) -> tuple[AgentConfig, float, list[MutationRecord], list[dict], int] | None:
        """Try to resume from a previous crashed/interrupted run."""
        log_path = self.log_dir / "differentiation_log.jsonl"
        champion_path = self.log_dir / "champion.yaml"
        history_path = self.log_dir / "champion_history.json"

        if not log_path.exists():
            return None

        raw_records = load_jsonl(log_path)
        if not raw_records:
            return None

        if not champion_path.exists():
            return None

        history = [
            MutationRecord(
                iteration=r["iteration"],
                mutation_names=r["mutation_names"],
                accepted=r["accepted"],
                score_before=r["score_before"],
                score_after=r["score_after"],
                delta=r.get("delta", 0.0),
                reason=r.get("reason", ""),
            )
            for r in raw_records
        ]

        champion = AgentConfig.from_yaml(champion_path)

        if history_path.exists():
            try:
                champion_history = load_json(history_path)
            except Exception:
                champion_history = []
        else:
            champion_history = []

        champion_score = None
        for rec in reversed(history):
            if rec.accepted:
                champion_score = rec.score_after
                break
        if champion_score is None and champion_history:
            champion_score = champion_history[-1].get("score")
        if champion_score is None:
            champion_score = history[0].score_before

        start_iteration = max(r.iteration for r in history) + 1

        return champion, champion_score, history, champion_history, start_iteration

    def _evaluate(self, config: AgentConfig) -> dict[str, bool]:
        """Evaluate config on dev + vital tasks. Returns task_id -> passed."""
        all_ids = list(dict.fromkeys(self.dev_task_ids + self.vital_task_ids))
        checkpoint_label = getattr(self, "_checkpoint_label", "evaluation")

        if self.dry_run:
            # Vital signs are tasks that vanilla already solves, so a typical
            # challenger preserves them. Default to passing on vital and
            # randomise dev so the loop exercises accept / reject / safeguard
            # paths. Occasionally fail one vital task to also exercise the
            # safeguard rejection path.
            vital_set = set(self.vital_task_ids)
            results: dict[str, bool] = {}
            for tid in all_ids:
                if tid in vital_set:
                    # 90% pass rate — keeps most iterations safe but still
                    # exercises the safeguard rejection branch.
                    results[tid] = self.rng.random() < 0.9
                else:
                    results[tid] = self.rng.random() < 0.5
            return results

        checkpoint_path = self._checkpoint_path(checkpoint_label, config)
        checkpoint = self._load_checkpoint(checkpoint_path)
        completed: dict[str, dict] = checkpoint.get("results", {})

        if completed:
            logger.info(
                "Checkpoint %s: reusing %d/%d completed task results",
                checkpoint_path.name,
                len(completed),
                len(all_ids),
            )

        results: dict[str, bool] = {}
        remaining_tasks = []
        for tid in all_ids:
            if tid in completed:
                results[tid] = bool(completed[tid]["passed"])
            else:
                task = self.tasks.get(tid)
                if task is None:
                    results[tid] = False
                    completed[tid] = {"passed": False, "duration_s": 0.0, "cost_usd": 0.0}
                else:
                    remaining_tasks.append(task)

        if not remaining_tasks:
            return results

        agent = BugFixAgent(config, self.llm)

        if remaining_tasks:
            batch_results = evaluate_split(agent, remaining_tasks, max_workers=self.max_workers)
            for tid, task_result in batch_results.items():
                completed[tid] = {
                    "passed": task_result.passed,
                    "duration_s": round(task_result.duration_s, 3),
                    "cost_usd": round(
                        task_result.agent_result.cost_usd if task_result.agent_result else 0.0,
                        6,
                    ),
                }
                results[tid] = task_result.passed

            config_dict = config.to_dict()
            save_json(checkpoint_path, {
                "label": checkpoint_label,
                "config_hash": hashlib.sha256(
                    json.dumps(config_dict, sort_keys=True, ensure_ascii=True).encode("utf-8")
                ).hexdigest()[:12],
                "config": config_dict,
                "task_ids": all_ids,
                "results": completed,
                "completed": len(completed),
                "total": len(all_ids),
                "updated_at": now_iso(),
            })
            logger.info(
                "Checkpoint %s: saved %d/%d task results",
                checkpoint_path.name,
                len(completed),
                len(all_ids),
            )

        return {tid: results.get(tid, False) for tid in all_ids}

    def _checkpoint_path(self, label: str, config: AgentConfig) -> Path:
        return self.log_dir / "checkpoints" / f"{label}_{self._config_hash(config)}.json"

    @staticmethod
    def _config_hash(config: AgentConfig) -> str:
        payload = json.dumps(config.to_dict(), sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _load_checkpoint(path: Path) -> dict:
        if not path.exists():
            return {"results": {}}
        try:
            return load_json(path)
        except Exception as exc:
            logger.warning("Ignoring unreadable checkpoint %s: %s", path, exc)
            return {"results": {}}

    def _dev_score(self, results: dict[str, bool]) -> float:
        """pass@1 on the dev set."""
        if not self.dev_task_ids:
            return 0.0
        return sum(results.get(t, False) for t in self.dev_task_ids) / len(self.dev_task_ids)

    def _log(
        self,
        record: MutationRecord,
        challenger: AgentConfig,
        note: str,
    ) -> None:
        entry = {
            **record.to_dict(),
            "note": note,
            "challenger_config": challenger.to_dict(),
            "timestamp": now_iso(),
        }
        append_jsonl(self.log_dir / "differentiation_log.jsonl", entry)
