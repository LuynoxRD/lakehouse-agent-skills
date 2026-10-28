"""Tests for the shipped-script sync and its parity check.

A per-skill install copies the skill's directory and nothing above it, so a script kept only in
this repository's `scripts/` is a script the consumer never receives. These copies are what
actually ships, which makes drift between a copy and its source the failure that matters: two
versions of the same check exist and only one of them was ever fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sync_skill_scripts as sync
import validate_skill_scripts as validate
from conftest import SKILL_A, SKILL_B, write
from lib.repo import Layout

SCRIPT = "verify-output.sh"
BODY = "#!/usr/bin/env bash\nset -euo pipefail\necho '{}'\n"


@pytest.fixture
def packaged(repo: Layout) -> Layout:
    """A repository with one shippable script and one skill that asks for it."""
    write(sync.source_directory(repo) / SCRIPT, BODY)
    document = repo.skills / SKILL_A / "SKILL.md"
    document.write_text(
        document.read_text(encoding="utf-8") + f"\nRun `scripts/{SCRIPT}` at the end.\n",
        encoding="utf-8",
        newline="\n",
    )
    return repo


def shipped(layout: Layout, skill: str) -> object:
    return layout.skills / skill / "scripts" / SCRIPT


def test_sync_writes_the_copy_into_the_skill_that_asks_for_it(packaged: Layout) -> None:
    assert sync.main(["--root", str(packaged.root)]) == 0

    target = packaged.skills / SKILL_A / "scripts" / SCRIPT
    assert target.read_text(encoding="utf-8") == BODY


def test_sync_leaves_a_skill_that_never_names_it_alone(packaged: Layout) -> None:
    sync.main(["--root", str(packaged.root)])

    assert not (packaged.skills / SKILL_B / "scripts").exists()


def test_a_missing_copy_fails_the_check(
    packaged: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """The instruction is unrunnable for everyone who installed that skill on its own."""
    assert validate.main(["--root", str(packaged.root)]) == 1
    assert "skill-scripts/missing" in capsys.readouterr().out


def test_a_drifted_copy_fails_the_check(
    packaged: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """Comparing that the file exists would pass this. The bytes are compared for that reason."""
    sync.main(["--root", str(packaged.root)])
    target = packaged.skills / SKILL_A / "scripts" / SCRIPT
    target.write_text(BODY + "echo 'edited in place'\n", encoding="utf-8", newline="\n")
    capsys.readouterr()

    assert validate.main(["--root", str(packaged.root)]) == 1
    assert "skill-scripts/drift" in capsys.readouterr().out


def test_a_copy_nobody_names_fails_the_check(
    packaged: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """Weight the install carries and nothing invokes."""
    write(packaged.skills / SKILL_B / "scripts" / SCRIPT, BODY)
    capsys.readouterr()

    assert validate.main(["--root", str(packaged.root)]) == 1
    assert "skill-scripts/unreferenced" in capsys.readouterr().out


def test_sync_removes_a_copy_once_the_skill_stops_naming_it(packaged: Layout) -> None:
    sync.main(["--root", str(packaged.root)])
    document = packaged.skills / SKILL_A / "SKILL.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(f"scripts/{SCRIPT}", "nothing"),
        encoding="utf-8",
        newline="\n",
    )

    assert sync.main(["--root", str(packaged.root)]) == 0
    assert not (packaged.skills / SKILL_A / "scripts").exists()


def test_sync_is_idempotent(packaged: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    """A second run must report nothing, or a clean tree looks like a pending change."""
    sync.main(["--root", str(packaged.root)])
    capsys.readouterr()

    assert sync.main(["--root", str(packaged.root)]) == 0
    assert "sync/written" not in capsys.readouterr().out


def test_the_real_repository_ships_what_its_skills_name() -> None:
    """The check that matters: this repository, as committed."""
    root = Path(__file__).resolve().parents[1]
    assert validate.validate(Layout(root)).exit_code == 0


@pytest.mark.parametrize("name", ["setup.sh", "helper.py"])
def test_a_shipped_file_with_no_source_fails_the_check(
    packaged: Layout, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    """Nothing compares it with anything, and a review skips the directory as generated copies."""
    sync.main(["--root", str(packaged.root)])
    write(packaged.skills / SKILL_A / "scripts" / name, BODY)
    capsys.readouterr()

    assert validate.main(["--root", str(packaged.root)]) == 1
    assert "skill-scripts/no-source" in capsys.readouterr().out
