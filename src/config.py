from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FewShotExample:
    buggy_code: str
    test_error: str
    reasoning: str
    fix: str
    source_task: str


@dataclass
class AgentConfig:
    # Prompt
    system_prompt: str = (
        "You are an expert Python developer. Fix the bug in the provided code. "
        "Return only the corrected Python code, no explanation."
    )
    few_shot_examples: list[FewShotExample] = field(default_factory=list)
    reasoning_instruction: str = ""
    output_format: str = "full_file"  # "diff" | "full_file" | "function_only"

    # Tools
    enabled_tools: list[str] = field(default_factory=list)
    tool_use_strategy: str = "never"  # "always" | "on_failure" | "never"

    # Strategy
    approach: str = "direct"  # "direct" | "cot" | "react" | "plan_execute"
    max_iterations: int = 1

    # Inference
    temperature: float = 0.0
    model: str = "gpt-4o-mini"

    def clone(self) -> AgentConfig:
        return deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        data = dict(data)
        raw_examples = data.pop("few_shot_examples", [])
        examples = [FewShotExample(**ex) for ex in raw_examples]
        return cls(few_shot_examples=examples, **data)

    @classmethod
    def from_yaml(cls, path: Path) -> AgentConfig:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentConfig):
            return NotImplemented
        return self.to_dict() == other.to_dict()


AVAILABLE_TOOLS: list[str] = [
    "read_file",
    "run_tests",
    "search_code",
    "get_ast",
    "get_diff",
    "list_functions",
    "get_traceback",
]

DEFAULT_CONFIG = AgentConfig(
    system_prompt=(
        "You are an expert Python developer. Fix the bug in the provided code. "
        "Return only the corrected Python code, no explanation."
    ),
    few_shot_examples=[],
    reasoning_instruction="",
    output_format="full_file",
    enabled_tools=[],
    tool_use_strategy="never",
    approach="direct",
    max_iterations=1,
    temperature=0.0,
    model="gpt-4o-mini",
)
