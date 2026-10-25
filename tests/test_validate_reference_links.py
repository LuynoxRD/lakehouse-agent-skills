"""Tests for the reference-link validator."""

from __future__ import annotations

import pytest

import validate_reference_links
from conftest import DESCRIPTION_B, SKILL_A, SKILL_B, skill_markdown, write
from lib.repo import Layout


def findings(layout: Layout) -> dict[str, str]:
    return {f.rule: f.severity.value for f in validate_reference_links.validate(layout).findings}


def test_valid_repo_is_clean(repo: Layout) -> None:
    report = validate_reference_links.validate(repo)
    assert report.findings == []
    assert report.checked > 0


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_reference_links.main(["--root", str(repo.root)]) == 0
    assert "validate-reference-links" in capsys.readouterr().out


def test_root_document_that_moved_is_an_error_not_a_silent_skip(repo: Layout) -> None:
    (repo.root / ".claude" / "CLAUDE.md").rename(repo.root / "CLAUDE.md")
    report = validate_reference_links.validate(repo)
    assert [(f.rule, f.severity.value) for f in report.findings] == [
        ("links/missing-root-document", "error")
    ]
    assert report.findings[0].path == repo.root / ".claude" / "CLAUDE.md"


def test_broken_relative_link(repo: Layout) -> None:
    write(repo.docs / "guide.md", "See [missing](./nowhere.md) and [ok](skill-anatomy.md#top).\n")
    report = validate_reference_links.validate(repo)
    assert [f.rule for f in report.findings] == ["links/broken"]
    assert report.findings[0].line == 1


def test_root_relative_and_external_links(repo: Layout) -> None:
    write(
        repo.docs / "guide.md",
        "[root](/CONTRIBUTING.md) [ext](https://example.com) "
        "[mail](mailto:a@b.c) [anchor](#here)\n",
    )
    assert validate_reference_links.validate(repo).findings == []


def test_backticked_reference_mentions_must_exist(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    write(
        path,
        path.read_text().replace(
            "Profiling comes first", "Open `references/ghost.md`. Profiling comes first"
        ),
    )
    assert findings(repo)["links/broken"] == "error"


def test_skill_local_reference_is_resolved(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    write(repo.skills / SKILL_A / "references" / "local.md", "# Local\n")
    write(
        path,
        path.read_text().replace(
            "Profiling comes first", "Open `references/local.md`. Profiling comes first"
        ),
    )
    assert findings(repo) == {}


def test_single_use_and_unused_shared_references(repo: Layout) -> None:
    write(repo.skills / SKILL_B / "SKILL.md", skill_markdown(SKILL_B, DESCRIPTION_B))
    assert findings(repo)["references/single-use"] == "warning"
    write(repo.references / "orphan.md", "# Orphan\n")
    assert findings(repo)["references/unused"] == "error"


def test_references_readme_is_not_counted(repo: Layout) -> None:
    write(repo.references / "README.md", "# Shared references\n")
    assert findings(repo) == {}


def test_toml_prompts_are_scanned(repo: Layout) -> None:
    write(
        repo.commands / "profile.toml",
        'description = "x"\nprompt = """\nInvoke the `etl-before-dashboard` skill; '
        'see [note](../docs/missing.md).\n"""\n',
    )
    assert findings(repo)["links/broken"] == "error"
