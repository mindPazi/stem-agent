from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.tools import (
    get_ast,
    get_diff,
    get_traceback,
    list_functions,
    read_file,
    run_tests,
    search_code,
)

SIMPLE_BUGGY = """\
def add(a, b):
    return a - b
"""

SIMPLE_FIXED = """\
def add(a, b):
    return a + b
"""

SIMPLE_TEST = """\
from solution import add

def test_add():
    assert add(1, 2) == 3

def test_zero():
    assert add(0, 0) == 0
"""


@pytest.fixture()
def task_dir(tmp_path: Path) -> Path:
    (tmp_path / "buggy.py").write_text(SIMPLE_BUGGY, encoding="utf-8")
    (tmp_path / "fixed.py").write_text(SIMPLE_FIXED, encoding="utf-8")
    (tmp_path / "test_suite.py").write_text(SIMPLE_TEST, encoding="utf-8")
    return tmp_path


def test_read_file(task_dir: Path):
    content = read_file(str(task_dir))
    assert "def add" in content


def test_read_file_missing(task_dir: Path):
    result = read_file(str(task_dir), "nonexistent.py")
    assert "Error" in result


def test_run_tests_buggy_fails(task_dir: Path):
    output = run_tests(str(task_dir))
    assert "FAILED" in output or "failed" in output or "error" in output.lower()


def test_run_tests_with_fix(task_dir: Path):
    output = run_tests(str(task_dir), solution_code=SIMPLE_FIXED)
    assert "passed" in output or "1 passed" in output


def test_search_code(task_dir: Path):
    result = search_code(str(task_dir), r"return a")
    assert "Line" in result
    assert "return a" in result


def test_search_code_no_match(task_dir: Path):
    result = search_code(str(task_dir), r"xyz_not_present")
    assert "No matches" in result


def test_get_ast(task_dir: Path):
    result = get_ast(str(task_dir))
    assert "FunctionDef" in result


def test_get_diff(task_dir: Path):
    result = get_diff(str(task_dir), SIMPLE_BUGGY, SIMPLE_FIXED)
    assert "-" in result and "+" in result


def test_get_diff_no_change(task_dir: Path):
    result = get_diff(str(task_dir), SIMPLE_BUGGY, SIMPLE_BUGGY)
    assert "No differences" in result


def test_list_functions(task_dir: Path):
    result = list_functions(str(task_dir))
    assert "add" in result
    assert "Line" in result


def test_get_traceback(task_dir: Path):
    result = get_traceback(str(task_dir))
    assert len(result) > 0


def test_run_tests_timeout(task_dir: Path):
    infinite = "import time\nfrom solution import add\ndef test_loop():\n    while True: pass\n"
    (task_dir / "test_suite.py").write_text(infinite, encoding="utf-8")
    output = run_tests(str(task_dir), timeout=3)
    assert "timeout" in output.lower() or "Error" in output
