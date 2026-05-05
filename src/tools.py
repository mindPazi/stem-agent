from __future__ import annotations

import ast
import difflib
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


def read_file(task_dir: str, filename: str = "buggy.py") -> str:
    path = Path(task_dir) / filename
    if not path.exists():
        return f"Error: {filename} not found in {task_dir}"
    return path.read_text(encoding="utf-8")


def run_tests(task_dir: str, solution_code: str | None = None, timeout: int = 30) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        task_path = Path(task_dir)

        shutil.copy(task_path / "test_suite.py", tmpdir / "test_suite.py")

        if solution_code is not None:
            (tmpdir / "solution.py").write_text(solution_code, encoding="utf-8")
        elif (task_path / "solution.py").exists():
            shutil.copy(task_path / "solution.py", tmpdir / "solution.py")
        else:
            shutil.copy(task_path / "buggy.py", tmpdir / "solution.py")

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "test_suite.py", "-v", "--tb=short", "--no-header"],
                cwd=tmpdir,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            output = result.stdout + result.stderr
            return output[-3000:] if len(output) > 3000 else output
        except subprocess.TimeoutExpired:
            return "Error: Tests timed out after 30 seconds"
        except Exception as e:
            return f"Error running tests: {e}"


def search_code(task_dir: str, pattern: str, filename: str = "buggy.py") -> str:
    path = Path(task_dir) / filename
    if not path.exists():
        return f"Error: {filename} not found"
    content = path.read_text(encoding="utf-8")
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(pattern, line):
            matches.append(f"Line {i}: {line}")
    return "\n".join(matches) if matches else "No matches found"


def get_ast(task_dir: str, filename: str = "buggy.py") -> str:
    path = Path(task_dir) / filename
    if not path.exists():
        return f"Error: {filename} not found"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return ast.dump(tree, indent=2)
    except SyntaxError as e:
        return f"SyntaxError: {e}"


def get_diff(task_dir: str, text_a: str, text_b: str) -> str:  # noqa: ARG001
    diff = difflib.unified_diff(
        text_a.splitlines(keepends=True),
        text_b.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
    )
    result = "".join(diff)
    return result if result else "No differences"


def list_functions(task_dir: str, filename: str = "buggy.py") -> str:
    path = Path(task_dir) / filename
    if not path.exists():
        return f"Error: {filename} not found"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return f"SyntaxError: {e}"
    fns = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            fns.append(f"Line {node.lineno}: def {node.name}({', '.join(args)})")
    return "\n".join(fns) if fns else "No functions found"


def get_traceback(task_dir: str, timeout: int = 30) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        task_path = Path(task_dir)
        shutil.copy(task_path / "test_suite.py", tmpdir / "test_suite.py")
        src = task_path / "solution.py" if (task_path / "solution.py").exists() else task_path / "buggy.py"
        shutil.copy(src, tmpdir / "solution.py")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "test_suite.py", "--tb=long", "-q", "--no-header"],
                cwd=tmpdir,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            output = result.stdout + result.stderr
            return output[-3000:] if len(output) > 3000 else output
        except subprocess.TimeoutExpired:
            return "Error: Tests timed out"
        except Exception as e:
            return f"Error: {e}"


TOOL_FUNCTIONS: dict[str, Callable] = {
    "read_file": read_file,
    "run_tests": run_tests,
    "search_code": search_code,
    "get_ast": get_ast,
    "get_diff": get_diff,
    "list_functions": list_functions,
    "get_traceback": get_traceback,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the task directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "File to read (default: buggy.py)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Execute the test suite and return stdout/stderr. Pass solution_code to test a specific fix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "solution_code": {
                        "type": "string",
                        "description": "Python code to test (uses buggy.py if omitted)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Regex search across a file in the task directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern"},
                    "filename": {"type": "string", "description": "File to search (default: buggy.py)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ast",
            "description": "Return the AST of a Python file as indented text",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File to parse (default: buggy.py)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_diff",
            "description": "Show unified diff between two strings",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_a": {"type": "string", "description": "Original text"},
                    "text_b": {"type": "string", "description": "Modified text"},
                },
                "required": ["text_a", "text_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_functions",
            "description": "List all function/method signatures in a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File to inspect (default: buggy.py)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_traceback",
            "description": (
                "Run pytest on the original buggy.py and return the full traceback. "
                "Note: this reflects the original bug, not any fix you have proposed — "
                "it is useful to understand what is failing, not to verify a candidate fix."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
