#!/usr/bin/env python3
"""Fail the build when a shipped skill script is missing, extra, or drifted from its source.

The copies under `skills/<name>/scripts/` are what an installed user actually receives, because a
per-skill install carries the skill's directory and nothing above it. That makes them the real
artefact and this repository's `scripts/skill-scripts/` the source, so the two must agree byte for
byte. `scripts/sync_skill_scripts.py` regenerates them; this checks them.

Three ways they can disagree, all of them failures:

* A skill tells the reader to run a script it does not ship. The instruction is unrunnable for
  everyone who installed that skill on its own.
* A skill ships a script it never mentions. Nothing invokes it, so it is weight the install
  carries and nobody reads.
* A copy differs from its source. Two versions of a check exist and only one of them was fixed.

Standard library only.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lib.repo import Layout, add_root_argument, configure_output
from lib.report import Report
from sync_skill_scripts import SCRIPTS_DIRECTORY, SOURCE_DIRECTORY, SUFFIX, plan, sources


def validate(layout: Layout) -> Report:
    """Compare every skill's shipped scripts with the source of truth."""
    report = Report("validate-skill-scripts")
    by_name = {source.name: source for source in sources(layout)}
    source_label = "/".join(SOURCE_DIRECTORY)

    for skill, wanted in plan(layout):
        directory = skill / SCRIPTS_DIRECTORY
        found = directory.glob(f"*{SUFFIX}") if directory.is_dir() else ()
        shipped = {path.name for path in found}

        for name in sorted(wanted):
            report.checked += 1
            target = directory / name
            if not target.is_file():
                report.error(
                    "skill-scripts/missing",
                    f"SKILL.md tells the reader to run {SCRIPTS_DIRECTORY}/{name}, but a "
                    f"per-skill install would not carry it; run sync_skill_scripts.py",
                    skill / "SKILL.md",
                )
                continue
            if target.read_bytes() != by_name[name].read_bytes():
                report.error(
                    "skill-scripts/drift",
                    f"differs from {source_label}/{name}; two versions of the same check exist "
                    "and only one of them was fixed. Run sync_skill_scripts.py",
                    target,
                )

        for name in sorted(shipped - wanted):
            report.checked += 1
            if name in by_name:
                report.error(
                    "skill-scripts/unreferenced",
                    "this skill ships the script but never tells anyone to run it; either name "
                    f"{SCRIPTS_DIRECTORY}/{name} in SKILL.md or remove the copy",
                    directory / name,
                )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = validate(layout)
    print(report.render(layout.root))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
