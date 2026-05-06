#!/usr/bin/env python3
"""Assign frozen benchmark splits from an existing vanilla_direct baseline result."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluator import load_tasks_from_dir
from src.splits import assign_splits
from src.utils import load_json, now_iso, save_json, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign frozen benchmark splits")
    parser.add_argument("--benchmark-dir", default="benchmark/tasks")
    parser.add_argument("--vanilla-results", default="results/baselines/vanilla_direct.json")
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing splits file")
    args = parser.parse_args()

    setup_logging()

    splits_path = Path(args.splits_path)
    if splits_path.exists() and not args.force:
        sys.exit(f"ERROR: {splits_path} already exists. Pass --force to overwrite it.")

    vanilla_path = Path(args.vanilla_results)
    if not vanilla_path.exists():
        sys.exit(f"ERROR: {vanilla_path} not found. Run run_baselines.py first.")

    tasks = load_tasks_from_dir(args.benchmark_dir)
    metadata = {
        task.task_id: {"category": task.category, "difficulty": task.difficulty}
        for task in tasks
    }
    vanilla_data = load_json(vanilla_path)
    vanilla_passed = {
        task_id: info["passed"]
        for task_id, info in vanilla_data.get("results", {}).items()
    }

    splits = assign_splits(
        all_task_ids=[task.task_id for task in tasks],
        vanilla_results=vanilla_passed,
        metadata=metadata,
        seed=args.seed,
    )
    splits["split_created_at"] = now_iso()
    splits["split_seed"] = args.seed
    save_json(splits_path, splits)

    print(
        "Wrote "
        f"{splits_path}: vital_signs={len(splits['vital_signs'])}, "
        f"calibration={len(splits['calibration'])}, dev={len(splits['dev'])}, "
        f"test={len(splits['test'])}"
    )


if __name__ == "__main__":
    main()
