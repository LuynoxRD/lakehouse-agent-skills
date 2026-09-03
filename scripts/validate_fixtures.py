#!/usr/bin/env python3
"""Validate eval fixtures: provenance notes, no executables, no oversized files, no orphans.

Every `evals/fixtures/<skill>/` folder must belong to a skill, carry a FIXTURE.md that states
the data is synthetic and explains how it was generated and which traps it contains, and hold
only data files (plus the `generate.py` that produced them). Every fixture referenced from an
eval case must exist, and every fixture folder must be referenced by a case.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lib.evals_schema import load_cases
from lib.markdown import normalize_heading, sections
from lib.repo import Layout, add_root_argument, iter_files, read_text
from lib.report import Report

FIXTURE_NOTE = "FIXTURE.md"
GENERATOR = "generate.py"
MAX_FIXTURE_BYTES = 5 * 1024 * 1024
FORBIDDEN_SUFFIXES = frozenset(
    {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".bat",
        ".cmd",
        ".vbs",
        ".js",
        ".mjs",
        ".cjs",
        ".jar",
        ".msi",
        ".xlsm",
        ".xlam",
        ".docm",
        ".pptm",
        ".pyc",
        ".pyd",
    }
)
PROVENANCE_HEADINGS = ("provenance", "how it was generated", "generation", "how this was generated")
TRAPS_HEADINGS = ("traps", "what it contains", "contents", "traps and quirks", "known traps")


def _has_section(text: str, prefixes: tuple[str, ...]) -> bool:
    return any(normalize_heading(s.heading.text).startswith(prefixes) for s in sections(text))


def check_note(folder: Path, report: Report) -> None:
    note = folder / FIXTURE_NOTE
    if not note.is_file():
        report.error("fixture/missing-note", f"fixture folder has no {FIXTURE_NOTE}", folder)
        return
    try:
        text = read_text(note)
    except UnicodeDecodeError as error:
        report.error("fixture/encoding", f"{FIXTURE_NOTE} is not valid UTF-8: {error.reason}", note)
        return
    if "synthetic" not in text.lower():
        report.error(
            "fixture/provenance-statement",
            f"{FIXTURE_NOTE} must state that the data is synthetic",
            note,
        )
    if not _has_section(text, PROVENANCE_HEADINGS):
        report.error(
            "fixture/provenance-section",
            f"{FIXTURE_NOTE} needs a 'Provenance' section explaining how the data was generated",
            note,
        )
    if not _has_section(text, TRAPS_HEADINGS):
        report.error(
            "fixture/traps-section",
            f"{FIXTURE_NOTE} needs a 'Traps' section listing what the fixture tests",
            note,
        )


def check_files(folder: Path, report: Report) -> None:
    for path in iter_files(folder):
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            report.error(
                "fixture/executable", f"'{suffix}' files are not allowed in fixtures", path
            )
        elif suffix == ".py" and path.name != GENERATOR:
            report.error(
                "fixture/executable",
                f"only {GENERATOR} may be Python; data files must be data",
                path,
            )
        size = path.stat().st_size
        if size > MAX_FIXTURE_BYTES:
            report.error(
                "fixture/too-large",
                f"{size} bytes exceeds the {MAX_FIXTURE_BYTES} byte limit; generate smaller data",
                path,
            )


def validate(layout: Layout) -> Report:
    """Validate fixture folders and their links to eval cases."""
    report = Report("validate-fixtures")
    known = set(layout.skill_names())
    folders = (
        sorted(p for p in layout.eval_fixtures.iterdir() if p.is_dir())
        if layout.eval_fixtures.is_dir()
        else []
    )
    for folder in folders:
        report.checked += 1
        if folder.name not in known:
            report.error(
                "fixture/orphan", f"no skill named '{folder.name}' owns this fixture folder", folder
            )
        check_note(folder, report)
        check_files(folder, report)
    if layout.eval_fixtures.is_dir():
        for stray in sorted(p for p in layout.eval_fixtures.iterdir() if p.is_file()):
            report.warning(
                "fixture/stray-file", "fixtures live in per-skill folders, not at the top", stray
            )

    cases, schema_report = load_cases(layout)
    report.extend(schema_report.findings)
    referenced: set[str] = set()
    for case in cases:
        for behavioral in case.evals:
            for fixture in behavioral.files:
                target = layout.eval_fixtures / fixture
                if not target.exists():
                    report.error(
                        "fixture/missing",
                        f"eval '{behavioral.id}' references fixture '{fixture}', "
                        "which does not exist",
                        case.path,
                    )
                    continue
                referenced.add(Path(fixture).parts[0])
    for folder in folders:
        if folder.name not in referenced:
            report.warning("fixture/unreferenced", "no eval case uses this fixture folder", folder)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = validate(layout)
    print(report.render(layout.root))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
