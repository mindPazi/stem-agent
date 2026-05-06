from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SafeguardResult:
    is_safe: bool
    reason: str
    vital_pass_rate: float
    failed_vital_tasks: list[str] = field(default_factory=list)


class Safeguard:
    """
    Enforces that agent specialization never loses core capabilities.

    Any challenger whose vital-sign pass rate drops below `threshold` is
    rejected outright, regardless of its dev-set score.  This is the novel
    "cellular apoptosis" invariant: a differentiating config that breaks
    baseline capabilities is destroyed.
    """

    def __init__(self, vital_tasks: list[str], threshold: float = 1.0) -> None:
        if not vital_tasks:
            raise ValueError("vital_tasks must not be empty")
        self.vital_tasks = list(vital_tasks)
        self.threshold = threshold

    def check(self, results: dict[str, bool]) -> SafeguardResult:
        """
        Returns SafeguardResult.  Missing task IDs are treated as failures.
        """
        failed = [t for t in self.vital_tasks if not results.get(t, False)]
        pass_count = len(self.vital_tasks) - len(failed)
        vital_pass_rate = pass_count / len(self.vital_tasks)

        if vital_pass_rate < self.threshold:
            reason = (
                f"Vital signs failure: {len(failed)}/{len(self.vital_tasks)} "
                f"tasks regressed: {failed}"
            )
            logger.warning(reason)
            return SafeguardResult(
                is_safe=False,
                reason=reason,
                vital_pass_rate=vital_pass_rate,
                failed_vital_tasks=failed,
            )

        return SafeguardResult(
            is_safe=True,
            reason="OK",
            vital_pass_rate=vital_pass_rate,
        )
