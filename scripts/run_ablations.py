#!/usr/bin/env python3
"""
Run ablation variants of the stem agent on BugsInPy tasks.

Two mandatory ablations:
- no_sensor:    differentiation without sensor guidance (sensor_report=None)
- no_safeguard: differentiation without vital-signs safeguard (threshold=0)

Prerequisites
-------------
- benchmark/splits.json
- results/baselines/vanilla_direct.json
- results/sensor/sensor_report.json (used by no_safeguard only)

Outputs
-------
results/no_sensor/final_champion.yaml
results/no_safeguard/final_champion.yaml
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from pathlib import Path

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
from src.sensor import SensorReport
from src.utils import load_env_file, load_json, save_json, setup_logging

logger = logging.getLogger(__name__)


def _load_tasks_and_splits(args):
    splits = load_json(Path(args.splits_path))
    dev_ids = splits["dev"]
    vital_ids = splits["vital_signs"]
    calib_ids = splits["calibration"]

    vanilla_path = Path(args.baselines_dir) / "vanilla_direct.json"
    solved_calib_ids = []
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

    solved_calib_tasks = [task_map[tid] for tid in solved_calib_ids if tid in task_map]
    return splits, task_map, dev_ids, vital_ids, solved_calib_tasks


def _run_variant(
    name: str,
    args,
    task_map: dict,
    dev_ids: list[str],
    vital_ids: list[str],
    solved_calib_tasks: list,
    sensor_report,
    vital_threshold: float,
    output_dir: Path,
    max_workers: int = 1,
):
    llm = LLMClient(
        api_key=args.api_key or "dry-run-key",
        default_model=args.model,
        log_dir=output_dir,
    )
    rng = random.Random(args.seed)
    mutator = Mutator(rng=rng)
    safeguard = Safeguard(vital_tasks=vital_ids, threshold=vital_threshold)

    output_dir.mkdir(parents=True, exist_ok=True)
    initial = AgentConfig()
    initial.save(output_dir / "initial_config.yaml")

    differentiator = Differentiator(
        llm_client=llm,
        mutator=mutator,
        safeguard=safeguard,
        tasks=task_map,
        dev_task_ids=dev_ids,
        vital_task_ids=vital_ids,
        log_dir=output_dir,
        sensor_report=sensor_report,
        solved_calibration_tasks=solved_calib_tasks,
        max_iterations=args.max_iterations,
        min_improvement=args.min_improvement,
        rng=rng,
        dry_run=args.dry_run,
        max_workers=max_workers,
    )

    logger.info("Starting %s: max_iterations=%d  max_workers=%d", name, args.max_iterations, max_workers)
    result = differentiator.run(initial)

    accepted = sum(1 for r in result.history if r.accepted)
    safeguard_rejections = sum(1 for r in result.history if r.reason == "safeguard")

    summary = {
        "variant": name,
        "final_score": result.final_score,
        "total_iterations": result.total_iterations,
        "converged": result.converged,
        "accepted_mutations": accepted,
        "safeguard_rejections": safeguard_rejections,
        "total_cost_usd": result.total_cost_usd,
        "model": args.model,
        "benchmark": "bugsinpy",
    }
    save_json(output_dir / "differentiation_summary.json", summary)

    logger.info(
        "%s done: score=%.3f  iterations=%d  accepted=%d  cost=$%.4f",
        name, result.final_score, result.total_iterations, accepted, result.total_cost_usd,
    )


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Run ablation variants on BugsInPy")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-iterations", type=int, default=15)
    parser.add_argument("--min-improvement", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    parser.add_argument("--baselines-dir", default="results/baselines")
    parser.add_argument("--sensor-dir", default="results/sensor")
    parser.add_argument("--bugsinpy-root", default=str(DEFAULT_BUGSINPY_ROOT))
    parser.add_argument(
        "--variants", nargs="+", default=["no_sensor", "no_safeguard"],
        choices=["no_sensor", "no_safeguard"],
    )
    args = parser.parse_args()

    setup_logging()

    if not args.api_key and not args.dry_run:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key (or use --dry-run)")

    splits, task_map, dev_ids, vital_ids, solved_calib_tasks = _load_tasks_and_splits(args)
    logger.info("Loaded %d tasks for ablations", len(task_map))

    sensor_report = None
    sensor_path = Path(args.sensor_dir) / "sensor_report.json"
    if sensor_path.exists():
        sensor_report = SensorReport.load(sensor_path)

    for variant in args.variants:
        if variant == "no_sensor":
            _run_variant(
                name="no_sensor",
                args=args,
                task_map=task_map,
                dev_ids=dev_ids,
                vital_ids=vital_ids,
                solved_calib_tasks=solved_calib_tasks,
                sensor_report=None,
                vital_threshold=1.0,
                output_dir=Path("results/no_sensor"),
                max_workers=args.max_workers,
            )
        elif variant == "no_safeguard":
            _run_variant(
                name="no_safeguard",
                args=args,
                task_map=task_map,
                dev_ids=dev_ids,
                vital_ids=vital_ids,
                solved_calib_tasks=solved_calib_tasks,
                sensor_report=sensor_report,
                vital_threshold=0.0,
                output_dir=Path("results/no_safeguard"),
                max_workers=args.max_workers,
            )


if __name__ == "__main__":
    main()
