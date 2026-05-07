# Stem Agent

One-day pilot of a self-specializing agent for real Python bug repair.

The benchmark is a frozen 26-bug BugsInPy subset in `benchmark/subset.json`.
Splits are fixed in `benchmark/splits.json`.

## Setup

```powershell
python -m pip install -e .
```

For real BugsInPy evaluation, install BugsInPy under `C:\tmp\BugsInPy` and keep
a project mirror cache at `C:\tmp\bugsinpy-project-cache`. The runner executes
BugsInPy tests through WSL.

Set `OPENAI_API_KEY` in `.env` or pass `--api-key`.

## Fast Local Checks

```powershell
python -m pytest -q
python scripts\run_sensor.py --heuristic
```

## Main Pipeline

```powershell
python scripts\run_baselines.py --baselines vanilla_direct
python scripts\run_sensor.py --heuristic
python scripts\run_differentiation.py --max-iterations 5
python scripts\run_final_eval.py --agents vanilla_direct stem_agent
```

Outputs are written under `results/`. The final comparison is
`results/final_eval/test_results.json`.

## Current Frozen Evidence

The stored phase-0 baseline result for `gpt-5.4-mini-2026-03-17` solves 7/25
BugsInPy calibration bugs and 1/8 bugs on the frozen test split. The report does
not claim a stem-agent improvement until `run_final_eval.py` has produced the
after result.
