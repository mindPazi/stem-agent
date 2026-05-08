# Stem Agent

One-day pilot of a self-specializing agent for real Python bug repair.

The benchmark is a frozen 26-bug BugsInPy subset in `benchmark/subset.json`.
Splits are fixed in `benchmark/splits.json`.

## Setup

```bash
python -m pip install -e .
```

### BugsInPy paths

All paths are configurable via environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `BUGSINPY_ROOT` | `C:/tmp/BugsInPy` | BugsInPy framework checkout |
| `BUGSINPY_CACHE` | `C:/tmp/bugsinpy-project-cache` | Git mirror cache |
| `BUGSINPY_WORKSPACE` | `workspace/bugsinpy-eval-workspace` | Temporary eval checkouts |

On Windows, the runner executes BugsInPy tests through WSL.

### Docker (Linux)

```bash
docker build -t stem-agent .
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY stem-agent python scripts/run_final_eval.py
```

Set `OPENAI_API_KEY` in `.env` or pass `--api-key`.

## Fast Local Checks

```bash
python -m pytest -q
python scripts/run_sensor.py --heuristic
```

## Main Pipeline

```bash
python scripts/run_baselines.py --baselines vanilla_direct
python scripts/run_sensor.py --heuristic
python scripts/run_differentiation.py --max-iterations 10 --vital-threshold 0.75
python scripts/run_final_eval.py --agents vanilla_direct vanilla_cot stem_agent \
    random_search no_sensor no_safeguard hand_tuned
```

Outputs are written under `results/`. The final comparison is
`results/final_eval/test_results.json`.

## Verifying Results Without Re-running

```bash
cat results/final_eval/test_results.json
cat results/differentiation/champion_history.json
python -m pytest -q
python scripts/run_differentiation.py --dry-run --max-iterations 3
```
