#!/usr/bin/env python3
"""
Run baseline agents on BugsInPy tasks and assign frozen splits.

This is the BugsInPy counterpart of run_baselines.py. It:
1. Loads tasks from benchmark/subset.json
2. Runs each baseline agent on all tasks
3. Assigns frozen splits based on vanilla_direct results
4. Saves results to results/baselines/

Usage
-----
python scripts/run_baselines.py
python scripts/run_baselines.py --baselines vanilla_direct vanilla_cot
python scripts/run_baselines.py --max-workers 4
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.bugsinpy_loader import (
    DEFAULT_BUGSINPY_ROOT,
    DEFAULT_CACHE_ROOT,
    DEFAULT_WORKSPACE_ROOT,
    load_bugsinpy_task,
)
from src.agent import BugFixAgent
from src.baselines import make_baselines
from src.config import DEFAULT_MODEL
from src.evaluator import evaluate_task
from src.llm_client import LLMClient
from src.splits import assign_splits
from src.utils import load_env_file, now_iso, save_json, setup_logging

logger = logging.getLogger(__name__)


def _evaluate_single_bug(
    task,
    llm: LLMClient,
    config,
) -> dict:
    """Run one configured agent on a BugsInPy task and evaluate the fix."""
    agent = BugFixAgent(config, llm)
    task_result = evaluate_task(agent, task)
    agent_result = task_result.agent_result
    return {
        "passed": task_result.passed,
        "test_output": task_result.stdout[-3000:],
        "raw_fix": agent_result.fix if agent_result else "",
        "cost_usd": round(agent_result.cost_usd if agent_result else 0.0, 6),
        "duration_s": round(task_result.duration_s, 3),
        "apply_error": task_result.stderr,
    }


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Run baselines on BugsInPy and assign splits")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--baselines", nargs="+",
        default=["vanilla_direct"],
    )
    parser.add_argument("--subset-path", default="benchmark/subset.json")
    parser.add_argument("--results-dir", default="results/baselines")
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    parser.add_argument("--bugsinpy-root", default=str(DEFAULT_BUGSINPY_ROOT))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    setup_logging()

    if not args.api_key:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key")

    subset_path = Path(args.subset_path)
    if not subset_path.exists():
        sys.exit(f"ERROR: {subset_path} not found. Run build_bugsinpy_benchmark.py first.")

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    splits_path = Path(args.splits_path)
    bugsinpy_root = Path(args.bugsinpy_root)

    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d bugs from %s", len(subset), subset_path)

    # Load all tasks
    logger.info("Loading BugsInPy tasks (this involves git checkouts)...")
    tasks = []
    for entry in subset:
        project = entry["project"]
        bug_id = str(entry["bug_id"])
        try:
            task = load_bugsinpy_task(
                project, bug_id, bugsinpy_root,
                DEFAULT_WORKSPACE_ROOT, DEFAULT_CACHE_ROOT,
            )
            task.category = entry.get("category", task.category)
            task.difficulty = entry.get("difficulty", task.difficulty)
            tasks.append(task)
        except Exception as exc:
            logger.warning("Failed to load %s:%s: %s", project, bug_id, exc)

    logger.info("Loaded %d tasks successfully", len(tasks))
    task_map = {task.task_id: task for task in tasks}

    llm = LLMClient(
        api_key=args.api_key,
        default_model=args.model,
        log_dir=results_dir,
    )

    baselines = make_baselines(model=args.model)
    all_results: dict[str, dict] = {}

    for baseline_name in args.baselines:
        if baseline_name not in baselines:
            logger.warning("Unknown baseline %s, skipping", baseline_name)
            continue
        config = baselines[baseline_name]
        out_path = results_dir / f"{baseline_name}.json"
        if out_path.exists() and not args.force:
            logger.info("Skipping %s; results exist at %s", baseline_name, out_path)
            all_results[baseline_name] = json.loads(out_path.read_text(encoding="utf-8"))
            continue

        logger.info("Running baseline: %s on %d tasks", baseline_name, len(tasks))
        baseline_results: dict[str, dict] = {}
        n_passed = 0

        for task in tasks:
            if task.task_id in baseline_results:
                continue

            logger.info("  %s: evaluating %s ...", baseline_name, task.task_id)
            result = _evaluate_single_bug(task, llm, config)
            baseline_results[task.task_id] = result

            if result["passed"]:
                n_passed += 1

            logger.info(
                "  %s: %s -> %s (%d/%d so far)",
                baseline_name, task.task_id,
                "PASS" if result["passed"] else "FAIL",
                n_passed, len(baseline_results),
            )

            # Save incrementally
            data = {
                "baseline": baseline_name,
                "model": args.model,
                "timestamp": now_iso(),
                "results": baseline_results,
                "n_total": len(baseline_results),
                "n_passed": n_passed,
                "pass_at_1": n_passed / len(baseline_results) if baseline_results else 0.0,
            }
            save_json(out_path, data)

        data["total_cost_usd"] = round(llm.get_total_cost(), 6)
        save_json(out_path, data)
        all_results[baseline_name] = data
        logger.info(
            "%s complete: pass@1=%.3f (%d/%d)",
            baseline_name, data["pass_at_1"], n_passed, len(baseline_results),
        )

    # Assign splits from vanilla_direct
    if not splits_path.exists() and "vanilla_direct" in all_results:
        vd = all_results["vanilla_direct"]["results"]
        vanilla_passed = {tid: info["passed"] for tid, info in vd.items()}
        metadata = {
            task.task_id: {"category": task.category, "difficulty": task.difficulty}
            for task in tasks
        }
        splits = assign_splits(
            all_task_ids=[task.task_id for task in tasks],
            vanilla_results=vanilla_passed,
            metadata=metadata,
            seed=args.seed,
        )
        splits["split_created_at"] = now_iso()
        splits["split_seed"] = args.seed
        splits["benchmark"] = "bugsinpy"
        save_json(splits_path, splits)
        logger.info(
            "Splits assigned: vital_signs=%d  calibration=%d  dev=%d  test=%d",
            len(splits["vital_signs"]),
            len(splits["calibration"]),
            len(splits["dev"]),
            len(splits["test"]),
        )
    elif splits_path.exists():
        logger.info("Splits already exist at %s", splits_path)

    # Summary
    logger.info("\n=== BugsInPy Baseline Summary ===")
    for name, data in all_results.items():
        logger.info(
            "  %-20s  pass@1=%.3f  (%d/%d)",
            name, data.get("pass_at_1", 0), data.get("n_passed", 0), data.get("n_total", 0),
        )
    logger.info("Total API cost: $%.4f", llm.get_total_cost())


if __name__ == "__main__":
    main()
