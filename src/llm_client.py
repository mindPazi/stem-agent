from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import openai

logger = logging.getLogger(__name__)

# Pricing per token (input, output) in USD.
# 5.4-series rates are not published; we use the 4o-mini tier as a documented
# proxy so that cost numbers remain comparable across runs (same scaling, not
# real billing).
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o-mini-2024-07-18": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
    "gpt-4o-2024-08-06": (2.50 / 1_000_000, 10.00 / 1_000_000),
    "gpt-5.4-mini-2026-03-17": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-5.4-nano-2026-03-17": (0.15 / 1_000_000, 0.60 / 1_000_000),
}


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] | None
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    cost_usd: float
    model: str
    latency_ms: float


class LLMClient:
    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-5.4-mini-2026-03-17",
        log_dir: Path | None = None,
    ) -> None:
        self.client = openai.OpenAI(api_key=api_key)
        self.default_model = default_model
        self.total_cost: float = 0.0
        self._log_path = (log_dir or Path("results")) / "api_calls.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        model = model or self.default_model
        t0 = time.perf_counter()

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        msg = response.choices[0].message
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        in_price, out_price = _PRICING.get(model, _PRICING["gpt-5.4-mini-2026-03-17"])
        cost = usage["prompt_tokens"] * in_price + usage["completion_tokens"] * out_price
        self.total_cost += cost

        tool_calls: list[dict] | None = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in msg.tool_calls
            ]

        resp = LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            usage=usage,
            cost_usd=cost,
            model=model,
            latency_ms=latency_ms,
        )
        self._log(resp)
        logger.debug(
            "LLM call model=%s tokens=%d cost=$%.4f latency=%.0fms",
            model,
            usage["total_tokens"],
            cost,
            latency_ms,
        )
        return resp

    def _log(self, resp: LLMResponse) -> None:
        import datetime

        record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "model": resp.model,
            "prompt_tokens": resp.usage["prompt_tokens"],
            "completion_tokens": resp.usage["completion_tokens"],
            "cost_usd": resp.cost_usd,
            "latency_ms": resp.latency_ms,
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def get_total_cost(self) -> float:
        return self.total_cost
