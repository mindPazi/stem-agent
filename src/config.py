from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

DEFAULT_MODEL = "gpt-5.4-mini-2026-03-17"

APPROACHES = ("direct", "cot", "react", "plan_execute")
OUTPUT_FORMATS = ("full_file", "diff", "function_only")
TOOL_USE_STRATEGIES = ("always", "on_failure", "never")

Approach = Literal["direct", "cot", "react", "plan_execute"]
OutputFormat = Literal["diff", "full_file", "function_only"]
ToolUseStrategy = Literal["always", "on_failure", "never"]

AVAILABLE_TOOLS: list[str] = [
    "read_file",
    "run_tests",
    "search_code",
    "get_ast",
    "get_diff",
    "list_functions",
    "get_traceback",
]


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
    output_format: OutputFormat = "full_file"

    # Tools
    enabled_tools: list[str] = field(default_factory=list)
    tool_use_strategy: ToolUseStrategy = "never"

    # Strategy
    approach: Approach = "direct"
    max_iterations: int = 1

    # Inference
    temperature: float = 0.0
    model: str = DEFAULT_MODEL

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.approach not in APPROACHES:
            raise ValueError(
                f"Invalid approach: {self.approach!r}. Expected one of {APPROACHES}."
            )
        if self.output_format not in OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format: {self.output_format!r}. Expected one of {OUTPUT_FORMATS}."
            )
        if self.tool_use_strategy not in TOOL_USE_STRATEGIES:
            raise ValueError(
                "Invalid tool_use_strategy: "
                f"{self.tool_use_strategy!r}. Expected one of {TOOL_USE_STRATEGIES}."
            )
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1.")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0.")

        unknown_tools = [tool for tool in self.enabled_tools if tool not in AVAILABLE_TOOLS]
        if unknown_tools:
            raise ValueError(f"Unknown enabled_tools: {unknown_tools}.")
        if len(set(self.enabled_tools)) != len(self.enabled_tools):
            raise ValueError("enabled_tools must not contain duplicates.")

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
    model=DEFAULT_MODEL,
)
