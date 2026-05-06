#!/usr/bin/env python3
"""
Run baseline agents on all tasks and assign frozen data splits.

Outputs
-------
results/baselines/vanilla_direct.json
results/baselines/vanilla_cot.json
results/baselines/generic_react.json
results/baselines/hand_tuned.json
benchmark/splits.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import BugFixAgent
from src.baselines import make_baselines
from src.config import DEFAULT_MODEL
from src.evaluator import evaluate_split, load_tasks_from_dir
from src.llm_client import LLMClient
from src.splits import assign_splits
from src.utils import load_env_file, now_iso, save_json, setup_logging

logger = logging.getLogger(__name__)


def _serialise_results(results: dict) -> dict:
    """Convert TaskResult objects to plain dicts for JSON."""
    out: dict = {"results": {}, "pass_at_1": 0.0, "n_passed": 0, "n_total": len(results)}
    passed = 0
    for tid, result in results.items():
        out["results"][tid] = {
            "passed": result.passed,
            "duration_s": round(result.duration_s, 3),
            "cost_usd": round(
                result.agent_result.cost_usd if result.agent_result else 0.0,
                6,
            ),
            "fix": result.agent_result.fix if result.agent_result else "",
        }
        if result.passed:
            passed += 1
    out["n_passed"] = passed
    out["pass_at_1"] = passed / len(results) if results else 0.0
    return out


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Run baselines and assign frozen splits")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--baselines",
        nargs="+",
        default=["vanilla_direct", "vanilla_cot", "generic_react", "hand_tuned"],
        help="Which baselines to run",
    )
    parser.add_argument("--max-tasks", type=int, default=None, help="Limit tasks")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--benchmark-dir", default="benchmark/tasks")
    parser.add_argument("--results-dir", default="results/baselines")
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    args = parser.parse_args()

    setup_logging()

    if not args.api_key:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key")

    results_dir = Path(args.results_dir)
    splits_path = Path(args.splits_path)

    if splits_path.exists():
        logger.warning(
            "splits.json already exists at %s; skipping split assignment. "
            "Delete it manually if you need to reassign splits.",
            splits_path,
        )
        splits_exist = True
    else:
        splits_exist = False

    all_tasks = load_tasks_from_dir(args.benchmark_dir)
    if args.max_tasks:
        all_tasks = all_tasks[: args.max_tasks]
    task_map = {task.task_id: task for task in all_tasks}
    metadata = {
        task.task_id: {"category": task.category, "difficulty": task.difficulty}
        for task in all_tasks
    }

    logger.info("Loaded %d tasks from %s", len(all_tasks), args.benchmark_dir)

    llm = LLMClient(api_key=args.api_key, default_model=args.model)
    baselines = make_baselines(model=args.model)

    all_results: dict[str, dict] = {}

    for name in args.baselines:
        out_path = results_dir / f"{name}.json"
        if out_path.exists():
            logger.info("Skipping %s; results already exist at %s", name, out_path)
            with open(out_path, encoding="utf-8") as f:
                all_results[name] = json.load(f)
            continue

        if name not in baselines:
            logger.warning("Unknown baseline %s, skipping", name)
            continue

        agent = BugFixAgent(baselines[name], llm)

        logger.info("Running baseline: %s on %d tasks", name, len(all_tasks))
        raw = evaluate_split(agent, all_tasks)
        serialised = _serialise_results(raw)
        serialised["baseline"] = name
        serialised["timestamp"] = now_iso()
        serialised["model"] = args.model

        save_json(out_path, serialised)
        all_results[name] = serialised
        logger.info(
            "%s: pass@1=%.3f (%d/%d); cumulative cost=$%.4f",
            name,
            serialised["pass_at_1"],
            serialised["n_passed"],
            serialised["n_total"],
            llm.get_total_cost(),
        )

    if not splits_exist and "vanilla_direct" in all_results:
        vd = all_results["vanilla_direct"]["results"]
        vanilla_passed = {tid: info["passed"] for tid, info in vd.items()}
        solved_count = sum(vanilla_passed.values())
        logger.info(
            "Split assignment: %d solved / %d unsolved by vanilla_direct",
            solved_count,
            len(vanilla_passed) - solved_count,
        )
        splits = assign_splits(
            all_task_ids=list(task_map.keys()),
            vanilla_results=vanilla_passed,
            metadata=metadata,
            seed=args.seed,
        )
        splits["split_created_at"] = now_iso()
        splits["split_seed"] = args.seed

        save_json(splits_path, splits)
        logger.info(
            "Splits assigned and frozen at %s\n"
            "  vital_signs=%d  calibration=%d  dev=%d  test=%d",
            splits_path,
            len(splits["vital_signs"]),
            len(splits["calibration"]),
            len(splits["dev"]),
            len(splits["test"]),
        )
    elif not splits_exist:
        logger.warning("vanilla_direct results not available; cannot assign splits")

    logger.info("\n=== Baseline Summary ===")
    for name, data in all_results.items():
        logger.info(
            "  %-20s  pass@1=%.3f  (%d/%d)",
            name,
            data["pass_at_1"],
            data["n_passed"],
            data["n_total"],
        )
    logger.info("Total API cost: $%.4f", llm.get_total_cost())


if __name__ == "__main__":
    main()
