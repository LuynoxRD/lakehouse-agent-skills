"""Tests for the Stop hook, run as a real process.

This is the only thing in the repository that can refuse to let a turn end, so the cases that
matter are the ones where it must not: no profile, a disclosure already written, a fresh receipt
from the artefact check, a payload it cannot read, a second turn in a session it already
interrupted. A hook that blocks when it should
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

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "stop-evidence.sh"
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
    assert [path.name for path in markers] == ["evidence-______escape"]


def test_the_reason_is_valid_json_even_with_quotes_in_the_paths(tmp_path: Path) -> None:
    """The payload is JSON, so anything embedded in it has to survive being escaped."""
    result = run(profiled(tmp_path / "project"), tmp_path / "tmp")

    json.loads(result.stdout)


def declared_figures(project: Path) -> Path:
    """A project where a run declared the numbers it publishes."""
    note = project / "docs" / "data" / "figures.json"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text('{"figures": []}\n', encoding="utf-8")
    return project


def receipt(project: Path) -> Path:
    """What verify-output.sh leaves behind when it finishes with zero errors."""
    path = project / "docs" / "data" / "verification.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"ok": true}\n', encoding="utf-8")
    return path


def test_declared_figures_with_no_receipt_are_sent_back(tmp_path: Path) -> None:
    """The checklist box said the check was run. Nothing on disk agrees."""
    project = declared_figures(tmp_path / "project")
    (project / "docs" / "data" / "disclosure.md").write_text("# D\n", encoding="utf-8")

    reason = blocked(run(project, tmp_path / "tmp"))

    assert "docs/data/verification.json" in reason
    assert "zero errors" in reason


def test_declared_figures_with_a_fresh_receipt_are_left_alone(tmp_path: Path) -> None:
    project = declared_figures(tmp_path / "project")
    receipt(project)

    approved(run(project, tmp_path / "tmp"))


def test_a_receipt_older_than_the_page_is_sent_back(tmp_path: Path) -> None:
    """Checked, then the page changed. The receipt describes a file that no longer exists."""
    project = declared_figures(tmp_path / "project")
    path = receipt(project)
    page = project / "dashboard.html"
    page.write_text("<!doctype html><html><body>x</body></html>\n", encoding="utf-8")
    stamp = path.stat().st_mtime
    os.utime(page, (stamp + 10, stamp + 10))

    reason = blocked(run(project, tmp_path / "tmp"))

    assert "dashboard.html" in reason
    assert "have changed since" in reason


def test_a_note_edited_after_the_check_is_sent_back(tmp_path: Path) -> None:
    """Found by audit. The receipt records a digest for the disclosure, so rewriting it after a
    green run makes the receipt describe a file that no longer exists in that form. Watching only
    the pages left the one artefact somebody has a motive to inflate outside the comparison."""
    project = declared_figures(tmp_path / "project")
    path = receipt(project)
    note = project / "docs" / "data" / "disclosure.md"
    note.write_text("Processed 8 of 8 inputs.\n", encoding="utf-8")
    stamp = path.stat().st_mtime
    os.utime(note, (stamp + 10, stamp + 10))

    reason = blocked(run(project, tmp_path / "tmp"))

    assert "disclosure.md" in reason
    assert "have changed since" in reason


def test_a_receipt_newer_than_the_page_is_left_alone(tmp_path: Path) -> None:
    project = declared_figures(tmp_path / "project")
    page = project / "dashboard.html"
    page.write_text("<!doctype html><html><body>x</body></html>\n", encoding="utf-8")
    path = receipt(project)
    stamp = page.stat().st_mtime
    os.utime(path, (stamp + 10, stamp + 10))

    approved(run(project, tmp_path / "tmp"))


def test_a_project_with_no_declared_figures_is_not_asked_for_a_receipt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "dashboard.html").write_text("<!doctype html><html></html>\n", encoding="utf-8")

    approved(run(project, tmp_path / "tmp"))


def test_both_omissions_are_reported_in_one_interruption(tmp_path: Path) -> None:
    """One block per session, so it has to say everything that is missing."""
    project = declared_figures(profiled(tmp_path / "project"))

    reason = blocked(run(project, tmp_path / "tmp"))

    assert "docs/data/disclosure.md" in reason
    assert "docs/data/verification.json" in reason


PAGE_SKILLS = (
    "dashboard-layout-by-widget-mix",
    "dashboard-color-and-visual-hierarchy",
    "dashboard-visual-craft",
)


def transcript(tmp_path: Path, *skills: str) -> Path:
    """A session transcript in the shape the tool writes: one JSON object per line, and a skill
    invocation is a tool call named Skill whose input names the skill, namespaced by the plugin."""
    path = tmp_path / "transcript.jsonl"
    lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "build the page"}})]
    for skill in skills:
        block = {
            "type": "tool_use",
            "id": "toolu_1",
            "name": "Skill",
            "input": {"skill": f"lakehouse-agent-skills:{skill}", "args": ""},
        }
        message = {"type": "assistant", "message": {"role": "assistant", "content": [block]}}
        lines.append(json.dumps(message, separators=(",", ":")))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def payload_naming(path: Path, session: str = "session-one") -> str:
    """The event payload as the tool sends it, with the transcript path JSON-escaped."""
    return json.dumps({"session_id": session, "transcript_path": str(path)})


def delivered_page(project: Path) -> Path:
    """A page declared and checked green, so every other fact the hook looks for is present."""
    declared_figures(project)
    receipt(project)
    return project


def test_a_declared_page_whose_craft_skill_never_ran_is_sent_back(tmp_path: Path) -> None:
    """The run that produced this: a page built, checked green and reviewed, with the skill that
    owns how it reads never invoked, and nothing anywhere able to see that."""
    project = delivered_page(tmp_path / "project")
    log = transcript(tmp_path, *PAGE_SKILLS[:2])

    reason = blocked(run(project, tmp_path / "tmp", payload_naming(log)))

    assert "no invocation of: dashboard-visual-craft." in reason
    assert "on the file that was written" in reason


def test_a_declared_page_with_every_skill_in_the_transcript_is_left_alone(tmp_path: Path) -> None:
    project = delivered_page(tmp_path / "project")
    log = transcript(tmp_path, *PAGE_SKILLS)

    approved(run(project, tmp_path / "tmp", payload_naming(log)))


def test_every_missing_skill_is_named_in_one_interruption(tmp_path: Path) -> None:
    project = delivered_page(tmp_path / "project")
    log = transcript(tmp_path)

    reason = blocked(run(project, tmp_path / "tmp", payload_naming(log)))

    for skill in PAGE_SKILLS:
        assert skill in reason


def test_a_payload_without_a_transcript_path_skips_the_skill_check(tmp_path: Path) -> None:
    """A transcript the hook cannot find is not evidence that a skill did not run."""
    project = delivered_page(tmp_path / "project")

    approved(run(project, tmp_path / "tmp"))


def test_a_transcript_that_is_not_there_skips_the_skill_check(tmp_path: Path) -> None:
    project = delivered_page(tmp_path / "project")

    approved(run(project, tmp_path / "tmp", payload_naming(tmp_path / "missing.jsonl")))


def test_a_skill_named_in_a_message_does_not_count_as_invoked(tmp_path: Path) -> None:
    """The hook's own reason reaches the transcript as a message naming the skills. A reminder that
    satisfied itself on the next turn would be worse than none."""
    project = delivered_page(tmp_path / "project")
    log = transcript(tmp_path, *PAGE_SKILLS[:2])
    feedback = {
        "type": "user",
        "message": {
            "role": "user",
            "content": "Stop hook feedback: shows no invocation of: dashboard-visual-craft. "
            'The "name": "Skill" tool with "skill": "dashboard-visual-craft" was not called.',
        },
    }
    log.write_text(log.read_text(encoding="utf-8") + json.dumps(feedback) + "\n", encoding="utf-8")

    reason = blocked(run(project, tmp_path / "tmp", payload_naming(log)))

    assert "dashboard-visual-craft" in reason


def test_a_project_with_no_declared_figures_never_asks_about_skills(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    log = transcript(tmp_path)

    approved(run(project, tmp_path / "tmp", payload_naming(log)))
