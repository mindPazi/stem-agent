from __future__ import annotations

import random


def stratified_sample(
    task_ids: list[str],
    metadata: dict[str, dict],
    n: int,
    rng: random.Random,
) -> list[str]:
    """Sample exactly n task IDs, stratified by metadata category."""
    if len(task_ids) <= n:
        return list(task_ids)

    by_cat: dict[str, list[str]] = {}
    for task_id in task_ids:
        cat = metadata.get(task_id, {}).get("category", "other")
        by_cat.setdefault(cat, []).append(task_id)

    cats = list(by_cat.keys())
    rng.shuffle(cats)

    sampled: list[str] = []
    quota_left = n

    for i, cat in enumerate(cats):
        if i == len(cats) - 1:
            take = quota_left
        else:
            proportion = len(by_cat[cat]) / len(task_ids)
            take = max(1, round(proportion * n))
            take = min(take, quota_left, len(by_cat[cat]))

        pool = list(by_cat[cat])
        rng.shuffle(pool)
        sampled.extend(pool[:take])
        quota_left -= take
        if quota_left <= 0:
            break

    return sampled[:n]


def assign_splits(
    all_task_ids: list[str],
    vanilla_results: dict[str, bool],
    metadata: dict[str, dict],
    seed: int = 42,
) -> dict[str, list[str]]:
    """
    Assign tasks to frozen experiment splits.

    Vital signs are sampled from tasks solved by vanilla_direct. Calibration,
    dev, and test are sampled from the remaining tasks.
    """
    rng = random.Random(seed)

    solved = [task_id for task_id in all_task_ids if vanilla_results.get(task_id, False)]
    vital_signs = stratified_sample(solved, metadata, n=min(8, len(solved)), rng=rng)

    remaining = [task_id for task_id in all_task_ids if task_id not in set(vital_signs)]
    rng.shuffle(remaining)

    calibration = stratified_sample(remaining, metadata, n=min(12, len(remaining)), rng=rng)

    after_calib = [task_id for task_id in remaining if task_id not in set(calibration)]
    dev = stratified_sample(after_calib, metadata, n=min(30, len(after_calib)), rng=rng)

    test = [task_id for task_id in after_calib if task_id not in set(dev)]

    return {
        "vital_signs": vital_signs,
        "calibration": calibration,
        "dev": dev,
        "test": test,
    }
