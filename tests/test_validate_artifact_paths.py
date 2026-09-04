"""Tests for the canonical artifact path validator."""

from __future__ import annotations

import pytest

import validate_artifact_paths
from conftest import SKILL_A, write
from lib.artifact_paths import CANONICAL_DATA_PATHS, CANONICAL_NOTE_PATHS, find_violations
from lib.repo import Layout


def test_canonical_paths_are_accepted() -> None:
    text = " ".join(CANONICAL_NOTE_PATHS + CANONICAL_DATA_PATHS) + " data/raw/sales.csv docs/data/"
    assert find_violations(text) == []


def test_non_canonical_paths_are_reported_with_lines() -> None:
    text = "ok docs/data/profile.md\nbad docs/data/profiling.md\nbad data/cleaned/x.parquet\n"
    violations = find_violations(text)
    assert [(v.kind, v.value, v.line) for v in violations] == [
        ("note", "docs/data/profiling.md", 2),
        ("layer", "data/cleaned/", 3),
    ]
    assert violations[0].expected == CANONICAL_NOTE_PATHS
    assert violations[1].expected == CANONICAL_DATA_PATHS


def test_nested_paths_are_not_artifact_conventions() -> None:
    assert find_violations("evals/fixtures/skill/data/weird/file.csv and metadata/data/x/") == []
    assert find_violations("`docs/data/model.md`, then (docs/data/disclosure.md).") == []


def test_repo_validation(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_artifact_paths.validate(repo).findings == []
    path = repo.skills / SKILL_A / "SKILL.md"
    write(path, path.read_text().replace("data/clean/", "data/cleaned/"))
    report = validate_artifact_paths.validate(repo)
    assert [f.rule for f in report.findings] == ["artifacts/layer"]
    assert validate_artifact_paths.main(["--root", str(repo.root)]) == 1
    assert "data/cleaned/" in capsys.readouterr().out
