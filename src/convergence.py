from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MutationRecord:
    """Immutable log entry for one differentiation iteration."""

    iteration: int
    mutation_names: list[str]
    accepted: bool
    score_before: float
    score_after: float
    delta: float = 0.0
    # "accepted" | "safeguard" | "no_improvement"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "mutation_names": self.mutation_names,
            "accepted": self.accepted,
            "score_before": self.score_before,
            "score_after": self.score_after,
            "delta": self.delta,
            "reason": self.reason,
        }


def check_convergence(
    history: list[MutationRecord],
    window: int = 5,
    min_delta: float = 0.02,
) -> bool:
    """Return True if no accepted improvement > min_delta in the last `window` records."""
    if len(history) < window:
        return False
    recent = history[-window:]
    return not any(r.delta > min_delta and r.accepted for r in recent)
