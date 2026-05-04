"""Quick smoke test: verifies the pipeline runs end-to-end on 3 tasks."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import BugFixAgent
from src.config import DEFAULT_CONFIG
from src.evaluator import compute_pass_at_1, evaluate_split, load_tasks_from_dir
from src.llm_client import LLMClient
from src.tools import TOOL_FUNCTIONS
from src.utils import setup_logging

setup_logging()

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set. Set it to run the smoke test.")
    sys.exit(1)

benchmark_dir = Path(__file__).parent.parent / "benchmark" / "tasks"
all_tasks = load_tasks_from_dir(benchmark_dir)
tasks = all_tasks[:3]

print(f"Running smoke test on {len(tasks)} tasks: {[t.task_id for t in tasks]}")

client = LLMClient(api_key=api_key, log_dir=Path("results"))
cfg = DEFAULT_CONFIG.clone()
agent = BugFixAgent(cfg, client, TOOL_FUNCTIONS)

results = evaluate_split(agent, tasks)
pass_rate = compute_pass_at_1(results)

print(f"\nResults:")
for tid, r in results.items():
    print(f"  {tid}: {'PASS' if r.passed else 'FAIL'} (cost=${r.agent_result.cost_usd:.4f})")

print(f"\npass@1 = {pass_rate:.2f}")
print(f"Total cost = ${client.get_total_cost():.4f}")
print(f"\nSmoke test complete. Pipeline is functional.")
