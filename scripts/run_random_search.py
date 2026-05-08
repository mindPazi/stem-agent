#!/usr/bin/env python3
"""
Run random search baseline on BugsInPy tasks.

This is the differentiation loop with sensor_report=None and
vital_threshold=0, producing a control for the stem agent's
sensor-guided search and safeguard mechanism.

Prerequisites
-------------
- benchmark/splits.json must exist
- results/baselines/vanilla_direct.json must exist

Outputs
-------
results/random_search/differentiation_log.jsonl
results/random_search/champion_history.json
results/random_search/final_champion.yaml
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bugsinpy_loader import (
    DEFAULT_BUGSINPY_ROOT,
    DEFAULT_CACHE_ROOT,
    DEFAULT_WORKSPACE_ROOT,
    load_bugsinpy_task,
)
from src.config import DEFAULT_MODEL, AgentConfig
from src.differentiator import Differentiator
from src.llm_client import LLMClient
from src.mutator import Mutator
from src.safeguard import Safeguard
from src.utils import load_env_file, load_json, save_json, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Run random search baseline on BugsInPy")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-iterations", type=int, default=15)
    parser.add_argument("--min-improvement", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    parser.add_argument("--baselines-dir", default="results/baselines")
    parser.add_argument("--output-dir", default="results/random_search")
    parser.add_argument("--bugsinpy-root", default=str(DEFAULT_BUGSINPY_ROOT))
    args = parser.parse_args()

    setup_logging()

    if not args.api_key and not args.dry_run:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key (or use --dry-run)")

    splits_path = Path(args.splits_path)
    if not splits_path.exists():
        sys.exit(f"ERROR: {splits_path} not found; run run_baselines.py first")

    splits = load_json(splits_path)
    dev_ids: list[str] = splits["dev"]
    vital_ids: list[str] = splits["vital_signs"]
    calib_ids: list[str] = splits["calibration"]

    logger.info(
        "Splits loaded: dev=%d  vital_signs=%d  calibration=%d  test=%d",
        len(dev_ids), len(vital_ids), len(calib_ids), len(splits.get("test", [])),
    )

    vanilla_path = Path(args.baselines_dir) / "vanilla_direct.json"
    solved_calib_ids: list[str] = []
    if vanilla_path.exists():
        vd = load_json(vanilla_path)
        solved_calib_ids = [
            tid for tid in calib_ids
            if vd.get("results", {}).get(tid, {}).get("passed", False)
        ]

    bugsinpy_root = Path(args.bugsinpy_root)
    all_needed_ids = list(dict.fromkeys(dev_ids + vital_ids + calib_ids))
    task_map = {}
    for tid in all_needed_ids:
        project, bug_id = tid.split(":", 1)
        try:
            task = load_bugsinpy_task(
                project, bug_id, bugsinpy_root,
                DEFAULT_WORKSPACE_ROOT, DEFAULT_CACHE_ROOT,
            )
            task_map[tid] = task
        except Exception as exc:
            logger.warning("Failed to load %s: %s", tid, exc)

    logger.info("Loaded %d/%d BugsInPy tasks", len(task_map), len(all_needed_ids))

    solved_calib_tasks = [task_map[tid] for tid in solved_calib_ids if tid in task_map]

    initial = AgentConfig()

    llm = LLMClient(
        api_key=args.api_key or "dry-run-key",
        default_model=args.model,
        log_dir=Path(args.output_dir),
    )
    rng = random.Random(args.seed)
    mutator = Mutator(rng=rng)
    safeguard = Safeguard(vital_tasks=vital_ids, threshold=0.0)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    initial.save(output_dir / "initial_config.yaml")

    differentiator = Differentiator(
        llm_client=llm,
        mutator=mutator,
        safeguard=safeguard,
        tasks=task_map,
        dev_task_ids=dev_ids,
        vital_task_ids=vital_ids,
        log_dir=output_dir,
        sensor_report=None,
        solved_calibration_tasks=solved_calib_tasks,
        max_iterations=args.max_iterations,
        min_improvement=args.min_improvement,
        rng=rng,
        dry_run=args.dry_run,
        max_workers=args.max_workers,
    )

    logger.info(
        "Starting random search: max_iterations=%d  no sensor, no safeguard",
        args.max_iterations,
    )
    result = differentiator.run(initial)

    accepted = sum(1 for r in result.history if r.accepted)

    summary = {
        "final_score": result.final_score,
        "total_iterations": result.total_iterations,
        "converged": result.converged,
        "accepted_mutations": accepted,
        "total_cost_usd": result.total_cost_usd,
        "model": args.model,
        "max_iterations": args.max_iterations,
        "vital_threshold": 0.0,
        "sensor_report": None,
        "dry_run": args.dry_run,
        "benchmark": "bugsinpy",
        "variant": "random_search",
    }
    save_json(output_dir / "differentiation_summary.json", summary)

    logger.info("\n=== Random Search Summary ===")
    logger.info("  Final dev score   : %.3f", result.final_score)
    logger.info("  Total iterations  : %d", result.total_iterations)
    logger.info("  Converged         : %s", result.converged)
    logger.info("  Accepted          : %d", accepted)
    logger.info("  Total API cost    : $%.4f", result.total_cost_usd)


if __name__ == "__main__":
    main()
