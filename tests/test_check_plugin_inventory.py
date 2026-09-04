"""Tests for the plugin inventory check.

The case that matters is the one that already happened. An `agents` field passed the manifest
validator, the install exited zero, and zero agents loaded, so three reviewer personas shipped in
the package with nothing reading them. It was found by a person reading the output of an install
by hand, which is a habit, and this file is what replaces the habit.
"""

from __future__ import annotations

import pytest

import check_plugin_inventory as inventory
from conftest import write
from lib.repo import Layout

AGENT = "---\nname: a-reviewer\ndescription: Reviews things.\n---\n\nBody\n"


class Stdin:
    """The smallest thing `sys.stdin.read()` needs to be."""

    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text


@pytest.fixture
def packaged(repo: Layout) -> Layout:
    """The miniature repository with a hook and a persona in it."""
    write(repo.hooks / "hooks.json", '{"hooks": {"SessionStart": []}}\n')
    write(repo.agents / "a-reviewer.md", AGENT)
    return repo


def sections(layout: Layout) -> tuple[str, str]:
    """The Skills and Agents lines a correct install would print for this repository."""
    expected = inventory.expected_components(layout)
    skills = ", ".join(sorted(expected["Skills"]))
    agents = ", ".join(sorted(expected["Agents"]))
    return (
        f"Skills ({len(expected['Skills'])})  {skills}",
        f"Agents ({len(expected['Agents'])})  {agents}",
    )


def inventory_text(skills: str, agents: str) -> str:
    return (
        "plugin 0.1.0\n"
        "  Description: something\n"
        "\n"
        "Component inventory\n"
        f"  {skills}\n"
        f"  {agents}\n"
        "  Hooks (1)  SessionStart  (harness-only, no model context cost)\n"
        "  MCP servers (0)\n"
        "  LSP servers (0)\n"
    )


def test_a_matching_inventory_passes(
    packaged: Layout, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    skills, agents = sections(packaged)
    monkeypatch.setattr("sys.stdin", Stdin(inventory_text(skills, agents)))

    assert inventory.main(["--root", str(packaged.root)]) == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_zero_agents_after_a_green_install_is_a_failure(
    packaged: Layout, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect verbatim: install green, section present, section empty."""
    skills, _ = sections(packaged)
    monkeypatch.setattr("sys.stdin", Stdin(inventory_text(skills, "Agents (0)")))

    code = inventory.main(["--root", str(packaged.root)])

    out = capsys.readouterr().out
    assert code == 1
    assert "Agents: 1 shipped, 0 loaded" in out
    assert "a-reviewer" in out


def test_a_component_swapped_for_another_is_caught_although_the_total_is_right(
    packaged: Layout, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Comparing totals would pass this. Names are compared for exactly this reason."""
    skills, _ = sections(packaged)
    monkeypatch.setattr("sys.stdin", Stdin(inventory_text(skills, "Agents (1)  someone-else")))

    assert inventory.main(["--root", str(packaged.root)]) == 1
    out = capsys.readouterr().out
    assert "loaded none of: a-reviewer" in out
    assert "loaded unexpectedly: someone-else" in out


def test_a_missing_skill_is_caught(
    packaged: Layout, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The colon defect in its other form: shipped in the tree, absent from the install."""
    _, agents = sections(packaged)
    expected = inventory.expected_components(packaged)
    kept = sorted(expected["Skills"])[1:]
    line = f"Skills ({len(kept)})  {', '.join(kept)}"
    monkeypatch.setattr("sys.stdin", Stdin(inventory_text(line, agents)))

    assert inventory.main(["--root", str(packaged.root)]) == 1
    assert "loaded none of:" in capsys.readouterr().out


def test_an_install_that_printed_no_inventory_is_refused(
    packaged: Layout, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Silence is the state this exists to refuse, so it cannot be the state that passes."""
    monkeypatch.setattr("sys.stdin", Stdin("Successfully installed plugin\n"))

    assert inventory.main(["--root", str(packaged.root)]) == 1
    assert "no component inventory found" in capsys.readouterr().out


def test_a_section_reported_with_a_count_and_no_names_still_fails() -> None:
    """A count without names is the shape that hid the defect; it must not read as a match."""
    parsed = inventory.parse_inventory("  Agents (3)\n")
    assert parsed["Agents"] == {"<3 unnamed>"}


def test_ansi_colour_and_the_hook_aside_do_not_confuse_the_parse() -> None:
    parsed = inventory.parse_inventory(
        "\x1b[1m  Skills (2)\x1b[0m  one, two\n"
        "  Agents (1)  a-reviewer\n"
        "  Hooks (1)  SessionStart  (harness-only, no model context cost)\n"
    )
    assert parsed["Skills"] == {"one", "two"}
    assert parsed["Agents"] == {"a-reviewer"}
    assert parsed["Hooks"] == {"SessionStart"}


def test_commands_are_expected_among_the_skills(packaged: Layout) -> None:
    """The inventory reports them together, so the expectation has to match that or always fail."""
    expected = inventory.expected_components(packaged)
    assert {path.name for path in packaged.skill_dirs()} <= expected["Skills"]
    assert {path.stem for path in packaged.commands.glob("*.toml")} <= expected["Skills"]


def test_the_file_option_reads_the_same_inventory(
    packaged: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    skills, agents = sections(packaged)
    path = write(packaged.root / "inventory.txt", inventory_text(skills, agents))
    assert inventory.main(["--root", str(packaged.root), "--inventory", str(path)]) == 0
    assert "3 checked" in capsys.readouterr().out
