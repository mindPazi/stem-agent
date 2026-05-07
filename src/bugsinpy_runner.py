"""Apply agent fixes and run BugsInPy tests via WSL.

Handles the JSON-edits format used by the BugsInPy agent flow and invokes
bugsinpy-compile + bugsinpy-test in WSL with timeout.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":/", 1)[-1]
    return f"/mnt/{drive}/{rest}"


def _run_bash(command: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", command],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout,
    )


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


def apply_json_edits(repo_dir: Path, raw_content: str) -> tuple[bool, str]:
    """Parse agent output as JSON edits and apply to the repo. Returns (success, error_msg)."""
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
                return False, (
                    f"line range out of bounds for {file_path}: "
                    f"{edit['start_line']}-{edit['end_line']} (file has {len(lines)} lines)"
                )
            lines[start:end] = edit["replacement"]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, ""


def compile_and_test(
    bugsinpy_root: Path,
    repo_dir: Path,
    timeout: int = 300,
    compile_timeout: int = 120,
) -> tuple[bool, str]:
    """Run bugsinpy-compile + bugsinpy-test via WSL. Returns (passed, output)."""
    script_dir = _wsl_path(bugsinpy_root / "framework" / "bin")
    repo = _wsl_path(repo_dir)

    compile_cmd = f"cd {repo} && {script_dir}/bugsinpy-compile"
    try:
        comp = _run_bash(compile_cmd, timeout=compile_timeout)
    except subprocess.TimeoutExpired:
        return False, f"Compile timeout after {compile_timeout}s"
    if comp.returncode != 0:
        output = (comp.stdout + "\n" + comp.stderr).strip()
        if "not a checkout" in output.lower() or "error" in output.lower():
            return False, f"Compile failed: {output[-2000:]}"

    test_cmd = f"cd {repo} && {script_dir}/bugsinpy-test"
    test_timeout = max(60, timeout - compile_timeout)
    try:
        result = _run_bash(test_cmd, timeout=test_timeout)
    except subprocess.TimeoutExpired:
        return False, f"Test timeout after {test_timeout}s"
    output = (result.stdout + "\n" + result.stderr).strip()
    failure_markers = ("FAILED", "FAIL:", "ERROR:", "Traceback", "SyntaxError", "AssertionError")
    passed = bool(re.search(r"(^|\n)OK(\n|$)", output)) and not any(
        marker in output for marker in failure_markers
    )
    return passed, output[-6000:]


def evaluate_bugsinpy_fix(
    bugsinpy_root: Path,
    repo_dir: Path,
    raw_fix: str,
    timeout: int = 300,
) -> dict:
    """Apply a JSON-edits fix to the repo and run tests. Returns result dict."""
    t0 = time.perf_counter()
    applied, apply_error = apply_json_edits(Path(repo_dir), raw_fix)
    if not applied:
        return {
            "passed": False,
            "error": "edit_apply_failed",
            "apply_error": apply_error,
            "duration_s": round(time.perf_counter() - t0, 3),
        }
    passed, test_output = compile_and_test(bugsinpy_root, Path(repo_dir), timeout=timeout)
    return {
        "passed": passed,
        "test_output": test_output,
        "duration_s": round(time.perf_counter() - t0, 3),
    }
