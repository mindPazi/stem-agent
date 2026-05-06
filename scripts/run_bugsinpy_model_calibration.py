#!/usr/bin/env python3
"""Run vanilla direct model calibration on a small BugsInPy subset."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_client import LLMClient
from src.utils import load_env_file, now_iso, save_json, setup_logging

logger = logging.getLogger(__name__)


DEFAULT_BUGS = ["youtube-dl:1", "youtube-dl:2", "youtube-dl:3", "youtube-dl:4", "youtube-dl:5"]


def _safe_model_dir(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model)


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":/", 1)[-1]
    return f"/mnt/{drive}/{rest}"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _run_bash(command: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return _run(["bash", "-lc", command], timeout=timeout)


def _parse_info(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r'\s*([A-Za-z0-9_]+)\s*=\s*"(.*)"\s*$', line)
        if match:
            data[match.group(1)] = match.group(2)
    return data


def _copy_file_bytes(src_root: Path, rel_path: str) -> bytes:
    return (src_root / rel_path).read_bytes()


def _load_patch_files_and_hunks(patch_path: Path) -> dict[str, list[tuple[int, int]]]:
    """Return changed files with old-file hunk ranges from a unified diff."""
    text = patch_path.read_text(encoding="utf-8", errors="ignore")
    current: str | None = None
    out: dict[str, list[tuple[int, int]]] = {}
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            current = parts[2][2:] if len(parts) >= 3 and parts[2].startswith("a/") else None
            if current:
                out.setdefault(current, [])
        elif current and line.startswith("@@"):
            match = re.search(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", line)
            if match:
                start = int(match.group(1))
                length = int(match.group(2) or "1")
                out[current].append((start, length))
    return out


def _load_patch_changed_ranges(patch_path: Path) -> list[dict]:
    """Return old-file line ranges that the reference patch changed, without fixed code."""
    text = patch_path.read_text(encoding="utf-8", errors="ignore")
    current: str | None = None
    old_line = 0
    ranges: list[dict] = []
    pending_start: int | None = None
    pending_end: int | None = None
    pending_lines: list[str] = []

    def flush() -> None:
        nonlocal pending_start, pending_end, pending_lines
        if current and pending_start is not None and pending_end is not None:
            ranges.append({
                "file": current,
                "start_line": pending_start,
                "end_line": pending_end,
                "buggy_lines": list(pending_lines),
            })
        pending_start = None
        pending_end = None
        pending_lines = []

    for line in text.splitlines():
        if line.startswith("diff --git "):
            flush()
            parts = line.split()
            current = parts[2][2:] if len(parts) >= 3 and parts[2].startswith("a/") else None
        elif current and line.startswith("@@"):
            flush()
            match = re.search(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", line)
            old_line = int(match.group(1)) if match else 0
        elif not current or line.startswith("--- ") or line.startswith("+++ "):
            continue
        elif line.startswith("-"):
            if pending_start is None:
                pending_start = old_line
            pending_end = old_line
            pending_lines.append(line[1:])
            old_line += 1
        elif line.startswith("+"):
            continue
        else:
            flush()
            if line.startswith(" "):
                old_line += 1

    flush()
    return ranges


def _snippet(path: Path, hunks: list[tuple[int, int]], context: int = 35) -> str:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    chunks: list[str] = []
    for start, length in hunks:
        lo = max(1, start - context)
        hi = min(len(lines), start + length + context)
        body = "\n".join(f"{idx:5d}: {lines[idx - 1]}" for idx in range(lo, hi + 1))
        chunks.append(f"# {path.as_posix()} lines {lo}-{hi}\n{body}")
    return "\n\n".join(chunks)


def _extract_patch(content: str) -> str:
    fenced = re.search(r"```(?:diff|patch)?\s*(.*?)```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1)
    start = content.find("diff --git ")
    if start != -1:
        return content[start:].strip() + "\n"
    start = content.find("--- ")
    if start != -1:
        return content[start:].strip() + "\n"
    return content.strip() + "\n"


def _extract_json(content: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1)
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(content[start:end + 1])


def _clean_replacement(value: object) -> list[str]:
    if isinstance(value, list):
        lines = [str(item) for item in value]
    else:
        lines = str(value).splitlines()
    cleaned: list[str] = []
    for line in lines:
        cleaned.append(re.sub(r"^\s*\d+:\s?", "", line))
    return cleaned


def _apply_json_edits(repo_dir: Path, raw_content: str) -> tuple[bool, str]:
    try:
        payload = _extract_json(raw_content)
        edits = payload.get("edits", [])
        if not isinstance(edits, list) or not edits:
            return False, "JSON has no edits list"
    except Exception as exc:
        return False, f"JSON parse failed: {exc}"

    by_file: dict[str, list[dict]] = {}
    for edit in edits:
        if not isinstance(edit, dict):
            return False, "edit is not an object"
        file_path = str(edit.get("file", "")).strip()
        try:
            start_line = int(edit.get("start_line"))
            end_line = int(edit.get("end_line"))
        except Exception:
            return False, f"invalid line range in edit: {edit!r}"
        if not file_path or start_line < 1 or end_line < start_line:
            return False, f"invalid edit: {edit!r}"
        by_file.setdefault(file_path, []).append({
            "start_line": start_line,
            "end_line": end_line,
            "replacement": _clean_replacement(edit.get("replacement", "")),
        })

    for file_path, file_edits in by_file.items():
        path = repo_dir / file_path
        if not path.exists():
            return False, f"file not found: {file_path}"
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for edit in sorted(file_edits, key=lambda item: item["start_line"], reverse=True):
            start = edit["start_line"] - 1
            end = edit["end_line"]
            if start < 0 or end > len(lines):
                return False, f"line range out of bounds for {file_path}: {edit['start_line']}-{edit['end_line']}"
            lines[start:end] = edit["replacement"]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, ""


def _ensure_project_cache(bugsinpy_root: Path, cache_root: Path, project: str) -> Path:
    project_info = _parse_info(bugsinpy_root / "projects" / project / "project.info")
    github_url = project_info.get("github_url")
    if not github_url:
        raise RuntimeError(f"Missing github_url for BugsInPy project {project}")

    cache_root.mkdir(parents=True, exist_ok=True)
    cache_dir = cache_root / f"{project}.git"
    if not cache_dir.exists():
        result = _run(["git", "clone", "--mirror", github_url, str(cache_dir)], timeout=900)
        if result.returncode != 0:
            raise RuntimeError(f"cache clone failed: {result.stdout}\n{result.stderr}")
    return cache_dir


def _checkout_version(
    bugsinpy_root: Path,
    workspace_root: Path,
    cache_root: Path,
    project: str,
    bug_id: str,
    version: str,
) -> Path:
    if version not in {"buggy", "fixed"}:
        raise ValueError("version must be 'buggy' or 'fixed'")
    dest = workspace_root / f"{project}-{bug_id}-{version}"
    if dest.exists():
        # BugsInPy creates virtualenv symlinks that Windows cannot always delete.
        # Remove within the C:\tmp workspace through WSL, which created them.
        cleanup = _run_bash(f"rm -rf -- {_wsl_path(dest)}", timeout=120)
        if cleanup.returncode != 0 and dest.exists():
            shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    cache_dir = _ensure_project_cache(bugsinpy_root, cache_root, project)
    repo_dir = dest / project

    result = _run(["git", "clone", "--shared", str(cache_dir), str(repo_dir)], timeout=420)
    if result.returncode != 0:
        raise RuntimeError(f"local checkout failed: {result.stdout}\n{result.stderr}")

    bug_dir = bugsinpy_root / "projects" / project / "bugs" / bug_id
    bug_info = _parse_info(bug_dir / "bug.info")
    fixed_commit = bug_info.get("fixed_commit_id")
    buggy_commit = bug_info.get("buggy_commit_id")
    test_files = [item for item in bug_info.get("test_file", "").split(";") if item]
    if not fixed_commit or not buggy_commit or not test_files:
        raise RuntimeError(f"Incomplete bug.info for {project}:{bug_id}")

    fixed = _run(["git", "reset", "--hard", fixed_commit], cwd=repo_dir, timeout=120)
    if fixed.returncode != 0:
        raise RuntimeError(f"fixed reset failed: {fixed.stdout}\n{fixed.stderr}")
    fixed_tests = {rel: _copy_file_bytes(repo_dir, rel) for rel in test_files}

    if version == "buggy":
        buggy = _run(["git", "reset", "--hard", buggy_commit], cwd=repo_dir, timeout=120)
        if buggy.returncode != 0:
            raise RuntimeError(f"buggy reset failed: {buggy.stdout}\n{buggy.stderr}")
        clean = _run(["git", "clean", "-f", "-d"], cwd=repo_dir, timeout=120)
        if clean.returncode != 0:
            raise RuntimeError(f"git clean failed: {clean.stdout}\n{clean.stderr}")

        for rel, content in fixed_tests.items():
            target = repo_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    shutil.copyfile(bug_dir / "bug.info", repo_dir / "bugsinpy_bug.info")
    shutil.copyfile(bug_dir / "requirements.txt", repo_dir / "bugsinpy_requirements.txt")
    shutil.copyfile(bug_dir / "run_test.sh", repo_dir / "bugsinpy_run_test.sh")
    (repo_dir / "bugsinpy_patchfile.info").write_text("", encoding="utf-8")
    if (bug_dir / "setup.sh").exists():
        shutil.copyfile(bug_dir / "setup.sh", repo_dir / "bugsinpy_setup.sh")
    return repo_dir


def _checkout_bug(
    bugsinpy_root: Path,
    workspace_root: Path,
    cache_root: Path,
    project: str,
    bug_id: str,
) -> Path:
    return _checkout_version(bugsinpy_root, workspace_root, cache_root, project, bug_id, "buggy")


def _compile_and_test(bugsinpy_root: Path, repo_dir: Path) -> tuple[bool, str]:
    script_dir = _wsl_path(bugsinpy_root / "framework" / "bin")
    repo = _wsl_path(repo_dir)
    command = f"cd {repo} && {script_dir}/bugsinpy-compile >/tmp/bugsinpy_compile.log 2>&1; {script_dir}/bugsinpy-test"
    result = _run_bash(command, timeout=300)
    output = (result.stdout + "\n" + result.stderr).strip()
    failure_markers = ("FAILED", "FAIL:", "ERROR:", "Traceback", "SyntaxError", "AssertionError")
    passed = bool(re.search(r"(^|\n)OK(\n|$)", output)) and not any(
        marker in output for marker in failure_markers
    )
    return passed, output[-6000:]


def _build_prompt(
    project: str,
    bug_id: str,
    test_output: str,
    snippets: dict[str, str],
    changed_ranges: list[dict],
) -> list[dict]:
    snippet_text = "\n\n".join(
        f"File: {file_path}\n```python\n{body}\n```" for file_path, body in snippets.items()
    )
    ranges_text = "\n".join(
        "- {file}:{start_line}-{end_line}\n{buggy}".format(
            file=item["file"],
            start_line=item["start_line"],
            end_line=item["end_line"],
            buggy="\n".join(f"  {line}" for line in item.get("buggy_lines", [])),
        )
        for item in changed_ranges
    )
    user = (
        f"Fix this real BugsInPy bug.\n\n"
        f"Project: {project}\n"
        f"Bug id: {bug_id}\n\n"
        "Failing test output:\n"
        f"```\n{test_output}\n```\n\n"
        "Relevant buggy-code snippets with line numbers:\n"
        f"{snippet_text}\n\n"
        "Candidate buggy line ranges to edit:\n"
        f"{ranges_text}\n\n"
        "Return only valid JSON with this exact shape:\n"
        "{\"edits\":[{\"file\":\"path/to/file.py\",\"start_line\":1,\"end_line\":1,"
        "\"replacement\":\"replacement line 1\\nreplacement line 2\"}]}\n"
        "The replacement must contain the full corrected text for the selected inclusive line range. "
        "Do not include markdown or explanation."
    )
    return [
        {"role": "system", "content": "You are a Python developer. Fix the bug with a minimal patch."},
        {"role": "user", "content": user},
    ]


def _evaluate_bug(
    bugsinpy_root: Path,
    workspace_root: Path,
    cache_root: Path,
    llm: LLMClient,
    model: str,
    bug_spec: str,
) -> dict:
    project, bug_id = bug_spec.split(":", 1)
    repo_dir = _checkout_bug(bugsinpy_root, workspace_root, cache_root, project, bug_id)
    initial_passed, test_output = _compile_and_test(bugsinpy_root, repo_dir)
    if initial_passed:
        return {
            "passed": False,
            "error": "buggy version unexpectedly passed",
            "test_output": test_output,
        }

    patch_path = bugsinpy_root / "projects" / project / "bugs" / bug_id / "bug_patch.txt"
    changed = _load_patch_files_and_hunks(patch_path)
    changed_ranges = _load_patch_changed_ranges(patch_path)
    snippets = {
        file_path: _snippet(repo_dir / file_path, hunks)
        for file_path, hunks in changed.items()
        if (repo_dir / file_path).exists()
    }
    if not snippets:
        return {"passed": False, "error": "no usable changed-file snippets found"}

    t0 = time.perf_counter()
    resp = llm.chat(
        _build_prompt(project, bug_id, test_output, snippets, changed_ranges),
        model=model,
        temperature=0.0,
    )
    applied, apply_error = _apply_json_edits(repo_dir, resp.content)
    if not applied:
        return {
            "passed": False,
            "error": "edit_apply_failed",
            "apply_error": apply_error,
            "raw_fix": resp.content,
            "cost_usd": round(resp.cost_usd, 6),
            "duration_s": round(time.perf_counter() - t0, 3),
        }

    passed, final_output = _compile_and_test(bugsinpy_root, repo_dir)
    return {
        "passed": passed,
        "test_output": final_output,
        "raw_fix": resp.content,
        "cost_usd": round(resp.cost_usd, 6),
        "duration_s": round(time.perf_counter() - t0, 3),
    }


def _validate_bug(
    bugsinpy_root: Path,
    workspace_root: Path,
    cache_root: Path,
    bug_spec: str,
) -> dict:
    project, bug_id = bug_spec.split(":", 1)
    started = time.perf_counter()
    try:
        buggy_repo = _checkout_version(bugsinpy_root, workspace_root, cache_root, project, bug_id, "buggy")
        buggy_passed, buggy_output = _compile_and_test(bugsinpy_root, buggy_repo)
        fixed_repo = _checkout_version(bugsinpy_root, workspace_root, cache_root, project, bug_id, "fixed")
        fixed_passed, fixed_output = _compile_and_test(bugsinpy_root, fixed_repo)
        ok = (not buggy_passed) and fixed_passed
        return {
            "valid": ok,
            "buggy_passed": buggy_passed,
            "fixed_passed": fixed_passed,
            "buggy_output": buggy_output[-2000:],
            "fixed_output": fixed_output[-2000:],
            "duration_s": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "valid": False,
            "error": str(exc),
            "duration_s": round(time.perf_counter() - started, 3),
        }


def _run_validation(args: argparse.Namespace) -> None:
    bugsinpy_root = Path(args.bugsinpy_root)
    workspace_root = Path(args.workspace_root) / "validation"
    cache_root = Path(args.cache_root)
    out_path = Path(args.results_dir) / "validated_subset.json"
    if out_path.exists() and not args.force:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        data = {"created_at": now_iso(), "results": {}}

    for bug_spec in args.bugs:
        if bug_spec in data["results"] and not args.force:
            logger.info("Validation: skipping %s", bug_spec)
            continue
        logger.info("Validation: checking %s", bug_spec)
        result = _validate_bug(bugsinpy_root, workspace_root, cache_root, bug_spec)
        data["results"][bug_spec] = result
        data["valid_bugs"] = [
            tid for tid, item in data["results"].items() if item.get("valid")
        ]
        data["updated_at"] = now_iso()
        save_json(out_path, data)
        logger.info("Validation: %s -> %s", bug_spec, "VALID" if result.get("valid") else "INVALID")


def _run_model(args: argparse.Namespace, model: str) -> None:
    bugsinpy_root = Path(args.bugsinpy_root)
    workspace_root = Path(args.workspace_root) / _safe_model_dir(model)
    cache_root = Path(args.cache_root)
    out_dir = Path(args.results_dir) / _safe_model_dir(model)
    out_path = out_dir / "vanilla_direct_bugsinpy.json"

    if out_path.exists() and not args.force:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        data = {
            "baseline": "vanilla_direct_bugsinpy",
            "model": model,
            "bugs": args.bugs,
            "created_at": now_iso(),
            "results": {},
        }

    llm = LLMClient(api_key=args.api_key, default_model=model, log_dir=out_dir)
    for bug_spec in args.bugs:
        if bug_spec in data["results"] and not args.force:
            logger.info("Model %s: skipping %s", model, bug_spec)
            continue
        logger.info("Model %s: evaluating %s", model, bug_spec)
        result = _evaluate_bug(bugsinpy_root, workspace_root, cache_root, llm, model, bug_spec)
        data["results"][bug_spec] = result
        n = len(data["results"])
        ok = sum(1 for item in data["results"].values() if item.get("passed"))
        data["n_total"] = n
        data["n_passed"] = ok
        data["pass_at_1"] = ok / n if n else 0.0
        data["updated_at"] = now_iso()
        save_json(out_path, data)
        logger.info("Model %s: %s -> %s (%d/%d)", model, bug_spec, "PASS" if result.get("passed") else "FAIL", ok, n)

    data["completed_at"] = now_iso()
    data["total_cost_usd"] = round(llm.get_total_cost(), 6)
    save_json(out_path, data)


def main() -> None:
    load_env_file()
    parser = argparse.ArgumentParser(description="Calibrate models on a small BugsInPy subset")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--models", nargs="+", default=[])
    parser.add_argument("--bugs", nargs="+", default=DEFAULT_BUGS)
    parser.add_argument("--bugsinpy-root", default="C:/tmp/BugsInPy")
    parser.add_argument("--workspace-root", default="C:/tmp/bugsinpy-model-calibration-workspace")
    parser.add_argument("--cache-root", default="C:/tmp/bugsinpy-project-cache")
    parser.add_argument("--results-dir", default="results/bugsinpy_model_calibration")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    setup_logging()
    if args.validate_only:
        _run_validation(args)
        return
    if not args.models:
        sys.exit("ERROR: pass --models or use --validate-only")
    if not args.api_key:
        sys.exit("ERROR: set OPENAI_API_KEY or pass --api-key")
    for model in args.models:
        _run_model(args, model)


if __name__ == "__main__":
    main()
