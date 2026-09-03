"""Tests for the fixture validator."""

from __future__ import annotations

import pytest

import validate_fixtures
from conftest import FIXTURE_NOTE, SKILL_A, write
from lib.repo import Layout


def findings(layout: Layout) -> dict[str, str]:
    return {f.rule: f.severity.value for f in validate_fixtures.validate(layout).findings}


def test_valid_fixtures_are_clean(repo: Layout) -> None:
    report = validate_fixtures.validate(repo)
    assert report.findings == []
    assert report.checked == 1


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_fixtures.main(["--root", str(repo.root)]) == 0
    assert "validate-fixtures: 1 checked" in capsys.readouterr().out


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
