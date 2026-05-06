#!/usr/bin/env python3
"""Run vanilla_direct across candidate models with per-task checkpointing."""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import BugFixAgent
from src.baselines import make_baselines
from src.evaluator import TaskResult, evaluate_task, load_tasks_from_dir
from src.llm_client import LLMClient
from src.utils import load_env_file, now_iso, save_json, setup_logging

logger = logging.getLogger(__name__)


def _safe_model_dir(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model)


def _serialise_task(result: TaskResult) -> dict:
    return {
        "passed": result.passed,
        "duration_s": round(result.duration_s, 3),
        "cost_usd": round(
            result.agent_result.cost_usd if result.agent_result else 0.0,
            6,
        ),
        "fix": result.agent_result.fix if result.agent_result else "",
    }


def _refresh_summary(data: dict) -> None:
    results = data.get("results", {})
    n_total = len(results)
    n_passed = sum(1 for item in results.values() if item.get("passed", False))
    data["n_total"] = n_total
    data["n_passed"] = n_passed
    data["pass_at_1"] = n_passed / n_total if n_total else 0.0
    data["updated_at"] = now_iso()


def _run_model(args: argparse.Namespace, model: str) -> None:
    out_dir = Path(args.results_dir) / _safe_model_dir(model)
    out_path = out_dir / "vanilla_direct.json"

    if out_path.exists() and not args.force:
        import json

        data = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        data = {
            "baseline": "vanilla_direct",
            "model": model,
            "created_at": now_iso(),
            "results": {},
            "n_total": 0,
            "n_passed": 0,
            "pass_at_1": 0.0,
        }

    all_tasks = load_tasks_from_dir(args.benchmark_dir)
    if args.max_tasks:
        all_tasks = all_tasks[: args.max_tasks]

    logger.info("Model %s: loaded %d tasks", model, len(all_tasks))

    llm = LLMClient(
        api_key=args.api_key,
        default_model=model,
        log_dir=out_dir,
    )
    agent = BugFixAgent(make_baselines(model=model)["vanilla_direct"], llm)

    for task in all_tasks:
        if task.task_id in data["results"] and not args.force:
            logger.info("Model %s: skipping %s (checkpoint exists)", model, task.task_id)
            continue

        last_error: Exception | None = None
        for attempt in range(1, args.max_retries + 1):
            try:
                result = evaluate_task(agent, task)
                data["results"][task.task_id] = _serialise_task(result)
                _refresh_summary(data)
                save_json(out_path, data)
                logger.info(
                    "Model %s: checkpoint %s pass@1=%.3f (%d/%d)",
                    model,
                    task.task_id,
                    data["pass_at_1"],
                    data["n_passed"],
                    data["n_total"],
                )
                break
            except Exception as exc:
                last_error = exc
                wait_s = min(args.retry_wait * attempt, args.max_retry_wait)
                logger.warning(
                    "Model %s: %s failed on attempt %d/%d: %s",
                    model,
                    task.task_id,
                    attempt,
                    args.max_retries,
                    exc,
                )
                if attempt < args.max_retries:
                    time.sleep(wait_s)
        else:
            logger.error(
                "Model %s: stopping at %s after repeated failures; progress saved at %s",
                model,
                task.task_id,
                out_path,
            )
            raise RuntimeError(f"{model} failed on {task.task_id}") from last_error

    _refresh_summary(data)
    data["completed_at"] = now_iso()
    data["total_cost_usd"] = round(llm.get_total_cost(), 6)
    save_json(out_path, data)
    logger.info(
        "Model %s complete: pass@1=%.3f (%d/%d), cost=$%.4f",
        model,
        data["pass_at_1"],
        data["n_passed"],
        data["n_total"],
        llm.get_total_cost(),
    )


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Calibrate vanilla_direct across models")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model IDs to evaluate",
    )
    parser.add_argument("--benchmark-dir", default="benchmark/tasks")
    parser.add_argument("--results-dir", default="results/model_calibration")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--retry-wait", type=float, default=2.0)
    parser.add_argument("--max-retry-wait", type=float, default=30.0)
    parser.add_argument("--force", action="store_true", help="Re-run existing task checkpoints")
    args = parser.parse_args()

    setup_logging()

    if not args.api_key:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key")

    for model in args.models:
        _run_model(args, model)


if __name__ == "__main__":
    main()
