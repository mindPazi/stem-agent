from __future__ import annotations

import pytest

from src.safeguard import Safeguard, SafeguardResult


def _make_safeguard(vital_ids=None, threshold=1.0):
    if vital_ids is None:
        vital_ids = ["t1", "t2", "t3"]
    return Safeguard(vital_tasks=vital_ids, threshold=threshold)


# ── Construction ──────────────────────────────────────────────────────────────

def test_empty_vital_tasks_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        Safeguard(vital_tasks=[])


def test_default_threshold_is_1():
    sg = Safeguard(vital_tasks=["a"])
    assert sg.threshold == 1.0


# ── Passing cases ─────────────────────────────────────────────────────────────

def test_all_vital_pass():
    sg = _make_safeguard()
    result = sg.check({"t1": True, "t2": True, "t3": True})
    assert result.is_safe
    assert result.reason == "OK"
    assert result.vital_pass_rate == 1.0
    assert result.failed_vital_tasks == []


def test_partial_vital_pass_within_threshold():
    sg = Safeguard(vital_tasks=["t1", "t2", "t3", "t4"], threshold=0.75)
    result = sg.check({"t1": True, "t2": True, "t3": True, "t4": False})
    assert result.is_safe
    assert result.vital_pass_rate == 0.75


# ── Failing cases ─────────────────────────────────────────────────────────────

def test_one_vital_fails_at_100pct_threshold():
    sg = _make_safeguard()
    result = sg.check({"t1": True, "t2": False, "t3": True})
    assert not result.is_safe
    assert "t2" in result.failed_vital_tasks
    assert result.vital_pass_rate == pytest.approx(2 / 3)


def test_all_vital_fail():
    sg = _make_safeguard()
    result = sg.check({"t1": False, "t2": False, "t3": False})
    assert not result.is_safe
    assert len(result.failed_vital_tasks) == 3
    assert result.vital_pass_rate == 0.0


def test_missing_task_treated_as_failure():
    sg = _make_safeguard(vital_ids=["t1", "t2"])
    result = sg.check({"t1": True})  # t2 missing
    assert not result.is_safe
    assert "t2" in result.failed_vital_tasks


# ── Threshold variations ──────────────────────────────────────────────────────

def test_threshold_zero_always_passes():
    sg = Safeguard(vital_tasks=["t1", "t2"], threshold=0.0)
    result = sg.check({"t1": False, "t2": False})
    assert result.is_safe


def test_threshold_strictly_less_than_boundary():
    # 1/2 = 0.5, threshold = 0.6 → should fail
    sg = Safeguard(vital_tasks=["t1", "t2"], threshold=0.6)
    result = sg.check({"t1": True, "t2": False})
    assert not result.is_safe


def test_challenger_rejection_does_not_mutate_vital_list():
    sg = Safeguard(vital_tasks=["t1", "t2"])
    sg.check({"t1": False, "t2": False})
    assert sg.vital_tasks == ["t1", "t2"]
