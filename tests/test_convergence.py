from __future__ import annotations

from src.convergence import MutationRecord, check_convergence


def _record(iteration: int, *, accepted: bool, delta: float = 0.0) -> MutationRecord:
    return MutationRecord(
        iteration=iteration,
        mutation_names=["x"],
        accepted=accepted,
        score_before=0.5,
        score_after=0.5 + delta,
        delta=delta,
        reason="accepted" if accepted else "no_improvement",
    )


# ── check_convergence ────────────────────────────────────────────────────────


def test_not_converged_when_history_too_short():
    history = [_record(0, accepted=True, delta=0.05)]
    assert not check_convergence(history, window=5, min_delta=0.02)


def test_not_converged_with_recent_acceptance_above_min_delta():
    history = [
        _record(0, accepted=False, delta=0.0),
        _record(1, accepted=False, delta=0.0),
        _record(2, accepted=False, delta=0.0),
        _record(3, accepted=False, delta=0.0),
        _record(4, accepted=True, delta=0.10),
    ]
    assert not check_convergence(history, window=5, min_delta=0.02)


def test_converged_when_only_rejections_in_window():
    history = [
        _record(0, accepted=False, delta=0.0),
        _record(1, accepted=False, delta=0.0),
        _record(2, accepted=False, delta=0.0),
        _record(3, accepted=False, delta=0.0),
        _record(4, accepted=False, delta=0.0),
    ]
    assert check_convergence(history, window=5, min_delta=0.02)


def test_converged_when_acceptance_below_min_delta():
    history = [
        _record(0, accepted=True, delta=0.005),
        _record(1, accepted=True, delta=0.001),
        _record(2, accepted=False, delta=0.0),
        _record(3, accepted=False, delta=0.0),
        _record(4, accepted=False, delta=0.0),
    ]
    # Despite "accepted" deltas in the window, they are below min_delta=0.02
    assert check_convergence(history, window=5, min_delta=0.02)


def test_old_acceptance_outside_window_does_not_prevent_convergence():
    history = [
        _record(0, accepted=True, delta=0.5),  # old big improvement
        _record(1, accepted=False, delta=0.0),
        _record(2, accepted=False, delta=0.0),
        _record(3, accepted=False, delta=0.0),
        _record(4, accepted=False, delta=0.0),
        _record(5, accepted=False, delta=0.0),
    ]
    assert check_convergence(history, window=5, min_delta=0.02)


# ── MutationRecord serialisation ──────────────────────────────────────────────


def test_mutation_record_to_dict_includes_all_fields():
    rec = MutationRecord(
        iteration=3,
        mutation_names=["add_exemplar", "specialize_for_category"],
        accepted=True,
        score_before=0.40,
        score_after=0.55,
        delta=0.15,
        reason="accepted",
    )
    d = rec.to_dict()
    assert d["iteration"] == 3
    assert d["mutation_names"] == ["add_exemplar", "specialize_for_category"]
    assert d["accepted"] is True
    assert d["delta"] == 0.15
    assert d["reason"] == "accepted"
