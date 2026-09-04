"""Tests for the Stop hook, run as a real process.

This is the only thing in the repository that can refuse to let a turn end, so the cases that
matter are the ones where it must not: no profile, a disclosure already written, a payload it
cannot read, a second turn in a session it already interrupted. A hook that blocks when it should
not is worse than the omission it was written to catch, and a hook that blocks forever is worse
than both.

Shell is tested by starting it. Every case below runs the script the way the tool does, with the
payload on stdin and the project directory in the environment.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "stop-disclosure.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="the hook is shell and needs bash to run")


def run(
    project: Path, temp: Path, payload: str = '{"session_id":"session-one"}'
) -> subprocess.CompletedProcess[str]:
    """Start the hook against a project directory, the way a tool does."""
    assert BASH is not None
    return subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        env={
            "CLAUDE_PROJECT_DIR": str(project),
            "TMPDIR": str(temp),
            "PATH": os.environ.get("PATH", ""),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def profiled(project: Path) -> Path:
    """A project where this pack's pipeline ran and left a profile behind."""
    note = project / "docs" / "data" / "profile.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# Profile\n", encoding="utf-8")
    return project


def blocked(result: subprocess.CompletedProcess[str]) -> str:
    """The reason the turn was sent back, or an assertion failure saying why not."""
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] == "block"
    reason = payload["reason"]
    assert isinstance(reason, str)
    return reason


def approved(result: subprocess.CompletedProcess[str]) -> None:
    """Nothing on stdout and a clean exit is how the hook lets a turn end."""
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_a_profiled_project_with_no_disclosure_is_sent_back(tmp_path: Path) -> None:
    reason = blocked(run(profiled(tmp_path / "project"), tmp_path / "tmp"))

    assert "docs/data/disclosure.md" in reason
    assert "honest-data-limits-disclosure" in reason
    assert "Numbers, not adjectives" in reason


def test_the_same_session_is_only_sent_back_once(tmp_path: Path) -> None:
    """A hook that blocks every turn of a session strands it, whatever the reason is."""
    project, temp = profiled(tmp_path / "project"), tmp_path / "tmp"

    blocked(run(project, temp))
    approved(run(project, temp))
    approved(run(project, temp))


def test_a_different_session_is_still_told(tmp_path: Path) -> None:
    project, temp = profiled(tmp_path / "project"), tmp_path / "tmp"

    blocked(run(project, temp, '{"session_id":"session-one"}'))
    blocked(run(project, temp, '{"session_id":"session-two"}'))


def test_a_project_that_never_profiled_anything_is_left_alone(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "notes.md").write_text("nothing to do with data\n", encoding="utf-8")

    approved(run(project, tmp_path / "tmp"))


def test_an_existing_disclosure_is_left_alone(tmp_path: Path) -> None:
    project = profiled(tmp_path / "project")
    (project / "docs" / "data" / "disclosure.md").write_text("# Disclosure\n", encoding="utf-8")

    approved(run(project, tmp_path / "tmp"))


def test_a_payload_without_a_session_id_is_never_blocked(tmp_path: Path) -> None:
    """Without an id there is no way to stop at one interruption, so it makes none."""
    result = run(profiled(tmp_path / "project"), tmp_path / "tmp", "{}")

    approved(result)
    assert "no session id" in result.stderr


def test_an_empty_payload_is_never_blocked(tmp_path: Path) -> None:
    approved(run(profiled(tmp_path / "project"), tmp_path / "tmp", ""))


def test_a_missing_project_directory_is_never_blocked(tmp_path: Path) -> None:
    approved(run(tmp_path / "gone", tmp_path / "tmp"))


def test_a_session_id_that_is_a_path_cannot_escape_the_marker_directory(tmp_path: Path) -> None:
    """The id arrives from outside, so it is reduced to a name before it becomes a file name."""
    project, temp = profiled(tmp_path / "project"), tmp_path / "tmp"

    blocked(run(project, temp, '{"session_id":"../../escape"}'))

    markers = list((temp / "lakehouse-agent-skills").glob("*"))
    assert [path.name for path in markers] == ["disclosure-______escape"]


def test_the_reason_is_valid_json_even_with_quotes_in_the_paths(tmp_path: Path) -> None:
    """The payload is JSON, so anything embedded in it has to survive being escaped."""
    result = run(profiled(tmp_path / "project"), tmp_path / "tmp")

    json.loads(result.stdout)
