from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agent import AgentResult, BugFixAgent, Task
from src.config import AgentConfig
from src.llm_client import LLMResponse


def _make_resp(content: str, cost: float = 0.001) -> LLMResponse:
    return LLMResponse(
        content=content,
        tool_calls=None,
        usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        cost_usd=cost,
        model="gpt-4o-mini",
        latency_ms=100.0,
    )


@pytest.fixture()
def task(tmp_path: Path) -> Task:
    (tmp_path / "buggy.py").write_text("def add(a,b): return a-b\n")
    (tmp_path / "test_suite.py").write_text(
        "from solution import add\ndef test_add(): assert add(1,2)==3\n"
    )
    return Task(
        task_id="task_001",
        task_dir=str(tmp_path),
        buggy_code="def add(a,b): return a-b",
        description="Wrong operator in add",
        test_suite_code="from solution import add\ndef test_add(): assert add(1,2)==3\n",
    )


def test_direct_strategy(task: Task):
    client = MagicMock()
    client.chat.return_value = _make_resp("```python\ndef add(a,b): return a+b\n```")

    cfg = AgentConfig(approach="direct")
    agent = BugFixAgent(cfg, client)
    result = agent.fix(task)

    assert "def add" in result.fix
    assert result.cost_usd == pytest.approx(0.001)
    assert result.iterations == 1


def test_cot_strategy(task: Task):
    client = MagicMock()
    client.chat.return_value = _make_resp(
        "The bug is the minus sign.\n\n```python\ndef add(a,b): return a+b\n```"
    )

    cfg = AgentConfig(approach="cot", reasoning_instruction="Think carefully.")
    agent = BugFixAgent(cfg, client)
    result = agent.fix(task)

    assert "def add" in result.fix
    call_args = client.chat.call_args
    # CoT instruction should be appended to user message
    assert "Think carefully" in call_args[0][0][-1]["content"]


def test_plan_execute_strategy(task: Task):
    client = MagicMock()
    client.chat.side_effect = [
        _make_resp("Step 1: Find the bug. Step 2: Fix it."),
        _make_resp("```python\ndef add(a,b): return a+b\n```"),
    ]

    cfg = AgentConfig(approach="plan_execute")
    agent = BugFixAgent(cfg, client)
    result = agent.fix(task)

    assert result.iterations == 2
    assert client.chat.call_count == 2


def test_react_strategy_no_tools(task: Task):
    client = MagicMock()
    client.chat.return_value = _make_resp("```python\ndef add(a,b): return a+b\n```")

    cfg = AgentConfig(approach="react", max_iterations=3, enabled_tools=[])
    agent = BugFixAgent(cfg, client)
    result = agent.fix(task)

    assert "def add" in result.fix


def test_extract_code_with_backticks():
    cfg = AgentConfig()
    agent = BugFixAgent(cfg, MagicMock())
    code = agent._extract_code("Some text\n```python\nx = 1\n```")
    assert code == "x = 1"


def test_extract_code_raw():
    cfg = AgentConfig()
    agent = BugFixAgent(cfg, MagicMock())
    code = agent._extract_code("def foo(): pass")
    assert code == "def foo(): pass"


def test_unknown_approach_raises(task: Task):
    cfg = AgentConfig(approach="unknown_approach")
    agent = BugFixAgent(cfg, MagicMock())
    with pytest.raises(ValueError, match="Unknown approach"):
        agent.fix(task)


def test_few_shot_examples_included(task: Task):
    from src.config import FewShotExample

    ex = FewShotExample(
        buggy_code="x = 1",
        test_error="fail",
        reasoning="because...",
        fix="x = 2",
        source_task="task_000",
    )
    client = MagicMock()
    client.chat.return_value = _make_resp("```python\ndef add(a,b): return a+b\n```")
    cfg = AgentConfig(approach="direct", few_shot_examples=[ex])
    agent = BugFixAgent(cfg, client)
    agent.fix(task)

    messages = client.chat.call_args[0][0]
    # Should have system + 2 few-shot messages + user = 4 messages
    assert len(messages) >= 4


def test_task_description_is_not_sent_to_model(task: Task):
    client = MagicMock()
    client.chat.return_value = _make_resp("```python\ndef add(a,b): return a+b\n```")
    cfg = AgentConfig(approach="direct")
    agent = BugFixAgent(cfg, client)
    agent.fix(task)

    messages = client.chat.call_args[0][0]
    user_prompt = messages[-1]["content"]
    assert task.description not in user_prompt
    assert "Bug description" not in user_prompt
    assert task.test_suite_code in user_prompt
