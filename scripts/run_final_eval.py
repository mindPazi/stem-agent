#!/usr/bin/env python3
"""
Final evaluation of stem agent + all baselines on the held-out test split.

Runs the champion config, all baselines, random_search champion, and ablation
variants on the test split. Reports pass@1 with bootstrap 95% CI and
pairwise McNemar's test against vanilla_direct.

Prerequisites
-------------
- benchmark/splits.json
- results/differentiation/final_champion.yaml
- results/random_search/final_champion.yaml (optional)

Outputs
-------
results/final_eval/test_results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bugsinpy_loader import (
    DEFAULT_BUGSINPY_ROOT,
    DEFAULT_CACHE_ROOT,
    DEFAULT_WORKSPACE_ROOT,
    load_bugsinpy_task,
)
from src.agent import BugFixAgent
from src.baselines import make_baselines
from src.config import DEFAULT_MODEL, AgentConfig
from src.evaluator import evaluate_task
from src.llm_client import LLMClient
from src.utils import load_env_file, load_json, now_iso, save_json, setup_logging

logger = logging.getLogger(__name__)


def _bootstrap_ci(passed: list[bool], n_resamples: int = 10000, alpha: float = 0.05) -> tuple[float, float, float]:
    """Bootstrap 95% CI for pass@1."""
    arr = np.array(passed, dtype=float)
    mean = arr.mean()
    rng = np.random.default_rng(42)
    boot_means = np.array([
        rng.choice(arr, size=len(arr), replace=True).mean()
        for _ in range(n_resamples)
    ])
    lo = float(np.percentile(boot_means, 100 * alpha / 2))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return mean, lo, hi


def _mcnemar_p(a_passed: list[bool], b_passed: list[bool]) -> float:
    """McNemar's test p-value (two-sided). a vs b on paired tasks."""
    b_only = sum(1 for a, b in zip(a_passed, b_passed) if not a and b)
    a_only = sum(1 for a, b in zip(a_passed, b_passed) if a and not b)
    n = b_only + a_only
    if n == 0:
        return 1.0
    from scipy.stats import binomtest
    result = binomtest(b_only, n, 0.5)
    return float(result.pvalue)


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Phase 3: final BugsInPy test-split evaluation")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--splits-path", default="benchmark/splits.json")
    parser.add_argument("--champion-path", default="results/differentiation/final_champion.yaml")
    parser.add_argument("--random-search-path", default="results/random_search/final_champion.yaml")
    parser.add_argument("--output-dir", default="results/final_eval")
    parser.add_argument("--bugsinpy-root", default=str(DEFAULT_BUGSINPY_ROOT))
    parser.add_argument(
        "--agents", nargs="+",
        default=["vanilla_direct", "stem_agent"],
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    setup_logging()

    if not args.api_key:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key")

    splits = load_json(Path(args.splits_path))
    test_ids: list[str] = splits["test"]
    logger.info("Test split: %d tasks", len(test_ids))

    bugsinpy_root = Path(args.bugsinpy_root)
    test_tasks = []
    for tid in test_ids:
        project, bug_id = tid.split(":", 1)
        try:
            task = load_bugsinpy_task(
                project, bug_id, bugsinpy_root,
                DEFAULT_WORKSPACE_ROOT, DEFAULT_CACHE_ROOT,
            )
            test_tasks.append(task)
        except Exception as exc:
            logger.warning("Failed to load %s: %s", tid, exc)

    logger.info("Loaded %d/%d test tasks", len(test_tasks), len(test_ids))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClient(api_key=args.api_key, default_model=args.model, log_dir=output_dir)
    baselines = make_baselines(model=args.model)

    champion_path = Path(args.champion_path)
    random_search_path = Path(args.random_search_path)

    configs: dict[str, AgentConfig] = {}
    for name in args.agents:
        if name in baselines:
            configs[name] = baselines[name]
        elif name == "stem_agent":
            if champion_path.exists():
                configs[name] = AgentConfig.from_yaml(champion_path)
            else:
                logger.warning("Champion not found at %s, skipping stem_agent", champion_path)
        elif name == "random_search":
            if random_search_path.exists():
                configs[name] = AgentConfig.from_yaml(random_search_path)
            else:
                logger.warning("Random search champion not found at %s, skipping", random_search_path)
        elif name == "no_sensor":
            no_sensor_path = Path("results/no_sensor/final_champion.yaml")
            if no_sensor_path.exists():
                configs[name] = AgentConfig.from_yaml(no_sensor_path)
            else:
                logger.warning("no_sensor champion not found, skipping")
        elif name == "no_safeguard":
            no_sg_path = Path("results/no_safeguard/final_champion.yaml")
            if no_sg_path.exists():
                configs[name] = AgentConfig.from_yaml(no_sg_path)
            else:
                logger.warning("no_safeguard champion not found, skipping")

    all_results: dict[str, dict] = {}

    for name, config in configs.items():
        out_path = output_dir / f"{name}.json"
        if out_path.exists() and not args.force:
            logger.info("Skipping %s; results exist at %s", name, out_path)
            all_results[name] = load_json(out_path)
            continue

        logger.info("Evaluating %s on %d test tasks", name, len(test_tasks))
        agent = BugFixAgent(config, llm)
        per_task: dict[str, dict] = {}
        n_passed = 0

        for task in test_tasks:
            tr = evaluate_task(agent, task)
            per_task[task.task_id] = {
                "passed": tr.passed,
                "duration_s": round(tr.duration_s, 3),
                "cost_usd": round(tr.agent_result.cost_usd if tr.agent_result else 0.0, 6),
            }
            if tr.passed:
                n_passed += 1

            data = {
                "agent": name,
                "model": args.model,
                "timestamp": now_iso(),
                "results": per_task,
                "n_total": len(per_task),
                "n_passed": n_passed,
                "pass_at_1": n_passed / len(per_task) if per_task else 0.0,
            }
            save_json(out_path, data)

        data["total_cost_usd"] = round(llm.get_total_cost(), 6)
        save_json(out_path, data)
        all_results[name] = data

        logger.info(
            "%s: pass@1=%.3f (%d/%d)",
            name, data["pass_at_1"], n_passed, len(per_task),
        )

    # Statistical analysis
    ordered_test_ids = [t.task_id for t in test_tasks]
    stats: dict[str, dict] = {}

    vanilla_passed_list = []
    if "vanilla_direct" in all_results:
        vanilla_passed_list = [
            all_results["vanilla_direct"]["results"].get(tid, {}).get("passed", False)
            for tid in ordered_test_ids
        ]

    for name, data in all_results.items():
        passed_list = [
            data["results"].get(tid, {}).get("passed", False)
            for tid in ordered_test_ids
        ]
        mean, lo, hi = _bootstrap_ci(passed_list)
        p_val = None
        if name != "vanilla_direct" and vanilla_passed_list:
            try:
                p_val = _mcnemar_p(vanilla_passed_list, passed_list)
            except ImportError:
                logger.warning("scipy not available; skipping McNemar's test")

        stats[name] = {
            "pass_at_1": round(mean, 4),
            "ci_95_lo": round(lo, 4),
            "ci_95_hi": round(hi, 4),
            "n_passed": data["n_passed"],
            "n_total": data["n_total"],
            "mcnemar_p_vs_vanilla": round(p_val, 4) if p_val is not None else None,
            "total_cost_usd": data.get("total_cost_usd", 0.0),
        }

    save_json(output_dir / "test_results.json", {
        "stats": stats,
        "test_ids": ordered_test_ids,
        "timestamp": now_iso(),
        "model": args.model,
    })

    logger.info("\n=== Phase 3 Test Results ===")
    for name, s in stats.items():
        p_str = f"  p={s['mcnemar_p_vs_vanilla']:.4f}" if s["mcnemar_p_vs_vanilla"] is not None else ""
        logger.info(
            "  %-20s  pass@1=%.3f [%.3f, %.3f]  (%d/%d)%s",
            name, s["pass_at_1"], s["ci_95_lo"], s["ci_95_hi"],
            s["n_passed"], s["n_total"], p_str,
        )
    logger.info("Total API cost: $%.4f", llm.get_total_cost())


if __name__ == "__main__":
    main()
