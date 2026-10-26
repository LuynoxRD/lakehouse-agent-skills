"""Tests for the per-tool persona copies and their parity check.

`agents/` is read by one tool. The other four read their own directories, in their own format —
one of them is not even markdown — and each expresses the no-editing guarantee with a different
field. That makes these
copies a translation rather than a duplication, and it makes a drifted copy the failure that
matters: the field carrying the guarantee is exactly the field a hand edit gets wrong, and a
reviewer that quietly regained write access raises nothing when it does.
"""

from __future__ import annotations

import tomllib
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
        f'tools: ["Read", "Grep", "Glob", "Bash"]\nomitClaudeMd: true\n---\n{BODY}',
    )
    return repo


def copy(layout: Layout, tool: str) -> Path:
    target = sync.TARGETS[tool]
    return layout.root.joinpath(*target.directory) / (NAME + target.suffix)


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


def test_a_key_only_claude_code_reads_stays_out_of_every_copy(staffed: Layout) -> None:
    """opencode routes a key it does not know into `options` in silence, so carrying
    `omitClaudeMd` across would put a field there that nothing reads."""
    sync.main(["--root", str(staffed.root)])

    for tool in sync.TARGETS:
        assert "omitClaudeMd" not in copy(staffed, tool).read_text(encoding="utf-8"), tool


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


def test_the_codex_copy_is_toml_and_sandboxed_read_only(staffed: Layout) -> None:
    """Codex is not markdown at all, and its restriction is a sandbox rather than a tool list.

    That makes it the strongest of the four: `read-only` covers the shell, which is the hole every
    other format leaves open and which these personas name in their own text.
    """
    sync.main(["--root", str(staffed.root)])
    document = tomllib.loads(copy(staffed, "codex").read_text(encoding="utf-8"))

    assert document["sandbox_mode"] == "read-only"
    assert document["name"] == NAME
    assert document["description"] == DESCRIPTION
    assert "You review data work that is already done." in document["developer_instructions"]


def test_the_protocol_itself_is_carried_across_unchanged(staffed: Layout) -> None:
    """Only the wrapper is translated. A persona that reviews differently per tool is two."""
    sync.main(["--root", str(staffed.root)])

    for tool, target in sync.TARGETS.items():
        text = copy(staffed, tool).read_text(encoding="utf-8")
        if target.suffix == ".toml":
            assert BODY.strip() in tomllib.loads(text)["developer_instructions"], tool
        else:
            assert text.endswith(BODY), tool


def test_a_protocol_that_would_close_the_toml_string_is_refused(
    staffed: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """The Codex copy carries the protocol inside a literal string, so one sequence cannot appear.

    Escaping it would silently change the text a reviewer is given. Refusing it asks for one line
    to be rewritten instead, which is the only outcome where all five copies still say the same.
    """
    source = staffed.agents / f"{NAME}.md"
    source.write_text(
        source.read_text(encoding="utf-8") + f"\nA fence {sync.TOML_FENCE} in the prose.\n",
        encoding="utf-8",
        newline="\n",
    )

    assert sync.main(["--root", str(staffed.root)]) == 1
    assert "agents/unquotable" in capsys.readouterr().out


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
