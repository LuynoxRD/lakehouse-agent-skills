"""Tests for the skill linter and its CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

import validate_skills
from conftest import DESCRIPTION_A, SKILL_A, SKILL_B, skill_markdown, write
from lib.repo import Layout
from lib.skill_lint import lint_catalog, lint_skill


def rules(layout: Layout, severity: str | None = None) -> list[str]:
    report = lint_catalog(layout)
    return [f.rule for f in report.findings if severity is None or f.severity.value == severity]


def test_valid_catalog_is_clean(repo: Layout) -> None:
    report = lint_catalog(repo)
    assert report.findings == []
    assert report.checked == 2
    assert report.exit_code == 0


def test_cli_exit_codes(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_skills.main(["--root", str(repo.root)]) == 0
    assert "validate-skills: 2 checked" in capsys.readouterr().out
    (repo.skills / SKILL_A / "SKILL.md").unlink()
    assert validate_skills.main(["--root", str(repo.root)]) == 1
    assert "skill/missing-skill-md" in capsys.readouterr().out


def test_name_mismatch_and_format(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    write(path, skill_markdown("Other_Name", DESCRIPTION_A))
    found = rules(repo, "error")
    assert "skill/name-mismatch" in found
    assert "skill/name-format" in found


def test_description_rules(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    write(path, skill_markdown(SKILL_A, "This skill charts data whenever asked."))
    found = lint_catalog(repo).findings
    assert any(f.rule == "skill/description-trigger" for f in found)
    assert any(f.rule == "skill/description-voice" for f in found)
    write(path, skill_markdown(SKILL_A, "x" * 1030 + " Use when needed."))
    assert "skill/description-length" in rules(repo, "error")
    write(
        path, skill_markdown(SKILL_A, DESCRIPTION_A).replace(f"description: {DESCRIPTION_A}\n", "")
    )
    assert "skill/description-required" in rules(repo, "error")


def test_missing_sections_and_checklist(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A)
    write(path, text.replace("## Red Flags", "## Something Else"))
    assert "skill/missing-section" in rules(repo, "error")
    write(
        path,
        text.replace("- [ ] `docs/data/profile.md`", "docs/data/profile.md").replace(
            "- [ ] Curated", "Curated"
        ),
    )
    assert "skill/verification-checklist" in rules(repo, "error")


def test_rationalizations_need_a_table_with_named_columns(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A)
    write(path, text.replace("| Excuse | Reality |\n| --- | --- |\n", ""))
    assert "skill/rationalizations-table" in rules(repo, "error")
    write(path, text.replace("| Excuse | Reality |", "| Left | Right |"))
    assert rules(repo, "error") == []
    assert rules(repo, "warning").count("skill/rationalizations-table") == 2


def test_when_to_use_without_exclusions_warns(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A).replace(
        " Do not use it for streaming pipelines.", ""
    )
    write(path, text)
    assert "skill/when-to-use-exclusions" in rules(repo, "warning")


def test_step_references_need_headings(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A).replace(
        "Step 1 always precedes Step 2.", "Then run Step 3."
    )
    write(path, text)
    errors = [f for f in lint_catalog(repo).findings if f.rule == "skill/step-heading"]
    assert len(errors) == 1
    assert errors[0].severity.value == "error"
    assert "Step 3" in errors[0].message
    no_headings = text.replace("### Step 1: Profile", "### Profile").replace(
        "### Step 2: Clean", "### Clean"
    )
    write(path, no_headings)
    warnings = [f for f in lint_catalog(repo).findings if f.rule == "skill/step-heading"]
    assert {f.severity.value for f in warnings} == {"warning"}


def test_a_step_belonging_to_another_skill_is_not_a_missing_heading(repo: Layout) -> None:
    """A catalogue of skills that point at each other cannot have this rule punish the pointing.

    Found by our own linter warning about `using-lakehouse-skills`, which cites Step 4 of the
    chart skill. The reference wrapped across two lines, so a line-by-line scan saw a bare
    "Step 4" and reported a heading this file was never supposed to have.
    """
    path = repo.skills / SKILL_A / "SKILL.md"
    wrapped = (
        "which is the thing Step 4 of the\n`" + SKILL_B + "` skill refuses for the same reason."
    )
    write(
        path,
        skill_markdown(SKILL_A, DESCRIPTION_A).replace("Step 1 always precedes Step 2.", wrapped),
    )

    findings = [f for f in lint_catalog(repo).findings if f.rule == "skill/step-heading"]

    assert findings == []


def test_cross_reference_to_missing_skill_warns(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A).replace(
        "Profiling comes first",
        f"Hand off to the `{SKILL_B}` skill or the `not-a-real-skill` skill. Profiling comes first",
    )
    write(path, text)
    warnings = [f for f in lint_catalog(repo).findings if f.rule == "skill/cross-reference"]
    assert len(warnings) == 1
    assert "not-a-real-skill" in warnings[0].message


def test_forbidden_and_unknown_frontmatter_keys(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A).replace(
        "---\nname:", "---\nexempt: true\ncolour: blue\nname:", 1
    )
    write(path, text)
    findings = lint_catalog(repo).findings
    assert any(
        f.rule == "skill/exemption-declared" and f.severity.value == "error" for f in findings
    )
    assert any(
        f.rule == "skill/frontmatter-key" and f.severity.value == "warning" for f in findings
    )


def test_router_is_exempt_from_sections_only(repo: Layout) -> None:
    router = repo.skills / "using-lakehouse-skills" / "SKILL.md"
    text = (
        "---\nname: using-lakehouse-skills\n"
        "description: Routes data tasks to the right skill. Use when starting any data task.\n"
        "---\n\n# Using lakehouse skills\n\nMap intent to skill.\n"
    )
    write(router, text)
    source_case = (repo.eval_cases / f"{SKILL_A}.json").read_text()
    write(
        repo.eval_cases / "using-lakehouse-skills.json",
        source_case.replace(SKILL_A, "using-lakehouse-skills"),
    )
    assert "skill/missing-section" not in rules(repo)


def test_encoding_rules(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A)
    path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
    messages = [f.message for f in lint_catalog(repo).findings if f.rule == "skill/encoding"]
    assert any("byte-order mark" in m for m in messages)
    assert any("CRLF" in m for m in messages)
    path.write_bytes(text.rstrip("\n").encode("utf-8"))
    warnings = [f for f in lint_catalog(repo).findings if f.rule == "skill/encoding"]
    assert len(warnings) == 1
    assert warnings[0].severity.value == "warning"


def test_sections_must_appear_in_the_documented_order(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    text = skill_markdown(SKILL_A, DESCRIPTION_A)
    head, _, tail = text.partition("## Overview")
    overview, _, rest = tail.partition("## When to Use")
    # Move Overview after When to Use: every required section is still present.
    reordered = f"{head}## When to Use{rest.split('## Core Process')[0]}## Overview{overview}"
    reordered += "## Core Process" + text.split("## Core Process", 1)[1]
    write(path, reordered)
    found = rules(repo, "error")
    assert "skill/missing-section" not in found
    assert "skill/section-order" in found


def test_too_long(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    write(path, skill_markdown(SKILL_A, DESCRIPTION_A) + "\n" * 600)
    assert "skill/too-long" in rules(repo, "error")


def test_exactly_the_limit_is_not_under_the_limit(repo: Layout) -> None:
    path = repo.skills / SKILL_A / "SKILL.md"
    body = skill_markdown(SKILL_A, DESCRIPTION_A)
    current = body.count("\n")
    write(path, body + "\n" * (500 - current))
    assert "skill/too-long" in rules(repo, "error")
    write(path, body + "\n" * (498 - current))
    assert "skill/too-long" not in rules(repo, "error")


def test_a_placeholder_does_not_make_a_directory_non_empty(repo: Layout) -> None:
    # git cannot track an empty directory, so a .gitkeep is exactly how the mistake this rule
    # exists to catch would reach the repository.
    write(repo.skills / SKILL_A / "scripts" / ".gitkeep", "")
    assert "skill/empty-directory" in rules(repo, "error")


def test_directory_hygiene_and_eval_case(repo: Layout) -> None:
    skill_dir = repo.skills / SKILL_A
    (skill_dir / "scripts").mkdir()
    write(skill_dir / "notes.txt", "stray")
    (skill_dir / "weird").mkdir()
    (repo.eval_cases / f"{SKILL_A}.json").unlink()
    findings = lint_catalog(repo).findings
    found = {f.rule: f.severity.value for f in findings}
    assert found["skill/empty-directory"] == "error"
    assert found["skill/unexpected-file"] == "warning"
    assert found["skill/missing-eval-case"] == "error"


def test_catalog_level_findings(repo: Layout) -> None:
    write(repo.eval_cases / "ghost-skill.json", "{}")
    write(repo.skills / "stray.md", "stray")
    write(repo.skills / "README.md", "# Catalog\n")
    found = {f.rule: f.severity.value for f in lint_catalog(repo).findings}
    assert found["catalog/orphan-case"] == "error"
    assert found["catalog/stray-file"] == "warning"
    assert not any("README" in f.location() for f in lint_catalog(repo).findings)


def test_missing_skill_md_and_bad_frontmatter(tmp_path: Path) -> None:
    empty = tmp_path / "skills" / "empty-skill"
    empty.mkdir(parents=True)
    findings = lint_skill(empty, known_skills=["empty-skill"], case_names=["empty-skill"])
    assert [f.rule for f in findings] == ["skill/missing-skill-md"]
    write(empty / "SKILL.md", "# No frontmatter\n")
    findings = lint_skill(empty, known_skills=["empty-skill"], case_names=["empty-skill"])
    assert findings[0].rule == "skill/frontmatter"
    assert findings[0].line == 1
