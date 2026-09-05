"""Lint rules for one skill directory and for the catalog as a whole.

Every rule here is documented in ``docs/skill-anatomy.md``. Errors fail the build;
warnings are printed for the reviewer.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path

from lib import frontmatter
from lib.markdown import (
    Section,
    checkbox_count,
    has_table,
    headings,
    normalize_heading,
    sections,
    strip_code_fences,
    table_header,
)
from lib.repo import Layout, read_checked
from lib.report import Finding, Report

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_LINES = 500

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIGGER_RE = re.compile(
    r"\buse\s+(?:this\s+)?when\b|\buse\s+(?:before|after|during)\b", re.IGNORECASE
)
FIRST_PERSON_RE = re.compile(r"^(this skill|i |we |you )", re.IGNORECASE)
STEP_HEADING_RE = re.compile(r"^step\s+(\d+)\b")
STEP_REFERENCE_RE = re.compile(r"\bStep\s+(\d+)\b")
# "Step 4 of the `other-skill` skill" points somewhere else, so this file having no Step 4 is not
# a defect. Without this, the rule punishes exactly the cross-references the catalogue depends on.
FOREIGN_STEP_RE = re.compile(r"\bStep\s+\d+\s+of\s+(?:the\s+)?`[a-z0-9-]+`", re.IGNORECASE)
CROSS_REFERENCE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`\s+skill\b"),
    re.compile(r"\bskills/([a-z0-9]+(?:-[a-z0-9]+)*)"),
)
EXCLUSION_WORDS_RE = re.compile(
    r"\b(not|never|instead|outside|don't|do not|unless|except)\b", re.IGNORECASE
)

SECTION_EXEMPT_SKILLS = frozenset({"using-lakehouse-skills"})
FORBIDDEN_FRONTMATTER_KEYS = frozenset(
    {"exempt", "exemptions", "lint", "skip-lint", "skip_lint", "no-lint", "validation"}
)
ALLOWED_FRONTMATTER_KEYS = frozenset(
    {
        "name",
        "description",
        "when_to_use",
        "disable-model-invocation",
        "user-invocable",
        "allowed-tools",
        "disallowed-tools",
        "argument-hint",
        "arguments",
        "model",
        "effort",
        "context",
        "agent",
        "background",
        "paths",
        "shell",
        "hooks",
        "metadata",
        "license",
        "compatibility",
    }
)
ALLOWED_SUBDIRECTORIES = frozenset({"scripts", "references", "assets", "examples"})
PLACEHOLDER_FILES = frozenset({".gitkeep", ".keep", ".placeholder"})
CATALOG_README = "README.md"


@dataclass(frozen=True, slots=True)
class SectionSpec:
    """A required section and the normalized headings that satisfy it."""

    key: str
    label: str
    matches: Callable[[str], bool]


def _starts_with_any(*prefixes: str) -> Callable[[str], bool]:
    return lambda heading: heading.startswith(prefixes)


def _contains_any(*needles: str) -> Callable[[str], bool]:
    return lambda heading: any(needle in heading for needle in needles)


REQUIRED_SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("overview", "Overview", _starts_with_any("overview", "summary")),
    SectionSpec("when-to-use", "When to Use", _starts_with_any("when to use", "when to apply")),
    SectionSpec(
        "process",
        "Core Process",
        _starts_with_any("core process", "process", "workflow", "the process", "procedure"),
    ),
    SectionSpec("rationalizations", "Common Rationalizations", _contains_any("rationalization")),
    SectionSpec("red-flags", "Red Flags", _contains_any("red flag", "warning sign")),
    SectionSpec("verification", "Verification", _starts_with_any("verification", "verify")),
)


def lint_skill(
    skill_dir: Path, *, known_skills: Collection[str], case_names: Collection[str]
) -> list[Finding]:
    """Lint one skill directory and return its findings."""
    report = Report("skill")
    name = skill_dir.name
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        report.error("skill/missing-skill-md", "directory has no SKILL.md", skill_dir)
        return report.findings

    text = _decode(skill_file, report)
    if text is None:
        return report.findings

    parsed = _parse_frontmatter(text, report, skill_file)
    _check_length(text, report, skill_file)
    if parsed is not None:
        _check_frontmatter(parsed, name, report, skill_file)
        body_offset = parsed.end_line
        body = parsed.body
        _check_title(body, body_offset, report, skill_file)
        if name not in SECTION_EXEMPT_SKILLS:
            _check_sections(body, body_offset, report, skill_file)
        _check_steps(body, body_offset, report, skill_file)
        _check_cross_references(body, body_offset, known_skills, report, skill_file)
    _check_directory(skill_dir, report)
    if name not in case_names:
        report.error(
            "skill/missing-eval-case",
            f"no eval case at evals/cases/{name}.json",
            skill_file,
        )
    return report.findings


def lint_catalog(layout: Layout) -> Report:
    """Lint every skill and the catalog-level invariants."""
    report = Report("validate-skills")
    known = layout.skill_names()
    case_names = [path.stem for path in layout.case_files()]
    for skill_dir in layout.skill_dirs():
        report.checked += 1
        report.extend(lint_skill(skill_dir, known_skills=known, case_names=case_names))
    for case_path in layout.case_files():
        if case_path.stem not in known:
            report.error(
                "catalog/orphan-case",
                f"eval case has no skill directory skills/{case_path.stem}/",
                case_path,
            )
    if layout.skills.is_dir():
        for entry in sorted(layout.skills.iterdir()):
            if entry.is_file() and entry.name != CATALOG_README:
                report.warning(
                    "catalog/stray-file",
                    "only skill directories and a README belong directly under skills/",
                    entry,
                )
    return report


def _decode(path: Path, report: Report) -> str | None:
    text = read_checked(path, report, "skill/encoding")
    if text is not None and text and not text.endswith("\n"):
        report.warning("skill/encoding", "file does not end with a newline", path)
    return text


def _parse_frontmatter(text: str, report: Report, path: Path) -> frontmatter.Frontmatter | None:
    try:
        return frontmatter.parse(text)
    except frontmatter.FrontmatterError as error:
        report.error("skill/frontmatter", error.detail, path, error.line)
        return None


def _check_frontmatter(
    parsed: frontmatter.Frontmatter, dir_name: str, report: Report, path: Path
) -> None:
    data = parsed.data
    for key in sorted(data):
        if key in FORBIDDEN_FRONTMATTER_KEYS:
            report.error(
                "skill/exemption-declared",
                f"frontmatter key '{key}' is not allowed; exemptions live in the linter only",
                path,
            )
        elif key not in ALLOWED_FRONTMATTER_KEYS:
            report.warning("skill/frontmatter-key", f"unknown frontmatter key '{key}'", path)
    _check_name(data.get("name"), dir_name, report, path)
    _check_description(data.get("description"), report, path)


def _check_name(name: object, dir_name: str, report: Report, path: Path) -> None:
    if not isinstance(name, str) or not name:
        report.error("skill/name-required", "frontmatter needs a non-empty 'name'", path)
        return
    if name != dir_name:
        report.error(
            "skill/name-mismatch",
            f"frontmatter name '{name}' differs from directory '{dir_name}'",
            path,
        )
    if not NAME_RE.match(name):
        report.error("skill/name-format", f"name '{name}' must be lowercase-hyphen-separated", path)
    if len(name) > MAX_NAME_LENGTH:
        report.error("skill/name-length", f"name exceeds {MAX_NAME_LENGTH} characters", path)


def _check_description(description: object, report: Report, path: Path) -> None:
    if not isinstance(description, str) or not description.strip():
        report.error(
            "skill/description-required", "frontmatter needs a non-empty 'description'", path
        )
        return
    if len(description) > MAX_DESCRIPTION_LENGTH:
        report.error(
            "skill/description-length",
            f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION_LENGTH}",
            path,
        )
    if not TRIGGER_RE.search(description):
        report.error(
            "skill/description-trigger",
            "description must contain a 'Use when …' trigger so agents know when to load it",
            path,
        )
    if FIRST_PERSON_RE.match(description.strip()):
        report.warning(
            "skill/description-voice",
            "description should state what the skill does in third person",
            path,
        )


def _check_length(text: str, report: Report, path: Path) -> None:
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    if lines >= MAX_SKILL_LINES:
        report.error(
            "skill/too-long",
            f"SKILL.md has {lines} lines; keep it under {MAX_SKILL_LINES} and move detail to "
            "references",
            path,
        )


def _check_title(body: str, offset: int, report: Report, path: Path) -> None:
    heads = headings(body)
    if not heads or heads[0].level != 1:
        report.warning("skill/title", "SKILL.md should open with a level-1 title", path, offset + 1)


def _check_sections(body: str, offset: int, report: Report, path: Path) -> None:
    found: dict[str, Section] = {}
    for section in sections(body):
        normalized = normalize_heading(section.heading.text)
        for spec in REQUIRED_SECTIONS:
            if spec.key not in found and spec.matches(normalized):
                found[spec.key] = section
    for spec in REQUIRED_SECTIONS:
        if spec.key not in found:
            report.error(
                "skill/missing-section", f"required section '{spec.label}' not found", path
            )
    _check_section_order(found, offset, report, path)

    rationalizations = found.get("rationalizations")
    if rationalizations is not None:
        line = rationalizations.heading.line + offset
        if not has_table(rationalizations.body):
            report.error(
                "skill/rationalizations-table",
                "Common Rationalizations must be a table of excuse | reality",
                path,
                line,
            )
        else:
            header = " ".join(table_header(rationalizations.body))
            if "excuse" not in header and "rationalization" not in header:
                report.warning(
                    "skill/rationalizations-table",
                    "rationalizations table header should name the excuse column",
                    path,
                    line,
                )
            if "reality" not in header and "truth" not in header and "response" not in header:
                report.warning(
                    "skill/rationalizations-table",
                    "rationalizations table header should name the reality column",
                    path,
                    line,
                )

    verification = found.get("verification")
    if verification is not None and checkbox_count(verification.body) == 0:
        report.error(
            "skill/verification-checklist",
            "Verification must be a checklist of '- [ ]' items with evidence",
            path,
            verification.heading.line + offset,
        )

    when_to_use = found.get("when-to-use")
    if when_to_use is not None and not EXCLUSION_WORDS_RE.search(when_to_use.body):
        report.warning(
            "skill/when-to-use-exclusions",
            "When to Use should also say when not to use the skill",
            path,
            when_to_use.heading.line + offset,
        )


def _check_section_order(
    found: dict[str, Section], offset: int, report: Report, path: Path
) -> None:
    """The required sections appear in the documented order; a reader relies on it."""
    expected = [spec.key for spec in REQUIRED_SECTIONS if spec.key in found]
    previous_line = 0
    previous_label = ""
    labels = {spec.key: spec.label for spec in REQUIRED_SECTIONS}
    for key in expected:
        line = found[key].heading.line
        if line < previous_line:
            report.error(
                "skill/section-order",
                f"'{labels[key]}' appears before '{previous_label}'; the required sections "
                f"follow the order {', '.join(spec.label for spec in REQUIRED_SECTIONS)}",
                path,
                line + offset,
            )
            return
        previous_line = line
        previous_label = labels[key]


def _check_steps(body: str, offset: int, report: Report, path: Path) -> None:
    declared: set[int] = set()
    for head in headings(body):
        match = STEP_HEADING_RE.match(normalize_heading(head.text))
        if match is not None:
            declared.add(int(match.group(1)))
    prose = strip_code_fences(body)
    referenced: dict[int, int] = {}
    # A reference to another skill's step wraps across lines as often as not, so the whole prose is
    # cleaned at once rather than line by line. The replacement keeps whatever newlines it swallowed
    # so the line numbers reported afterwards still point at the right place.
    local = FOREIGN_STEP_RE.sub(lambda found: "\n" * found.group(0).count("\n"), prose)
    for number, line in enumerate(local.split("\n"), start=1):
        for match in STEP_REFERENCE_RE.finditer(line):
            referenced.setdefault(int(match.group(1)), number)
    missing = sorted(step for step in referenced if step not in declared)
    for step in missing:
        line_no = referenced[step] + offset
        message = f"'Step {step}' is referenced but has no 'Step {step}' heading"
        if declared:
            report.error("skill/step-heading", message, path, line_no)
        else:
            report.warning("skill/step-heading", message, path, line_no)


def _check_cross_references(
    body: str, offset: int, known_skills: Collection[str], report: Report, path: Path
) -> None:
    prose = strip_code_fences(body)
    seen: set[str] = set()
    for number, line in enumerate(prose.split("\n"), start=1):
        for pattern in CROSS_REFERENCE_RES:
            for match in pattern.finditer(line):
                referenced = match.group(1)
                if referenced in known_skills or referenced in seen:
                    continue
                seen.add(referenced)
                report.warning(
                    "skill/cross-reference",
                    f"references skill '{referenced}', which does not exist",
                    path,
                    number + offset,
                )


def _check_directory(skill_dir: Path, report: Report) -> None:
    for entry in sorted(skill_dir.iterdir()):
        if entry.is_dir():
            if entry.name not in ALLOWED_SUBDIRECTORIES:
                report.warning(
                    "skill/unexpected-file",
                    f"unexpected directory '{entry.name}' inside the skill",
                    entry,
                )
            elif not any(child.name not in PLACEHOLDER_FILES for child in entry.iterdir()):
                # A placeholder is the only way git can track an empty directory, so a directory
                # holding nothing else is exactly the case this rule exists to catch.
                report.error(
                    "skill/empty-directory",
                    f"'{entry.name}/' is empty; do not create directories to mirror other skills",
                    entry,
                )
        elif entry.name != "SKILL.md" and entry.suffix.lower() != ".md":
            report.warning(
                "skill/unexpected-file",
                f"unexpected file '{entry.name}' next to SKILL.md",
                entry,
            )
