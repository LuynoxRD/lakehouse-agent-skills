"""Tests for the fixture validator."""

from __future__ import annotations

import shutil

import pytest

import validate_fixtures
from conftest import FIXTURE_NOTE, SKILL_A, SKILL_B, write
from lib.repo import REPO_ROOT, Layout


def findings(layout: Layout) -> dict[str, str]:
    return {f.rule: f.severity.value for f in validate_fixtures.validate(layout).findings}


def test_fixtures_are_excluded_from_line_ending_normalization() -> None:
    """A fixture's bytes are the fixture.

    `.gitattributes` sets `text=auto eol=lf` repository-wide, which rewrites a CRLF export to
    LF on commit and deletes the very defect a fixture was built to carry. The exclusion is an
    invariant of the repository, so it is asserted rather than trusted.
    """
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "evals/fixtures/** -text" in attributes


def test_valid_fixtures_are_clean(repo: Layout) -> None:
    report = validate_fixtures.validate(repo)
    assert report.findings == []
    assert report.checked == 2


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_fixtures.main(["--root", str(repo.root)]) == 0
    assert "validate-fixtures: 2 checked" in capsys.readouterr().out


def test_every_skill_needs_its_own_fixture_folder(repo: Layout) -> None:
    shutil.rmtree(repo.eval_fixtures / SKILL_B)
    assert findings(repo)["fixture/missing-folder"] == "error"


def test_fixture_paths_may_not_escape_the_fixture_tree(repo: Layout) -> None:
    # The behavioral runner copies these files into the agent's workspace, so a path that
    # walks out of evals/fixtures/ would smuggle repository files into an eval.
    case = repo.eval_cases / f"{SKILL_A}.json"
    write(case, case.read_text().replace(f"{SKILL_A}/sales.csv", "../../pyproject.toml"))
    assert findings(repo)["fixture/outside-tree"] == "error"


def test_note_rules(repo: Layout) -> None:
    note = repo.eval_fixtures / SKILL_A / "FIXTURE.md"
    note.unlink()
    assert findings(repo)["fixture/missing-note"] == "error"
    write(note, "# Note\n\n## Provenance\n\nMade up by hand.\n\n## Traps\n\n- none\n")
    assert findings(repo)["fixture/provenance-statement"] == "error"
    write(note, "# Note\n\nSynthetic data.\n")
    found = findings(repo)
    assert found["fixture/provenance-section"] == "error"
    assert found["fixture/traps-section"] == "error"


def test_executables_and_size(repo: Layout) -> None:
    folder = repo.eval_fixtures / SKILL_A
    write(folder / "run.sh", "#!/usr/bin/env bash\n")
    write(folder / "helper.py", "print(1)\n")
    write(folder / "generate.py", "print('ok')\n")
    write(folder / "macro.xlsm", "x")
    found = [f for f in validate_fixtures.validate(repo).findings if f.rule == "fixture/executable"]
    assert sorted(f.path.name for f in found if f.path) == ["helper.py", "macro.xlsm", "run.sh"]
    (folder / "big.csv").write_bytes(b"0" * (validate_fixtures.MAX_FIXTURE_BYTES + 1))
    assert findings(repo)["fixture/too-large"] == "error"


def test_orphan_folder_and_stray_file(repo: Layout) -> None:
    write(repo.eval_fixtures / "unknown-skill" / "FIXTURE.md", FIXTURE_NOTE)
    write(repo.eval_fixtures / "loose.csv", "a,b\n")
    found = findings(repo)
    assert found["fixture/orphan"] == "error"
    assert found["fixture/stray-file"] == "warning"
    assert found["fixture/unreferenced"] == "warning"


def test_case_referencing_missing_fixture(repo: Layout) -> None:
    case = repo.eval_cases / f"{SKILL_A}.json"
    write(case, case.read_text().replace(f"{SKILL_A}/sales.csv", f"{SKILL_A}/absent.csv"))
    found = findings(repo)
    assert found["fixture/missing"] == "error"


def test_schema_errors_surface_here_too(repo: Layout) -> None:
    write(repo.eval_cases / f"{SKILL_A}.json", "{ broken")
    assert findings(repo)["case/unreadable"] == "error"
