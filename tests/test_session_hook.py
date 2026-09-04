"""Tests for the session-start hook, run as a real process.

The hook is shell, so testing it any other way tests a description of it. Every case here starts
the script the way a tool would, with a project directory in the environment, and reads what came
back on each stream. That is the contract: JSON on stdout, status on stderr, and never a non-zero
exit, because a reminder that blocks somebody's session is worse than no reminder.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session-start.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="the hook is shell and needs bash to run")


def run(project: Path) -> subprocess.CompletedProcess[str]:
    """Start the hook against a project directory, the way a tool does."""
    assert BASH is not None
    return subprocess.run(
        [BASH, str(HOOK)],
        env={"CLAUDE_PROJECT_DIR": str(project), "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def message(result: subprocess.CompletedProcess[str]) -> str:
    """The context the hook asked to have added, or an assertion failure saying why not."""
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    text = payload["hookSpecificOutput"]["systemMessage"]
    assert isinstance(text, str)
    return text


def test_data_without_a_profile_is_reported(tmp_path: Path) -> None:
    (tmp_path / "exports").mkdir()
    (tmp_path / "orders.csv").write_text("a,b\n", encoding="utf-8")
    (tmp_path / "exports" / "q1.xlsx").write_bytes(b"not really a workbook")
    (tmp_path / "exports" / "events.parquet").write_bytes(b"not really parquet")

    text = message(run(tmp_path))

    assert "3 data file(s)" in text
    assert "orders.csv" in text
    assert "exports/q1.xlsx" in text
    # The names are a readable list, not a run-together string.
    assert "orders.csv, " in text or ", orders.csv" in text
    assert "using-lakehouse-skills" in text


def test_a_project_with_a_profile_says_nothing(tmp_path: Path) -> None:
    (tmp_path / "orders.csv").write_text("a,b\n", encoding="utf-8")
    (tmp_path / "docs" / "data").mkdir(parents=True)
    (tmp_path / "docs" / "data" / "profile.md").write_text("# Profile\n", encoding="utf-8")

    result = run(tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "nothing to say" in result.stderr


def test_a_project_with_no_data_says_nothing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# A project\n", encoding="utf-8")

    result = run(tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_dependency_directories_are_not_counted(tmp_path: Path) -> None:
    """A virtualenv full of test data is not this project's unprofiled data."""
    for directory in ("node_modules", ".venv", ".git"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "sample.csv").write_text("a\n", encoding="utf-8")

    result = run(tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_many_files_are_summarised_rather_than_listed(tmp_path: Path) -> None:
    for index in range(12):
        (tmp_path / f"export_{index:02d}.csv").write_text("a\n", encoding="utf-8")

    text = message(run(tmp_path))

    assert "12 data file(s)" in text
    assert "and 7 more" in text
    assert text.count(".csv") == 5


def test_a_missing_project_directory_does_not_fail_the_session(tmp_path: Path) -> None:
    result = run(tmp_path / "does-not-exist")

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "no project directory" in result.stderr


def test_a_quote_in_a_file_name_does_not_break_the_json(tmp_path: Path) -> None:
    """The message is interpolated into JSON, so a name with a quote in it is the shape to check."""
    try:
        (tmp_path / 'we"ird.csv').write_text("a\n", encoding="utf-8")
    except OSError:  # pragma: no cover - some filesystems refuse the character
        pytest.skip("this filesystem does not allow a quote in a file name")

    text = message(run(tmp_path))

    assert 'we"ird.csv' in text
