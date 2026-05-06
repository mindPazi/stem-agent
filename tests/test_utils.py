from __future__ import annotations

import os

from src.utils import load_env_file


def test_load_env_file_sets_missing_values(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# local secrets\n"
        "OPENAI_API_KEY='test-key'\n"
        "export OTHER_VALUE=abc\n",
        encoding="utf-8",
    )

    load_env_file(env_path)

    assert os.environ["OPENAI_API_KEY"] == "test-key"
    assert os.environ["OTHER_VALUE"] == "abc"


def test_load_env_file_does_not_override_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "already-set")
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")

    load_env_file(env_path)

    assert os.environ["OPENAI_API_KEY"] == "already-set"
