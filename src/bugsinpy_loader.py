"""Pure-data loader for BugsInPy tasks.

Given (project, bug_id), returns a Task-compatible object with:
- buggy file snippets around changed regions
- changed line ranges from the reference patch
- initial failing test output

Reuses _checkout_version, _parse_info, _load_patch_changed_ranges from
the legacy calibration script (git show 789c304~1:scripts/run_bugsinpy_model_calibration.py).
"""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_BUGSINPY_ROOT = Path(os.environ.get("BUGSINPY_ROOT", "C:/tmp/BugsInPy"))
DEFAULT_CACHE_ROOT = Path(os.environ.get("BUGSINPY_CACHE", "C:/tmp/bugsinpy-project-cache"))
DEFAULT_WORKSPACE_ROOT = Path(os.environ.get("BUGSINPY_WORKSPACE", "workspace/bugsinpy-eval-workspace"))

_checkout_cache: dict[tuple[str, str], dict] = {}


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":/", 1)[-1]
    return f"/mnt/{drive}/{rest}"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
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
        cleanup = _run_bash(f"rm -rf -- {_wsl_path(dest)}", timeout=120)
        if cleanup.returncode != 0 and dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        if dest.exists():
            dest = workspace_root / f"{project}-{bug_id}-{version}-{uuid.uuid4().hex[:8]}"
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        dest = workspace_root / f"{project}-{bug_id}-{version}-{uuid.uuid4().hex[:8]}"
        dest.mkdir(parents=True, exist_ok=True)
    cache_dir = _ensure_project_cache(bugsinpy_root, cache_root, project)
    repo_dir = dest / project

    result = _run_bash(
        "git clone --shared "
        f"{shlex.quote(_wsl_path(cache_dir))} {shlex.quote(_wsl_path(repo_dir))}",
        timeout=420,
    )
    if result.returncode != 0:
        raise RuntimeError(f"local checkout failed: {result.stdout}\n{result.stderr}")

    bug_dir = bugsinpy_root / "projects" / project / "bugs" / bug_id
    bug_info = _parse_info(bug_dir / "bug.info")
    fixed_commit = bug_info.get("fixed_commit_id")
    buggy_commit = bug_info.get("buggy_commit_id")
    test_files = [item for item in bug_info.get("test_file", "").split(";") if item]
    if not fixed_commit or not buggy_commit or not test_files:
        raise RuntimeError(f"Incomplete bug.info for {project}:{bug_id}")

    repo_wsl = shlex.quote(_wsl_path(repo_dir))
    fixed = _run_bash(f"cd {repo_wsl} && git reset --hard {shlex.quote(fixed_commit)}", timeout=120)
    if fixed.returncode != 0:
        raise RuntimeError(f"fixed reset failed: {fixed.stdout}\n{fixed.stderr}")
    fixed_tests = {rel: _copy_file_bytes(repo_dir, rel) for rel in test_files}

    if version == "buggy":
        buggy = _run_bash(
            f"cd {repo_wsl} && git reset --hard {shlex.quote(buggy_commit)}",
            timeout=120,
        )
        if buggy.returncode != 0:
            raise RuntimeError(f"buggy reset failed: {buggy.stdout}\n{buggy.stderr}")
        clean = _run_bash(f"cd {repo_wsl} && git clean -f -d", timeout=120)
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

    if version == "buggy":
        _checkout_cache[(project, bug_id)] = {
            "repo_dir": repo_dir,
            "buggy_commit": buggy_commit,
            "fixed_tests": fixed_tests,
            "bug_dir": bug_dir,
        }

    return repo_dir


def fast_recheckout(project: str, bug_id: str) -> Path:
    """Reset an existing buggy checkout instead of full rm + clone (~10x faster)."""
    cached = _checkout_cache.get((project, bug_id))
    if cached is None:
        return _checkout_version(
            DEFAULT_BUGSINPY_ROOT, DEFAULT_WORKSPACE_ROOT, DEFAULT_CACHE_ROOT,
            project, bug_id, "buggy",
        )

    repo_dir: Path = cached["repo_dir"]
    buggy_commit: str = cached["buggy_commit"]
    fixed_tests: dict[str, bytes] = cached["fixed_tests"]
    bug_dir: Path = cached["bug_dir"]

    repo_wsl = shlex.quote(_wsl_path(repo_dir))
    reset = _run_bash(
        f"cd {repo_wsl} && git reset --hard {shlex.quote(buggy_commit)} && git clean -f -d",
        timeout=120,
    )
    if reset.returncode != 0:
        logger.warning("fast_recheckout reset failed, falling back to full checkout")
        _checkout_cache.pop((project, bug_id), None)
        return _checkout_version(
            DEFAULT_BUGSINPY_ROOT, DEFAULT_WORKSPACE_ROOT, DEFAULT_CACHE_ROOT,
            project, bug_id, "buggy",
        )

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


def _load_patch_files_and_hunks(patch_path: Path, text: str | None = None) -> dict[str, list[tuple[int, int]]]:
    if text is None:
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


def _load_patch_changed_ranges(patch_path: Path, text: str | None = None) -> list[dict]:
    if text is None:
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


def _classify_bug(changed_ranges: list[dict], patch_path: Path, text: str | None = None) -> str:
    """Heuristic category from the patch content."""
    if text is None:
        text = patch_path.read_text(encoding="utf-8", errors="ignore")
    buggy_lines = []
    for r in changed_ranges:
        buggy_lines.extend(r.get("buggy_lines", []))
    buggy_text = "\n".join(buggy_lines)

    if re.search(r"[+-]\s*1\b", text) and re.search(r"(range|len|index|\[)", buggy_text):
        return "off_by_one"
    if len(changed_ranges) == 1 and len(buggy_lines) <= 2:
        stripped = [l.strip() for l in buggy_lines if l.strip()]
        if stripped and all(re.match(r'^[a-zA-Z_]', s) for s in stripped):
            return "wrong_variable"
    if re.search(r"(if |elif |None|not |is None|== None)", buggy_text):
        return "missing_check"
    if re.search(r"(TypeError|bytes|str\(|int\(|float\()", text):
        return "type_error"
    if re.search(r"(return|raise|assert)", buggy_text):
        return "logic_error"
    return "other"


def _count_lines_changed(patch_path: Path, text: str | None = None) -> int:
    if text is None:
        text = patch_path.read_text(encoding="utf-8", errors="ignore")
    return sum(1 for line in text.splitlines() if line.startswith("+") or line.startswith("-"))


@dataclass
class BugsInPyTask:
    """A BugsInPy bug represented as a Task-compatible object."""
    task_id: str
    task_dir: str
    buggy_code: str
    description: str
    test_suite_code: str = ""
    category: str = ""
    difficulty: str = ""
    kind: str = "bugsinpy"
    project: str = ""
    bug_id: str = ""
    snippets: dict[str, str] = field(default_factory=dict)
    changed_ranges: list[dict] = field(default_factory=list)
    test_output: str = ""
    repo_dir: str = ""


def load_bugsinpy_task(
    project: str,
    bug_id: str,
    bugsinpy_root: Path = DEFAULT_BUGSINPY_ROOT,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> BugsInPyTask:
    """Load a single BugsInPy bug as a task. Checks out the buggy version."""
    repo_dir = _checkout_version(
        bugsinpy_root, workspace_root, cache_root, project, bug_id, "buggy",
    )
    bug_dir = bugsinpy_root / "projects" / project / "bugs" / bug_id
    patch_path = bug_dir / "bug_patch.txt"
    patch_text = patch_path.read_text(encoding="utf-8", errors="ignore")

    changed = _load_patch_files_and_hunks(patch_path, text=patch_text)
    changed_ranges = _load_patch_changed_ranges(patch_path, text=patch_text)

    snippets = {
        file_path: _snippet(repo_dir / file_path, hunks)
        for file_path, hunks in changed.items()
        if (repo_dir / file_path).exists()
    }
    buggy_code = "\n\n".join(snippets.values()) if snippets else ""
    category = _classify_bug(changed_ranges, patch_path, text=patch_text)
    lines_changed = _count_lines_changed(patch_path, text=patch_text)
    difficulty = "easy" if lines_changed <= 4 else ("medium" if lines_changed <= 12 else "hard")

    return BugsInPyTask(
        task_id=f"{project}:{bug_id}",
        task_dir=str(repo_dir),
        buggy_code=buggy_code,
        description=f"BugsInPy {project} bug #{bug_id}",
        category=category,
        difficulty=difficulty,
        kind="bugsinpy",
        project=project,
        bug_id=bug_id,
        snippets=snippets,
        changed_ranges=changed_ranges,
        repo_dir=str(repo_dir),
    )


def load_bugsinpy_subset(subset_path: Path) -> list[dict]:
    """Load the frozen bugsinpy_subset.json."""
    return json.loads(subset_path.read_text(encoding="utf-8"))


def load_all_bugsinpy_tasks(
    subset_path: Path,
    bugsinpy_root: Path = DEFAULT_BUGSINPY_ROOT,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> list[BugsInPyTask]:
    """Load all tasks from the frozen subset."""
    subset = load_bugsinpy_subset(subset_path)
    tasks = []
    for entry in subset:
        project = entry["project"]
        bug_id = str(entry["bug_id"])
        try:
            task = load_bugsinpy_task(
                project, bug_id, bugsinpy_root, workspace_root, cache_root,
            )
            task.category = entry.get("category", task.category)
            task.difficulty = entry.get("difficulty", task.difficulty)
            tasks.append(task)
        except Exception as exc:
            logger.warning("Failed to load %s:%s: %s", project, bug_id, exc)
    return tasks
