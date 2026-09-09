"""Tests for the command copy generator.

The parity validator can only say that a copy drifted. This script is what stops it drifting, so
what matters here is that regenerating produces exactly what the validator accepts, and that a
copy nobody should keep is removed rather than left to fail the build later.
"""

from __future__ import annotations

import pytest

import sync_commands
import validate_commands
from conftest import COMMAND_TOML, write
from lib.repo import Layout


def test_regenerated_copies_are_what_the_validator_accepts(repo: Layout) -> None:
    (repo.claude_commands / "profile.md").unlink()
    (repo.gemini_commands / "profile.toml").unlink()
    assert validate_commands.validate(repo).errors

    report = sync_commands.sync(repo)
    assert not report.errors
    assert report.checked == 1
    assert validate_commands.validate(repo).findings == []


def test_a_drifted_copy_is_brought_back_rather_than_reported(repo: Layout) -> None:
    write(
        repo.claude_commands / "profile.md", "---\ndescription: Drifted.\n---\n\nSomething else.\n"
    )
    write(repo.gemini_commands / "profile.toml", COMMAND_TOML + "\n# hand edited\n")

    sync_commands.sync(repo)

    assert validate_commands.validate(repo).findings == []
    assert (repo.gemini_commands / "profile.toml").read_bytes() == (
        repo.commands / "profile.toml"
    ).read_bytes()


def test_a_copy_without_a_source_is_removed(repo: Layout) -> None:
    orphan_md = write(repo.claude_commands / "ghost.md", "---\ndescription: x\n---\n\nbody\n")
    orphan_toml = write(repo.gemini_commands / "ghost.toml", COMMAND_TOML)

    report = sync_commands.sync(repo)

    assert not orphan_md.exists()
    assert not orphan_toml.exists()
    assert [f.rule for f in report.findings].count("sync/removed") == 2


def test_writing_is_reported_only_when_the_bytes_change(repo: Layout) -> None:
    """A run that changes nothing says nothing, so a noisy run means a copy really had drifted."""
    sync_commands.sync(repo)
    assert sync_commands.sync(repo).findings == []


def test_copies_use_lf_endings(repo: Layout) -> None:
    """The repository is LF everywhere, and this script writes bytes on a platform that is not."""
    sync_commands.sync(repo)
    for path in (repo.claude_commands / "profile.md", repo.gemini_commands / "profile.toml"):
        assert b"\r\n" not in path.read_bytes()


def test_a_source_that_cannot_be_parsed_is_an_error_not_a_crash(repo: Layout) -> None:
    write(repo.commands / "broken.toml", 'description = "unterminated\n')
    report = sync_commands.sync(repo)
    assert "sync/unreadable" in {f.rule for f in report.findings}
    assert len(report.errors) == 1


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert sync_commands.main(["--root", str(repo.root)]) == 0
    assert "sync-commands: 1 checked" in capsys.readouterr().out


def test_a_stage_command_forks_and_the_others_do_not(repo: Layout) -> None:
    """profile is a stage command; a chart is not. The generator decides from one list, and the
    validator accepts exactly what the generator wrote."""
    write(repo.commands / "chart.toml", COMMAND_TOML)

    sync_commands.sync(repo)

    profile = (repo.claude_commands / "profile.md").read_text(encoding="utf-8")
    chart = (repo.claude_commands / "chart.md").read_text(encoding="utf-8")
    assert profile.startswith("---\ndescription: ")
    assert "\ncontext: fork\nbackground: false\n---\n" in profile
    assert "context:" not in chart
    assert "background:" not in chart
    assert validate_commands.validate(repo).findings == []
