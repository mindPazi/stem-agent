from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .config import APPROACHES, AVAILABLE_TOOLS, OUTPUT_FORMATS, AgentConfig, FewShotExample
from .convergence import MutationRecord

if TYPE_CHECKING:
    from .agent import Task
    from .llm_client import LLMClient
    from .sensor import SensorReport

logger = logging.getLogger(__name__)

# ── Public registry ───────────────────────────────────────────────────────────

MUTATION_OPERATORS: dict[str, str] = {
    "add_exemplar": "Add a few-shot example from a solved calibration task",
    "remove_exemplar": "Remove a few-shot example (reduces prompt length)",
    "rephrase_system": "Rewrite system prompt preserving semantics (LLM-assisted)",
    "add_constraint": "Add a specific debugging instruction to the system prompt",
    "remove_constraint": "Remove the last appended constraint from the system prompt",
    "specialize_for_category": "Inject category-specific guidance for the worst bug category",
    "enable_tool": "Enable an additional tool for the inner agent",
    "disable_tool": "Disable one of the currently enabled tools",
    "switch_approach": "Cycle the reasoning approach (direct->cot->react->plan_execute)",
    "adjust_iterations": "Increase or decrease max_iterations by 1–2",
    "switch_output_format": "Cycle the output format (full_file->diff->function_only)",
    "adjust_temperature": "Nudge temperature by ±0.1",
}

_APPROACH_CYCLE = list(APPROACHES)
_OUTPUT_FORMAT_CYCLE = list(OUTPUT_FORMATS)

# Predefined constraint sentences the mutator can inject/remove
_CONSTRAINTS = [
    "Always check for off-by-one errors in loop bounds and array indices.",
    "Handle edge cases explicitly: empty collections, None, zero, and negative values.",
    "Verify every comparison operator (<, <=, >, >=) against the intended invariant.",
    "Use the minimal change that makes all tests pass — do not refactor.",
    "Check for integer vs float division issues.",
    "Confirm that the return type matches the expected output of the function.",
    "Look for missing base cases in recursive functions.",
    "Double-check variable names for subtle confusion (e.g., i vs j, left vs right).",
]

# Hints injected by specialize_for_category
_CATEGORY_HINTS: dict[str, str] = {
    "off_by_one": (
        "FOCUS — OFF-BY-ONE: check loop bounds carefully. "
        "Use `< len(arr)` not `<= len(arr)`, "
        "`range(n)` not `range(n+1)`, `high = len(arr)-1` not `high = len(arr)`."
    ),
    "wrong_variable": (
        "FOCUS — WRONG VARIABLE: trace each expression and verify the correct "
        "variable is used.  Look for subtle naming confusion (e.g., `i`/`j`, `left`/`right`)."
    ),
    "missing_check": (
        "FOCUS — MISSING CHECK: add guards for empty collections, None, zero, "
        "and negative numbers before performing operations."
    ),
    "logic_error": (
        "FOCUS — LOGIC ERROR: trace the algorithm with a concrete example step by step. "
        "Verify the control flow matches the specification."
    ),
    "type_error": (
        "FOCUS — TYPE ERROR: check integer vs float division, str vs bytes, "
        "and ensure types match across assignments."
    ),
    "api_misuse": (
        "FOCUS — API MISUSE: verify the correct method name, parameter order, "
        "and return-value usage."
    ),
    "boundary": (
        "FOCUS — BOUNDARY: test mentally with first element, last element, "
        "single-element, and empty input."
    ),
    "other": (
        "FOCUS: read the test assertions carefully to understand the exact expected behaviour "
        "before proposing a fix."
    ),
}


# ── Context passed to each operator ──────────────────────────────────────────

@dataclass
class MutationContext:
    sensor_report: SensorReport | None
    iteration: int
    mutation_history: list[MutationRecord]
    # Tasks from calibration split that vanilla solved — used by add_exemplar
    solved_calibration_tasks: list[Task] = field(default_factory=list)
    llm_client: LLMClient | None = None
    rng: random.Random = field(default_factory=lambda: random.Random(42))


# ── Mutator ───────────────────────────────────────────────────────────────────

class Mutator:
    """
    Applies mutation operators to AgentConfig instances.

    Sampling strategy (by iteration):
      0–5   : 70% sensor-suggested operators, 30% random
      6–15  : uniform random from all applicable operators
      16+   : targeted (operators related to worst-performing categories)

    Anti-oscillation: operators that were rejected in the last 3 iterations
    are excluded from the candidate pool (unless no others are available).
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random(42)

    # ── Public API ────────────────────────────────────────────────────────────

    def sample_mutations(
        self,
        config: AgentConfig,
        context: MutationContext,
    ) -> list[str]:
        """Return a list of 1–2 operator names to apply this iteration."""
        n = context.rng.choices([1, 2], weights=[0.7, 0.3])[0]

        applicable = self._applicable_operators(config)
        if not applicable:
            return []

        # Anti-oscillation filter
        recently_rejected = self._recently_rejected(context.mutation_history, window=3)
        available = [op for op in applicable if op not in recently_rejected]
        if not available:
            available = applicable  # relax if everything was recently rejected

        # Sampling strategy
        chosen: list[str] = []

        if context.iteration <= 5 and context.sensor_report:
            chosen = self._sample_sensor_guided(available, context, n)
        elif context.iteration >= 16 and context.sensor_report:
            chosen = self._sample_targeted(available, context, n)
        else:
            chosen = self._sample_random(available, n, context.rng)

        return chosen

    def apply(
        self,
        config: AgentConfig,
        mutation_name: str,
        context: MutationContext,
    ) -> AgentConfig:
        """Apply a single named operator and return a new config."""
        dispatch = {
            "add_exemplar": self._op_add_exemplar,
            "remove_exemplar": self._op_remove_exemplar,
            "rephrase_system": self._op_rephrase_system,
            "add_constraint": self._op_add_constraint,
            "remove_constraint": self._op_remove_constraint,
            "specialize_for_category": self._op_specialize_for_category,
            "enable_tool": self._op_enable_tool,
            "disable_tool": self._op_disable_tool,
            "switch_approach": self._op_switch_approach,
            "adjust_iterations": self._op_adjust_iterations,
            "switch_output_format": self._op_switch_output_format,
            "adjust_temperature": self._op_adjust_temperature,
        }
        fn = dispatch.get(mutation_name)
        if fn is None:
            raise ValueError(f"Unknown mutation operator: {mutation_name}")
        result = fn(config, context)
        logger.debug("Applied %s: config changed=%s", mutation_name, result != config)
        return result

    def apply_mutations(
        self,
        config: AgentConfig,
        mutation_names: list[str],
        context: MutationContext,
    ) -> AgentConfig:
        """Apply a sequence of operators, each to the result of the previous."""
        result = config.clone()
        for name in mutation_names:
            result = self.apply(result, name, context)
        return result

    # ── Sampling helpers ──────────────────────────────────────────────────────

    def _applicable_operators(self, config: AgentConfig) -> list[str]:
        ops = list(MUTATION_OPERATORS.keys())
        filtered = []
        for op in ops:
            if op == "remove_exemplar" and not config.few_shot_examples:
                continue
            if op == "disable_tool" and not config.enabled_tools:
                continue
            if op == "enable_tool" and set(config.enabled_tools) >= set(AVAILABLE_TOOLS):
                continue
            if op == "adjust_iterations" and config.approach not in ("react", "plan_execute"):
                continue
            filtered.append(op)
        return filtered

    @staticmethod
    def _recently_rejected(
        history: list[MutationRecord], window: int = 3
    ) -> set[str]:
        rejected: set[str] = set()
        for record in history[-window:]:
            if not record.accepted:
                rejected.update(record.mutation_names)
        return rejected

    def _sample_sensor_guided(
        self,
        available: list[str],
        context: MutationContext,
        n: int,
    ) -> list[str]:
        assert context.sensor_report is not None
        sensor_ops = set(context.sensor_report.suggested_mutations) & set(available)
        other_ops = [op for op in available if op not in sensor_ops]
        rng = context.rng

        chosen: list[str] = []
        for _ in range(n):
            remaining_avail = [op for op in available if op not in chosen]
            if not remaining_avail:
                break
            sensor_remaining = [op for op in sensor_ops if op not in chosen]
            other_remaining = [op for op in other_ops if op not in chosen]
            if sensor_remaining and (not other_remaining or rng.random() < 0.70):
                chosen.append(rng.choice(sensor_remaining))
            elif other_remaining:
                chosen.append(rng.choice(other_remaining))
            elif sensor_remaining:
                chosen.append(rng.choice(sensor_remaining))
        return chosen

    def _sample_targeted(
        self,
        available: list[str],
        context: MutationContext,
        n: int,
    ) -> list[str]:
        """Target operators linked to worst-performing categories."""
        assert context.sensor_report is not None
        perf = context.sensor_report.category_performance
        if not perf:
            return self._sample_random(available, n, context.rng)

        worst_cats = sorted(perf, key=perf.get)[:2]
        targeted: list[str] = []
        for cat in worst_cats:
            if cat in _CATEGORY_HINTS:
                targeted.extend(["specialize_for_category", "add_constraint"])
            if any(c in ("off_by_one", "boundary", "missing_check") for c in worst_cats):
                targeted.append("add_exemplar")

        targeted_avail = list(dict.fromkeys(
            op for op in targeted if op in available
        ))
        if targeted_avail:
            return self._sample_random(targeted_avail, n, context.rng)
        return self._sample_random(available, n, context.rng)

    @staticmethod
    def _sample_random(pool: list[str], n: int, rng: random.Random) -> list[str]:
        if not pool:
            return []
        return rng.sample(pool, min(n, len(pool)))

    # ── Operator implementations ──────────────────────────────────────────────

    def _op_add_exemplar(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        if len(config.few_shot_examples) >= 5:
            return config
        if not context.solved_calibration_tasks:
            return config

        task = context.rng.choice(context.solved_calibration_tasks)

        # Avoid duplicating an example we already have
        existing_sources = {ex.source_task for ex in config.few_shot_examples}
        if task.task_id in existing_sources:
            candidates = [t for t in context.solved_calibration_tasks
                          if t.task_id not in existing_sources]
            if not candidates:
                return config
            task = context.rng.choice(candidates)

        fixed_path = Path(task.task_dir) / "fixed.py"
        if not fixed_path.exists():
            return config
        correct_fix = fixed_path.read_text(encoding="utf-8")

        # Optionally generate a brief reasoning trace
        reasoning = ""
        if context.llm_client:
            try:
                resp = context.llm_client.chat(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are a Python expert. In exactly 1-2 sentences, "
                                "explain what the bug was and why the fix is correct."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Buggy:\n```python\n{task.buggy_code[:400]}\n```\n\n"
                                f"Fixed:\n```python\n{correct_fix[:400]}\n```"
                            ),
                        },
                    ],
                    temperature=0.0,
                )
                reasoning = resp.content.strip()[:300]
            except Exception as e:
                logger.debug("add_exemplar reasoning generation failed: %s", e)

        example = FewShotExample(
            buggy_code=task.buggy_code[:800],
            test_error="",
            reasoning=reasoning,
            fix=correct_fix[:800],
            source_task=task.task_id,
        )
        new_config = config.clone()
        new_config.few_shot_examples = config.few_shot_examples + [example]
        return new_config

    def _op_remove_exemplar(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        if not config.few_shot_examples:
            return config
        new_config = config.clone()
        # Remove a random example
        idx = context.rng.randrange(len(new_config.few_shot_examples))
        new_config.few_shot_examples = (
            new_config.few_shot_examples[:idx] + new_config.few_shot_examples[idx + 1:]
        )
        return new_config

    def _op_rephrase_system(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        if not context.llm_client:
            return config
        try:
            resp = context.llm_client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the following system prompt using different wording. "
                            "Preserve ALL requirements and instructions. "
                            "Return ONLY the rewritten prompt — no preamble."
                        ),
                    },
                    {"role": "user", "content": config.system_prompt},
                ],
                temperature=0.7,
            )
            new_config = config.clone()
            new_config.system_prompt = resp.content.strip()
            return new_config
        except Exception as e:
            logger.debug("rephrase_system failed: %s", e)
            return config

    def _op_add_constraint(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        # Pick a constraint not already in the prompt
        candidates = [c for c in _CONSTRAINTS if c not in config.system_prompt]
        if not candidates:
            return config
        constraint = context.rng.choice(candidates)
        new_config = config.clone()
        new_config.system_prompt = config.system_prompt.rstrip() + "\n" + constraint
        return new_config

    def _op_remove_constraint(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        # Remove any constraint sentence that was previously injected
        present = [c for c in _CONSTRAINTS if c in config.system_prompt]
        if not present:
            return config
        to_remove = context.rng.choice(present)
        new_config = config.clone()
        new_config.system_prompt = new_config.system_prompt.replace(
            "\n" + to_remove, ""
        ).replace(to_remove, "").strip()
        return new_config

    def _op_specialize_for_category(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        # Determine target category: worst-performing if sensor report available
        if context.sensor_report and context.sensor_report.category_performance:
            perf = context.sensor_report.category_performance
            category = min(perf, key=perf.get)
        else:
            category = context.rng.choice(list(_CATEGORY_HINTS.keys()))

        hint = _CATEGORY_HINTS.get(category, _CATEGORY_HINTS["other"])
        if hint in config.system_prompt:
            # Already specialized for this category — try another
            other_cats = [c for c in _CATEGORY_HINTS if _CATEGORY_HINTS[c] not in config.system_prompt]
            if not other_cats:
                return config
            category = context.rng.choice(other_cats)
            hint = _CATEGORY_HINTS[category]

        new_config = config.clone()
        new_config.system_prompt = config.system_prompt.rstrip() + f"\n\n{hint}"
        return new_config

    def _op_enable_tool(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        disabled = [t for t in AVAILABLE_TOOLS if t not in config.enabled_tools]
        if not disabled:
            return config
        tool = context.rng.choice(disabled)
        new_config = config.clone()
        new_config.enabled_tools = config.enabled_tools + [tool]
        # Switching to a tool-using strategy if not already
        if new_config.tool_use_strategy == "never":
            new_config.tool_use_strategy = "always"
        if new_config.approach == "direct":
            new_config.approach = "react"
            new_config.max_iterations = max(new_config.max_iterations, 3)
        return new_config

    def _op_disable_tool(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        if not config.enabled_tools:
            return config
        tool = context.rng.choice(config.enabled_tools)
        new_config = config.clone()
        new_config.enabled_tools = [t for t in config.enabled_tools if t != tool]
        if not new_config.enabled_tools:
            new_config.tool_use_strategy = "never"
            if new_config.approach in ("react", "plan_execute"):
                new_config.approach = "cot"
                new_config.max_iterations = 1
        return new_config

    def _op_switch_approach(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        current_idx = (
            _APPROACH_CYCLE.index(config.approach)
            if config.approach in _APPROACH_CYCLE
            else 0
        )
        next_approach = _APPROACH_CYCLE[(current_idx + 1) % len(_APPROACH_CYCLE)]
        new_config = config.clone()
        new_config.approach = next_approach

        if next_approach in ("react", "plan_execute"):
            if not new_config.enabled_tools:
                new_config.enabled_tools = ["get_traceback"]
                new_config.tool_use_strategy = "always"
            new_config.max_iterations = max(new_config.max_iterations, 3)
        else:
            # direct / cot don't loop
            new_config.max_iterations = 1

        return new_config

    def _op_adjust_iterations(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        delta = context.rng.choice([-2, -1, 1, 2])
        new_val = max(1, min(10, config.max_iterations + delta))
        if new_val == config.max_iterations:
            return config
        new_config = config.clone()
        new_config.max_iterations = new_val
        return new_config

    def _op_switch_output_format(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        current_idx = (
            _OUTPUT_FORMAT_CYCLE.index(config.output_format)
            if config.output_format in _OUTPUT_FORMAT_CYCLE
            else 0
        )
        next_fmt = _OUTPUT_FORMAT_CYCLE[(current_idx + 1) % len(_OUTPUT_FORMAT_CYCLE)]
        new_config = config.clone()
        new_config.output_format = next_fmt
        return new_config

    def _op_adjust_temperature(
        self, config: AgentConfig, context: MutationContext
    ) -> AgentConfig:
        delta = context.rng.choice([-0.1, 0.1])
        new_val = round(max(0.0, min(1.0, config.temperature + delta)), 1)
        if new_val == config.temperature:
            return config
        new_config = config.clone()
        new_config.temperature = new_val
        return new_config
