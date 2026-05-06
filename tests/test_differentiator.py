from __future__ import annotations

import random
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import AgentConfig
from src.differentiator import Differentiator
from src.safeguard import Safeguard


_VITAL = ["v1", "v2"]
_DEV = ["d1", "d2", "d3", "d4"]


def _make(tmp_path: Path, **overrides) -> Differentiator:
    llm = MagicMock()
    llm.get_total_cost.return_value = 0.0

    mutator = MagicMock()
    mutator.sample_mutations.return_value = ["add_constraint"]
    mutator.apply_mutations.return_value = AgentConfig()

    kwargs = dict(
        llm_client=llm,
        mutator=mutator,
        safeguard=Safeguard(vital_tasks=_VITAL),
        tasks={},
        dev_task_ids=_DEV,
        vital_task_ids=_VITAL,
        log_dir=tmp_path / "logs",
        max_iterations=10,
        min_improvement=0.02,
        convergence_window=3,
        rng=random.Random(0),
    )
    kwargs.update(overrides)
    return Differentiator(**kwargs)


def _results(dev_pass: int, vitals_ok: bool = True) -> dict[str, bool]:
    return {
        **{tid: (i < dev_pass) for i, tid in enumerate(_DEV)},
        **{tid: vitals_ok for tid in _VITAL},
    }


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_runs_to_max_iterations(tmp_path):
    """When each challenger improves the score, the loop runs all max_iterations."""
    MAX = 4
    d = _make(tmp_path, max_iterations=MAX, convergence_window=3)
    seq = [_results(i) for i in range(MAX + 1)]
    idx = 0

    def _fake(_config):
        nonlocal idx
        r = seq[idx]
        idx += 1
        return r

    with patch.object(d, "_evaluate", side_effect=_fake):
        result = d.run(AgentConfig())

    assert result.total_iterations == MAX
    assert not result.converged


def test_converges_early_when_no_improvement(tmp_path):
    """Constant score → all rejections → convergence fires after window iterations."""
    d = _make(tmp_path, max_iterations=20, convergence_window=3)

    with patch.object(d, "_evaluate", return_value=_results(2)):
        result = d.run(AgentConfig())

    assert result.converged
    assert result.total_iterations == 3


def test_no_calibration_tasks_does_not_crash(tmp_path):
    """solved_calibration_tasks=None should be treated as an empty list."""
    d = _make(tmp_path, solved_calibration_tasks=None, max_iterations=2, convergence_window=5)

    with patch.object(d, "_evaluate", return_value=_results(2)):
        result = d.run(AgentConfig())

    assert result is not None
    assert d.solved_calibration_tasks == []


def test_safeguard_rejection_logged(tmp_path):
    """Challengers that fail vital tasks are rejected with reason='safeguard'."""
    d = _make(tmp_path, max_iterations=3, convergence_window=10)

    call_count = 0

    def _fake(_config):
        nonlocal call_count
        call_count += 1
        return _results(2, vitals_ok=True) if call_count == 1 else _results(3, vitals_ok=False)

    with patch.object(d, "_evaluate", side_effect=_fake):
        result = d.run(AgentConfig())

    assert all(r.reason == "safeguard" for r in result.history)
    assert result.final_score == pytest.approx(2 / 4)


def test_accepted_mutation_raises_final_score(tmp_path):
    """After one accepted mutation the final score reflects the improved champion."""
    d = _make(tmp_path, max_iterations=5, convergence_window=3)

    call_count = 0

    def _fake(_config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _results(1)  # initial champion: 0.25
        if call_count == 2:
            return _results(4)  # first challenger: 1.0 → accepted
        return _results(4)      # subsequent challengers: same → rejected → converge

    with patch.object(d, "_evaluate", side_effect=_fake):
        result = d.run(AgentConfig())

    assert result.final_score == pytest.approx(1.0)
    assert result.history[0].accepted is True
