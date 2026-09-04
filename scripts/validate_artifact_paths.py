#!/usr/bin/env python3
"""Validate that skills, commands, agents and docs cite the same artifact paths.

The lifecycle commands write notes into `docs/data/` and data into `data/raw/`, `data/clean/`
and `data/curated/`. Any other spelling (`docs/data/profiling.md`, `data/cleaned/`) is an error;
the canonical list lives in lib/artifact_paths.py and docs/skill-anatomy.md.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lib.artifact_paths import find_violations
from lib.repo import Layout, add_root_argument, iter_files, read_checked
from lib.report import Report

SCANNED_SUFFIXES = frozenset({".md", ".toml"})


def scanned_files(layout: Layout) -> list[Path]:
    """Files whose artifact-path mentions must be canonical."""
    files: list[Path] = []
    for directory in (
        layout.skills,
        layout.commands,
        layout.claude_commands,
        layout.gemini_commands,
        layout.agents,
        layout.references,
        layout.docs,
    ):
        files.extend(p for p in iter_files(directory) if p.suffix.lower() in SCANNED_SUFFIXES)
    return sorted(set(files))


def validate(layout: Layout) -> Report:
    """Report every non-canonical artifact path."""
    report = Report("validate-artifact-paths")
    for path in scanned_files(layout):
        report.checked += 1
        text = read_checked(path, report, "artifacts/encoding")
        if text is None:
            continue
        for violation in find_violations(text):
            report.error(
                f"artifacts/{violation.kind}",
                f"'{violation.value}' is not a canonical artifact path; use one of "
                f"{', '.join(violation.expected)}",
                path,
                violation.line,
            )
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
