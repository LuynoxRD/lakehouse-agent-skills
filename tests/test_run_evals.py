"""Tests for the Tier 2 runner and its CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_evals
from conftest import DESCRIPTION_A, SKILL_A, SKILL_B, skill_markdown, write
from lib.evals_schema import load_cases
from lib.repo import Layout
from lib.report import Report


def tier2(layout: Layout) -> tuple[run_evals.Tier2Result, Report]:
    report = Report("run-evals")
    cases, schema = load_cases(layout)
    report.extend(schema.findings)
    catalog = run_evals.load_catalog(layout, report)
    config = run_evals.load_config(layout, report)
    return run_evals.run_tier2(cases, catalog, config, report), report


def test_valid_repo_passes_tier2(repo: Layout) -> None:
    result, report = tier2(repo)
    assert report.ok, report.render(repo.root)
    assert result.positives_total == 6
    assert result.positives_passed == 6
    assert result.negatives_total == 4
    assert result.negatives_passed == 4
    assert result.rank1_percent == 100.0


def test_cli_prints_summary_and_writes_json(
    repo: Layout, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_file = tmp_path / "out" / "tier2.json"
    assert run_evals.main(["--root", str(repo.root), "--json", str(out_file)]) == 0
    out = capsys.readouterr().out
    assert "tier2: rank-1 100.0% (floor 0%), positives 6/6, negatives 4/4" in out
    payload = json.loads(out_file.read_text())
    assert payload["tier"] == 2
    assert payload["rank1_percent"] == 100.0
    assert payload["positives"] == {"passed": 6, "total": 6}


def test_positive_failure_reports_rank(repo: Layout) -> None:
    case = repo.eval_cases / f"{SKILL_A}.json"
    document = json.loads(case.read_text())
    document["trigger"]["positive"][0] = {
        "prompt": "disclose memory limits and sampling",
        "top_k": 1,
    }
    write(case, json.dumps(document))
    result, report = tier2(repo)
    errors = [f for f in report.errors if f.rule == "tier2/positive"]
    assert len(errors) == 1
    assert "#2" in errors[0].message
    assert result.rank1_hits == 5


def test_negative_failure_and_unknown_owner(repo: Layout) -> None:
    case = repo.eval_cases / f"{SKILL_A}.json"
    document = json.loads(case.read_text())
    document["trigger"]["negative"][0] = {
        "prompt": "profile clean model persist visualize order",
        "owner": SKILL_B,
    }
    document["trigger"]["negative"][1] = {"prompt": "anything", "owner": "ghost-skill"}
    write(case, json.dumps(document))
    _, report = tier2(repo)
    rules = [f.rule for f in report.errors]
    assert "tier2/negative" in rules
    assert "tier2/owner-unknown" in rules


def test_collisions(repo: Layout) -> None:
    write(repo.skills / SKILL_B / "SKILL.md", skill_markdown(SKILL_B, DESCRIPTION_A))
    result, report = tier2(repo)
    assert result.collision_errors == 1
    assert any(f.rule == "tier2/collision" and f.severity.value == "error" for f in report.findings)


def test_rank1_floor(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    case = repo.eval_cases / f"{SKILL_A}.json"
    document = json.loads(case.read_text())
    document["trigger"]["positive"][0] = {
        "prompt": "disclose memory limits and sampling",
        "top_k": 3,
    }
    write(case, json.dumps(document))
    assert run_evals.main(["--root", str(repo.root), "--min-rank1", "90"]) == 1
    assert "tier2/rank1-floor" in capsys.readouterr().out
    assert run_evals.main(["--root", str(repo.root), "--min-rank1", "80"]) == 0


def test_config_loading(repo: Layout) -> None:
    report = Report("x")
    write(
        repo.eval_config,
        json.dumps({"min_rank1_percent": 70, "collision_error": 0.9, "unknown": 1}),
    )
    config = run_evals.load_config(repo, report)
    assert config.min_rank1_percent == 70.0
    assert config.collision_error == 0.9
    assert config.collision_warning == 0.5
    assert [f.rule for f in report.findings] == ["config/unknown-key"]
    repo.eval_config.unlink()
    report = Report("x")
    assert run_evals.load_config(repo, report).min_rank1_percent == 0.0
    assert [f.rule for f in report.findings] == ["config/missing"]
    write(repo.eval_config, json.dumps({"min_rank1_percent": "high"}))
    report = Report("x")
    run_evals.load_config(repo, report)
    assert [f.rule for f in report.findings] == ["config/shape"]


def test_empty_catalog_is_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert run_evals.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "tier2/empty" in out
    assert "rank-1 n/a" in out


def test_catalog_errors(repo: Layout) -> None:
    write(repo.skills / SKILL_B / "SKILL.md", "---\nname: x\n---\nno description\n")
    (repo.skills / "broken").mkdir()
    report = Report("x")
    catalog = run_evals.load_catalog(repo, report)
    assert set(catalog) == {SKILL_A}
    assert sorted(f.rule for f in report.findings) == [
        "catalog/description",
        "catalog/missing-skill-md",
    ]
