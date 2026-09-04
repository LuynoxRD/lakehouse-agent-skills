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

from lib.evals_schema import EvalCase, load_cases
from lib.markdown import normalize_heading, sections
from lib.repo import Layout, add_root_argument, confined_path, iter_files, read_checked
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
    text = read_checked(note, report, "fixture/encoding")
    if text is None:
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

    for name in sorted(known):
        if not (layout.eval_fixtures / name).is_dir():
            report.error(
                "fixture/missing-folder",
                f"skill '{name}' has no fixture folder at evals/fixtures/{name}/",
                layout.skills / name,
            )

    cases, schema_report = load_cases(layout)
    report.extend(schema_report.findings)
    referenced = _check_case_fixtures(cases, layout, report)
    for folder in folders:
        if folder.name not in referenced:
            report.warning("fixture/unreferenced", "no eval case uses this fixture folder", folder)
    return report


def _check_case_fixtures(cases: Sequence[EvalCase], layout: Layout, report: Report) -> set[str]:
    """Check every fixture an eval references and return the folders that are actually used."""
    referenced: set[str] = set()
    for case in cases:
        for behavioral in case.evals:
            for fixture in behavioral.files:
                if not _is_confined(fixture, layout):
                    report.error(
                        "fixture/outside-tree",
                        f"eval '{behavioral.id}' references '{fixture}', which escapes "
                        "evals/fixtures/; the runner copies these files into the agent's "
                        "workspace, so they must stay inside the fixture tree",
                        case.path,
                    )
                elif not (layout.eval_fixtures / fixture).exists():
                    report.error(
                        "fixture/missing",
                        f"eval '{behavioral.id}' references fixture '{fixture}', "
                        "which does not exist",
                        case.path,
                    )
                else:
                    referenced.add(Path(fixture).parts[0])
    return referenced


def _is_confined(fixture: str, layout: Layout) -> bool:
    """Whether a fixture path stays inside ``evals/fixtures/``.

    The behavioral runner copies these files into the agent's workspace, so a path such as
    ``../../pyproject.toml`` would smuggle repository files into an eval. The runner enforces
    this again at the point of use; this check reports it as a finding at review time.
    """
    return confined_path(layout.eval_fixtures, fixture) is not None


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
