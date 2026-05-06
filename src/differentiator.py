from __future__ import annotations

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
from .utils import append_jsonl, now_iso, save_json

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

        log_dir.mkdir(parents=True, exist_ok=True)

    def run(self, initial_config: AgentConfig) -> DifferentiationResult:
        """Run the full differentiation loop. Returns the final champion."""
        champion = initial_config.clone()

        logger.info("Evaluating initial champion on dev+vital sets…")
        champion_results = self._evaluate(champion)
        champion_score = self._dev_score(champion_results)

        history: list[MutationRecord] = []
        champion_history: list[dict] = [
            {
                "iteration": 0,
                "score": champion_score,
                "config": champion.to_dict(),
                "timestamp": now_iso(),
            }
        ]

        logger.info("Differentiation start. Champion score: %.3f", champion_score)

        converged = False
        for iteration in range(self.max_iterations):
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
                # Persist champion immediately so crashes don't lose it
                champion.save(self.log_dir / "champion.yaml")
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

    def _evaluate(self, config: AgentConfig) -> dict[str, bool]:
        """Evaluate config on dev + vital tasks. Returns task_id -> passed."""
        all_ids = list(dict.fromkeys(self.dev_task_ids + self.vital_task_ids))

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

        tasks_to_eval = [self.tasks[tid] for tid in all_ids if tid in self.tasks]
        agent = BugFixAgent(config, self.llm)
        results = evaluate_split(agent, tasks_to_eval)
        return {tid: r.passed for tid, r in results.items() if tid in all_ids}

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
