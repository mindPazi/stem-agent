from __future__ import annotations

import random

from src.splits import assign_splits, stratified_sample


def test_stratified_sample_is_deterministic_for_seed():
    task_ids = [f"task_{i:03d}" for i in range(12)]
    metadata = {
        task_id: {"category": "a" if i < 6 else "b"}
        for i, task_id in enumerate(task_ids)
    }

    first = stratified_sample(task_ids, metadata, n=6, rng=random.Random(42))
    second = stratified_sample(task_ids, metadata, n=6, rng=random.Random(42))

    assert first == second
    assert len(first) == 6


def test_assign_splits_uses_vital_tasks_from_vanilla_solved_pool():
    task_ids = [f"task_{i:03d}" for i in range(20)]
    metadata = {
        task_id: {"category": "logic_error" if i % 2 else "boundary"}
        for i, task_id in enumerate(task_ids)
    }
    vanilla_results = {task_id: i < 10 for i, task_id in enumerate(task_ids)}

    splits = assign_splits(task_ids, vanilla_results, metadata, seed=7)

    assert set(splits) == {"vital_signs", "calibration", "dev", "test"}
    assert set(splits["vital_signs"]) <= {
        task_id for task_id, passed in vanilla_results.items() if passed
    }
    all_split_ids = (
        splits["vital_signs"] + splits["calibration"] + splits["dev"] + splits["test"]
    )
    assert sorted(all_split_ids) == sorted(task_ids)
    assert len(all_split_ids) == len(set(all_split_ids))
