"""Tests for the per-tool persona copies and their parity check.

`agents/` is read by one tool. The other three read their own directories, in their own
frontmatter, and each expresses the no-editing guarantee with a different field. That makes these
copies a translation rather than a duplication, and it makes a drifted copy the failure that
matters: the field carrying the guarantee is exactly the field a hand edit gets wrong, and a
reviewer that quietly regained write access raises nothing when it does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sync_agents as sync
import validate_agent_copies as validate
from conftest import write
from lib.repo import Layout

NAME = "data-work-reviewer"
DESCRIPTION = (
    "Reviews finished data work against the artifacts it left behind, reporting which "
    "verification claims are backed by evidence and which are assertions. Use after a profile, "
    "clean, model or disclose step."
)
BODY = "\n# Data work reviewer\n\nYou review data work that is already done.\n"


@pytest.fixture
def staffed(repo: Layout) -> Layout:
    """A repository with one persona and no copies yet."""
    write(
        repo.agents / f"{NAME}.md",
        f"---\nname: {NAME}\ndescription: {DESCRIPTION}\nmodel: inherit\ncolor: cyan\n"
        f'tools: ["Read", "Grep", "Glob", "Bash"]\n---\n{BODY}',
    )
    return repo


def copy(layout: Layout, tool: str) -> Path:
    return layout.root.joinpath(*sync.TARGETS[tool].directory) / f"{NAME}.md"


def test_one_persona_reaches_every_supported_tool(staffed: Layout) -> None:
    assert sync.main(["--root", str(staffed.root)]) == 0

    for tool in sync.TARGETS:
        assert copy(staffed, tool).is_file(), tool


def test_the_opencode_copy_denies_editing_and_never_says_tools(staffed: Layout) -> None:
    """The load-bearing translation.

    opencode has no `tools` field, and it does not reject the ones it does not know: an unknown
    key is routed into `options` in silence. A copy carrying `tools` would look correct in review
    and grant the reviewer everything.
    """
    sync.main(["--root", str(staffed.root)])
    text = copy(staffed, "opencode").read_text(encoding="utf-8")

    assert "permission:\n  edit: deny\n" in text
    assert "tools" not in text.split("---")[1]
    assert "mode: subagent" in text
    assert "color: '#06B6D4'" in text
    # The name comes from the filename there, so carrying it would be a field nothing reads.
    assert "name:" not in text.split("---")[1]


def test_the_cursor_copy_is_readonly(staffed: Layout) -> None:
    sync.main(["--root", str(staffed.root)])
    front = copy(staffed, "cursor").read_text(encoding="utf-8").split("---")[1]

    assert "readonly: true" in front
    assert f"name: {NAME}" in front


def test_the_gemini_copy_grants_only_confirmed_tool_names(staffed: Layout) -> None:
    """An allowlist entry that does not exist removes a tool rather than granting one."""
    sync.main(["--root", str(staffed.root)])
    front = copy(staffed, "gemini").read_text(encoding="utf-8").split("---")[1]

    assert "tools:\n" in front
    for tool in sync.GEMINI_TOOLS:
        assert f"  - {tool}\n" in front
    for absent in ("write_file", "replace", "edit_file", "glob"):
        assert absent not in front


def test_the_protocol_itself_is_carried_across_unchanged(staffed: Layout) -> None:
    """Only the frontmatter is translated. A persona that reviews differently per tool is two."""
    sync.main(["--root", str(staffed.root)])

    for tool in sync.TARGETS:
        assert copy(staffed, tool).read_text(encoding="utf-8").endswith(BODY), tool


def test_a_missing_copy_fails_the_check(
    staffed: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    assert validate.main(["--root", str(staffed.root)]) == 1
    assert "agent-copy/missing" in capsys.readouterr().out


def test_a_drifted_copy_fails_the_check(
    staffed: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    sync.main(["--root", str(staffed.root)])
    target = copy(staffed, "cursor")
    target.write_text(
        target.read_text(encoding="utf-8").replace("readonly: true", "readonly: false"),
        encoding="utf-8",
        newline="\n",
    )

    assert validate.main(["--root", str(staffed.root)]) == 1
    assert "agent-copy/drifted" in capsys.readouterr().out


def test_a_copy_no_persona_owns_is_reported_then_removed(
    staffed: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """A persona deleted here goes on running there, with the protocol it had before."""
    sync.main(["--root", str(staffed.root)])
    stray = copy(staffed, "opencode").with_name("retired-reviewer.md")
    write(stray, "---\nmode: subagent\n---\n\nstill here\n")

    assert validate.main(["--root", str(staffed.root)]) == 1
    assert "agent-copy/orphan" in capsys.readouterr().out

    sync.main(["--root", str(staffed.root)])
    assert not stray.exists()
    assert validate.main(["--root", str(staffed.root)]) == 0


def test_a_value_that_would_break_the_frontmatter_is_quoted() -> None:
    assert sync.scalar("plain text") == "plain text"
    assert sync.scalar("has: a colon") == "'has: a colon'"
    assert sync.scalar("it's quoted") == "'it''s quoted'"
    assert sync.scalar("#8B5CF6") == "'#8B5CF6'"
