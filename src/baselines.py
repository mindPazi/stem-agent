from __future__ import annotations

from .config import AVAILABLE_TOOLS, DEFAULT_MODEL, AgentConfig


HAND_TUNED_PROMPT = """\
You are a senior Python engineer specialised in debugging and bug repair.

TASK: Fix the MINIMAL bug in the provided code so that ALL tests pass.

PROCEDURE:
1. Call get_traceback to see exactly which test fails and what error is raised.
2. Call read_file to read the full buggy code if needed.
3. Identify the single root cause; do NOT speculate about unrelated issues.
4. Write the minimal fix (often 1-3 lines).
5. Optionally call run_tests with your proposed fix to verify before returning.
6. Return the COMPLETE fixed Python file: no markdown, no explanation.

COMMON BUG PATTERNS - check these first:
- Off-by-one: `high = len(arr)` -> `high = len(arr) - 1`; `while low <= high`.
- Wrong operator: `<` vs `<=`, `>` vs `>=`, `and` vs `or`, `+` vs `-`, `//` vs `/`.
- Missing edge case: empty list `[]`, `None`, zero `0`, negative numbers, single element.
- Wrong variable: using `i` where `j` is meant; `left`/`right` confusion.
- Type error: integer division vs float, str vs bytes.
- Missing return / wrong return value.

DISCIPLINE:
- Change the fewest lines necessary.
- Do not rename variables, add docstrings, or refactor.
- Do not add features beyond what the failing tests require.\
"""


def make_baselines(model: str = DEFAULT_MODEL) -> dict[str, AgentConfig]:
    """Return the named baseline configurations."""
    return {
        "vanilla_direct": AgentConfig(
            system_prompt="You are a Python developer. Fix the bug.",
            approach="direct",
            temperature=0.0,
            model=model,
        ),
        "vanilla_cot": AgentConfig(
            system_prompt="You are a Python developer. Fix the bug.",
            reasoning_instruction="Think step by step before writing your fix.",
            approach="cot",
            temperature=0.0,
            model=model,
        ),
        "generic_react": AgentConfig(
            system_prompt="You are a Python developer. Fix the bug.",
            approach="react",
            enabled_tools=list(AVAILABLE_TOOLS),
            tool_use_strategy="always",
            max_iterations=5,
            temperature=0.0,
            model=model,
        ),
        "hand_tuned": AgentConfig(
            system_prompt=HAND_TUNED_PROMPT,
            reasoning_instruction=(
                "Analyse the traceback, identify the root cause, then write the minimal fix."
            ),
            approach="react",
            enabled_tools=["get_traceback", "read_file", "run_tests"],
            tool_use_strategy="always",
            max_iterations=5,
            temperature=0.0,
            model=model,
        ),
    }
