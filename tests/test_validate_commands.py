"""Tests for the command parity validator."""

from __future__ import annotations

import pytest

import validate_commands
from conftest import COMMAND_TOML, write
from lib.repo import Layout


def rules(layout: Layout) -> dict[str, str]:
    return {f.rule: f.severity.value for f in validate_commands.validate(layout).findings}


def test_valid_commands_are_clean(repo: Layout) -> None:
    report = validate_commands.validate(repo)
    assert report.findings == []
    assert report.checked == 1


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_commands.main(["--root", str(repo.root)]) == 0
    assert "validate-commands: 1 checked" in capsys.readouterr().out


def test_missing_copies(repo: Layout) -> None:
    (repo.claude_commands / "profile.md").unlink()
    (repo.gemini_commands / "profile.toml").unlink()
    report = validate_commands.validate(repo)
    assert [f.rule for f in report.findings] == ["command/missing-copy", "command/missing-copy"]


def test_description_and_prompt_drift(repo: Layout) -> None:
    write(
        repo.claude_commands / "profile.md",
        "---\ndescription: Something else.\n---\n\n"
        "Invoke the `etl-before-dashboard` skill differently.\n",
    )
    write(repo.gemini_commands / "profile.toml", COMMAND_TOML + "\n# drift\n")
    found = [f.rule for f in validate_commands.validate(repo).findings]
    assert found.count("command/description-drift") == 1
    assert found.count("command/prompt-drift") == 2


def test_source_shape_errors(repo: Layout) -> None:
    write(repo.commands / "profile.toml", 'description = ""\nprompt = "x"\n')
    assert rules(repo)["command/shape"] == "error"
    write(repo.commands / "profile.toml", "not toml at all = = =\n")
    assert rules(repo)["command/unreadable"] == "error"
    write(repo.commands / "profile.toml", COMMAND_TOML + 'extra = "field"\n')
    assert rules(repo)["command/shape"] == "warning"


def test_skill_references(repo: Layout) -> None:
    write(
        repo.commands / "profile.toml",
        'description = "Profile a dataset before cleaning or charting it."\n\n'
        'prompt = """\nJust do it with `top-k` settings.\n"""\n',
    )
    found = rules(repo)
    assert found["command/no-skill-reference"] == "error"
    assert found["command/unknown-skill"] == "warning"


def test_orphan_copies_and_bad_names(repo: Layout) -> None:
    write(repo.claude_commands / "ghost.md", "---\ndescription: x\n---\n\nbody\n")
    write(repo.gemini_commands / "ghost.toml", "description = 'x'\nprompt = 'y'\n")
    write(repo.commands / "Bad_Name.toml", COMMAND_TOML)
    write(repo.claude_commands / "Bad_Name.md", (repo.claude_commands / "profile.md").read_text())
    write(repo.gemini_commands / "Bad_Name.toml", COMMAND_TOML)
    found = [f.rule for f in validate_commands.validate(repo).findings]
    assert found.count("command/orphan-copy") == 2
    assert "command/name-format" in found


def test_copy_with_broken_frontmatter(repo: Layout) -> None:
    write(repo.claude_commands / "profile.md", "no frontmatter\n")
    assert rules(repo)["command/copy-frontmatter"] == "error"


def test_empty_command_set_only_flags_orphans(repo: Layout) -> None:
    (repo.commands / "profile.toml").unlink()
    found = [f.rule for f in validate_commands.validate(repo).findings]
    assert found == ["command/orphan-copy", "command/orphan-copy"]
