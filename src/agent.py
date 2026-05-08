from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable

from .config import AgentConfig
from .llm_client import LLMClient
from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

logger = logging.getLogger(__name__)

_RE_CODE_PYTHON = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)
_RE_CODE_GENERIC = re.compile(r"```\n?(.*?)```", re.DOTALL)


@dataclass
class Task:
    task_id: str
    task_dir: str
    buggy_code: str
    description: str
    test_suite_code: str = ""
    category: str = ""
    difficulty: str = ""
    kind: str = "synthetic"


@dataclass
class AgentResult:
    fix: str
    reasoning: str
    tool_calls: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    iterations: int = 0


class BugFixAgent:
    def __init__(
        self,
        config: AgentConfig,
        llm_client: LLMClient,
        tools: dict[str, Callable] | None = None,
    ) -> None:
        self.config = config
        self.llm = llm_client
        all_tools = tools or TOOL_FUNCTIONS
        self.tools = {name: all_tools[name] for name in config.enabled_tools if name in all_tools}
        self._enabled_schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] in self.tools] or None
    def fix(self, task: Task) -> AgentResult:
        logger.debug("Fixing task %s with approach=%s", task.task_id, self.config.approach)
        match self.config.approach:
            case "direct":
                return self._fix_direct(task)
            case "cot":
                return self._fix_cot(task)
            case "react":
                return self._fix_react(task)
            case "plan_execute":
                return self._fix_plan_execute(task)
            case _:
                raise ValueError(f"Unknown approach: {self.config.approach}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _user_prompt(self, task: Task) -> str:
        if task.kind == "bugsinpy":
            return self._user_prompt_bugsinpy(task)
        fmt_hint = {
            "diff": "Return a unified diff patch of the fix.",
            "function_only": "Return only the fixed function(s), not the entire file.",
        }.get(self.config.output_format, "Return the complete fixed Python file.")
        prompt = (
            "Fix the Python implementation so that all hidden tests pass.\n\n"
            f"Buggy code:\n```python\n{task.buggy_code}\n```"
        )
        return f"{prompt}\n\n{fmt_hint}"

    def _user_prompt_bugsinpy(self, task: Task) -> str:
        snippets = getattr(task, "snippets", {})
        changed_ranges = getattr(task, "changed_ranges", [])
        test_output = getattr(task, "test_output", "")
        project = getattr(task, "project", "")
        bug_id = getattr(task, "bug_id", "")

        snippet_text = "\n\n".join(
            f"File: {fp}\n```python\n{body}\n```" for fp, body in snippets.items()
        )
        ranges_text = "\n".join(
            "- {file}:{start_line}-{end_line}\n{buggy}".format(
                file=item["file"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                buggy="\n".join(f"  {line}" for line in item.get("buggy_lines", [])),
            )
            for item in changed_ranges
        )
        return (
            f"Fix this real BugsInPy bug.\n\n"
            f"Project: {project}\nBug id: {bug_id}\n\n"
            f"Failing test output:\n```\n{test_output[:3000]}\n```\n\n"
            f"Relevant buggy-code snippets with line numbers:\n{snippet_text}\n\n"
            f"Candidate buggy line ranges to edit:\n{ranges_text}\n\n"
            "Return only valid JSON with this exact shape:\n"
            '{"edits":[{"file":"path/to/file.py","start_line":1,"end_line":1,'
            '"replacement":"replacement line 1\\nreplacement line 2"}]}\n'
            "The replacement must contain the full corrected text for the selected "
            "inclusive line range. Do not include markdown or explanation."
        )

    def _base_messages(self, task: Task) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": self.config.system_prompt}]
        for ex in self.config.few_shot_examples:
            messages.append({
                "role": "user",
                "content": (
                    f"Buggy code:\n```python\n{ex.buggy_code}\n```\n\n"
                    "Return the complete fixed Python file."
                ),
            })
            body = f"{ex.reasoning}\n\n```python\n{ex.fix}\n```" if ex.reasoning else f"```python\n{ex.fix}\n```"
            messages.append({"role": "assistant", "content": body})
        messages.append({"role": "user", "content": self._user_prompt(task)})
        return messages

    @staticmethod
    def _extract_code(content: str) -> str:
        m = _RE_CODE_PYTHON.search(content)
        if m:
            return m.group(1).strip()
        m = _RE_CODE_GENERIC.search(content)
        if m:
            return m.group(1).strip()
        return content.strip()

    def _postprocess_fix(self, content: str, task: Task) -> str:
        if task.kind == "bugsinpy":
            return content.strip()
        return self._extract_code(content)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _fix_direct(self, task: Task) -> AgentResult:
        messages = self._base_messages(task)
        resp = self.llm.chat(messages, temperature=self.config.temperature, model=self.config.model)
        return AgentResult(
            fix=self._postprocess_fix(resp.content, task),
            reasoning="",
            cost_usd=resp.cost_usd,
            iterations=1,
        )

    def _fix_cot(self, task: Task) -> AgentResult:
        messages = self._base_messages(task)
        instr = self.config.reasoning_instruction or "Think step by step before writing the fix."
        messages[-1]["content"] += f"\n\n{instr}"
        resp = self.llm.chat(messages, temperature=self.config.temperature, model=self.config.model)
        return AgentResult(
            fix=self._postprocess_fix(resp.content, task),
            reasoning=resp.content,
            cost_usd=resp.cost_usd,
            iterations=1,
        )

    def _fix_react(self, task: Task) -> AgentResult:
        if not self.tools:
            logger.warning(
                "react approach called with no enabled tools on task %s; falling back to direct",
                task.task_id,
            )
            return self._fix_direct(task)
        messages = self._base_messages(task)
        if task.kind == "bugsinpy":
            messages[-1]["content"] += (
                "\n\nYou have tools to inspect repository files. "
                "Use them only if needed, then return the JSON edits requested above."
            )
        else:
            messages[-1]["content"] += (
                "\n\nYou have tools to inspect and test the code. "
                "Use them to understand the bug, then return the complete fixed Python file."
            )
        tool_log: list[dict] = []
        total_cost = 0.0

        for iteration in range(self.config.max_iterations):
            resp = self.llm.chat(
                messages,
                tools=self._enabled_schemas,
                temperature=self.config.temperature,
                model=self.config.model,
            )
            total_cost += resp.cost_usd

            if resp.tool_calls:
                # Append assistant message with tool_calls
                messages.append({
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in resp.tool_calls
                    ],
                })
                for tc in resp.tool_calls:
                    tool_log.append(tc)
                    fn = self.tools.get(tc["name"])
                    if fn:
                        try:
                            result = fn(task.task_dir, **tc["arguments"])
                        except Exception as e:
                            result = f"Tool error: {e}"
                    else:
                        result = f"Unknown tool: {tc['name']}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(result),
                    })
            else:
                return AgentResult(
                    fix=self._postprocess_fix(resp.content, task),
                    reasoning=resp.content,
                    tool_calls=tool_log,
                    cost_usd=total_cost,
                    iterations=iteration + 1,
                )

        # Exhausted iterations — request final answer
        final_prompt = (
            "Based on your analysis, provide the fix now."
            if task.kind == "bugsinpy"
            else "Based on your analysis, provide the complete fixed Python file now."
        )
        messages.append({"role": "user", "content": final_prompt})
        resp = self.llm.chat(messages, temperature=self.config.temperature, model=self.config.model)
        total_cost += resp.cost_usd
        return AgentResult(
            fix=self._postprocess_fix(resp.content, task),
            reasoning=resp.content,
            tool_calls=tool_log,
            cost_usd=total_cost,
            iterations=self.config.max_iterations,
        )

    def _fix_plan_execute(self, task: Task) -> AgentResult:
        plan_messages = [
            {"role": "system", "content": self.config.system_prompt},
            {
                "role": "user",
                "content": (
                    f"{self._user_prompt(task)}\n\n"
                    "Create a concise step-by-step plan to identify and fix the bug."
                ),
            },
        ]
        plan_resp = self.llm.chat(plan_messages, temperature=self.config.temperature, model=self.config.model)
        total_cost = plan_resp.cost_usd

        exec_hint = (
            "Execute this plan and provide the fix."
            if task.kind == "bugsinpy"
            else "Execute this plan and return the complete fixed Python file."
        )
        exec_messages = [
            {"role": "system", "content": self.config.system_prompt},
            {
                "role": "user",
                "content": (
                    f"{self._user_prompt(task)}\n\n"
                    f"Your plan:\n{plan_resp.content}\n\n"
                    f"{exec_hint}"
                ),
            },
        ]
        exec_resp = self.llm.chat(exec_messages, temperature=self.config.temperature, model=self.config.model)
        total_cost += exec_resp.cost_usd

        return AgentResult(
            fix=self._postprocess_fix(exec_resp.content, task),
            reasoning=f"Plan:\n{plan_resp.content}\n\nExecution:\n{exec_resp.content}",
            cost_usd=total_cost,
            iterations=2,
        )
