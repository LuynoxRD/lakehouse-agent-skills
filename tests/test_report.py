"""Tests for findings, reports and exit codes."""

from __future__ import annotations

from pathlib import Path

from lib.report import Finding, Report, Severity


def test_exit_code_follows_errors_only() -> None:
    report = Report("demo")
    assert report.ok
    assert report.exit_code == 0
    report.warning("rule/w", "soft")
    assert report.exit_code == 0
    report.error("rule/e", "hard")
    assert report.exit_code == 1
    assert len(report.errors) == 1
    assert len(report.warnings) == 1


def test_render_is_sorted_and_relative(tmp_path: Path) -> None:
    report = Report("demo", checked=2)
    report.error("rule/b", "second", tmp_path / "b.md", 4)
    report.warning("rule/a", "first", tmp_path / "a.md", 9)
    report.error("rule/a", "earlier line", tmp_path / "b.md", 2)
    rendered = report.render(tmp_path, github=False).split("\n")
    assert rendered == [
        "a.md:9: warning[rule/a] first",
        "b.md:2: error[rule/a] earlier line",
        "b.md:4: error[rule/b] second",
        "demo: 2 checked, 2 error(s), 1 warning(s): FAIL",
    ]


def test_github_annotations_escape_newlines(tmp_path: Path) -> None:
    finding = Finding(Severity.ERROR, "rule/x", "line one\nline two 100%", tmp_path / "f.md", 3)
    assert (
        finding.render_annotation(tmp_path)
        == "::error file=f.md,line=3::[rule/x] line one%0Aline two 100%25"
    )
    bare = Finding(Severity.WARNING, "rule/y", "no path")
    assert bare.render_annotation() == "::warning::[rule/y] no path"


def test_render_adds_annotations_when_requested(tmp_path: Path) -> None:
    report = Report("demo")
    report.info("rule/i", "note")
    report.error("rule/e", "bad", tmp_path / "x.md")
    lines = report.render(tmp_path, github=True).split("\n")
    assert "::error file=x.md::[rule/e] bad" in lines
    assert not any(line.startswith("::notice") for line in lines)


def test_to_dict(tmp_path: Path) -> None:
    report = Report("demo", checked=1)
    report.error("rule/e", "bad", tmp_path / "x.md", 7)
    payload = report.to_dict(tmp_path)
    assert payload["ok"] is False
    assert payload["errors"] == 1
    findings = payload["findings"]
    assert isinstance(findings, list)
    assert findings[0]["path"] == "x.md"
    assert findings[0]["line"] == 7
    assert findings[0]["severity"] == "error"
