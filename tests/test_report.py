"""Tests for findings, reports and exit codes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from lib.repo import REPO_ROOT, confined_path, read_checked
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


def test_configure_output_survives_a_legacy_code_page() -> None:
    """A verdict quotes an agent's own words, so the output can hold any character.

    On Windows the console defaults to a legacy code page, and printing an arrow raised
    UnicodeEncodeError after a 660-second behavioral run had already finished its work.
    """
    arrow = "→"
    env = {"PYTHONIOENCODING": "cp1252", "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    scripts = str(REPO_ROOT / "scripts")
    unguarded = subprocess.run(
        [sys.executable, "-c", f"print('a {arrow} b')"], capture_output=True, env=env, check=False
    )
    program = (
        f"import sys; sys.path.insert(0, {scripts!r}); "
        f"from lib.repo import configure_output; configure_output(); print('a {arrow} b')"
    )
    guarded = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, env=env, check=False
    )
    assert guarded.returncode == 0, guarded.stderr.decode("utf-8", "replace")
    if unguarded.returncode == 0:
        pytest.skip("this platform's default encoding already carries the character")


def test_confined_path_behaves_the_same_on_every_platform(tmp_path: Path) -> None:
    root = tmp_path / "fixtures"
    (root / "skill").mkdir(parents=True)
    (root / "skill" / "data.csv").write_text("a\n", encoding="utf-8")
    assert confined_path(root, "skill/data.csv") == (root / "skill" / "data.csv").resolve()
    for escape in ["../secret", "/etc/passwd", "C:/Windows/win.ini", "c:/x", "skill/../../x"]:
        assert confined_path(root, escape) is None, escape


def test_read_checked_reports_encoding_problems_instead_of_raising(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_bytes(b"plain text\n")
    report = Report("demo")
    assert read_checked(good, report, "x/encoding") == "plain text\n"
    assert report.findings == []

    bom = tmp_path / "bom.md"
    bom.write_bytes(b"\xef\xbb\xbfwith a mark\n")
    report = Report("demo")
    assert read_checked(bom, report, "x/encoding") == "with a mark\n"
    assert [f.rule for f in report.findings] == ["x/encoding"]
    assert "byte-order mark" in report.findings[0].message

    crlf = tmp_path / "crlf.md"
    crlf.write_bytes(b"one\r\ntwo\r\n")
    report = Report("demo")
    assert read_checked(crlf, report, "x/encoding") == "one\ntwo\n"
    assert "CRLF" in report.findings[0].message

    latin1 = tmp_path / "latin1.md"
    latin1.write_bytes(b"caf\xe9\n")
    report = Report("demo")
    assert read_checked(latin1, report, "x/encoding") is None
    assert "not valid UTF-8" in report.findings[0].message


def test_paths_outside_the_root_stay_whole(tmp_path: Path) -> None:
    outside = tmp_path.parent / "elsewhere" / "notes.md"
    finding = Finding(Severity.ERROR, "rule/x", "outside", outside, 12)
    assert finding.relative_path(tmp_path) == outside.as_posix()
    assert finding.location(tmp_path) == f"{outside.as_posix()}:12"
    report = Report("demo")
    report.findings.append(finding)
    payload = report.to_dict(tmp_path)
    findings = payload["findings"]
    assert isinstance(findings, list)
    # A Windows path such as C:/dev/x.md must survive intact, drive letter included.
    assert findings[0]["path"] == outside.as_posix()
    assert findings[0]["line"] == 12


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
