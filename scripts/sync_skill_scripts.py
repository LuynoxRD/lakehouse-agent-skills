#!/usr/bin/env python3
"""Copy the shippable skill scripts into every skill whose SKILL.md calls for one.

A per-skill install copies the skill's own directory and nothing above it: the installer walks
`skills/<name>/` and excludes only `metadata.json`, `.git` and the Python caches. A script that
lives in this repository's `scripts/` is therefore a script no installed user ever receives, and
a check the consumer cannot run is not a check. So the script ships inside each skill that asks
for it, and this file keeps those copies from drifting, exactly as `sync_commands.py` does for
the per-tool command copies.

Which skills get a copy is read from the skills themselves: a `SKILL.md` that names
`scripts/<file>` receives that file, and one that does not name it must not carry it. The
instructions and the shipped bytes cannot disagree, because neither is written by hand.

`scripts/validate_skill_scripts.py` fails the build when a copy drifts. This script is how a copy
stops drifting. Run it after changing anything under `scripts/skill-scripts/`, then commit the
source and every copy together.

Standard library only. It writes nothing outside `skills/<name>/scripts/`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, configure_output
from lib.report import Report

SCRIPTS_DIRECTORY = "scripts"
SOURCE_DIRECTORY = ("scripts", "skill-scripts")
SUFFIX = ".sh"


def source_directory(layout: Layout) -> Path:
    """Where the single copy of each shippable skill script is maintained."""
    return layout.root.joinpath(*SOURCE_DIRECTORY)


def sources(layout: Layout) -> list[Path]:
    """Every script that a skill may ship, sorted."""
    directory = source_directory(layout)
    return sorted(directory.glob(f"*{SUFFIX}")) if directory.is_dir() else []


def requested(skill: Path, names: Sequence[str]) -> set[str]:
    """The script names this skill's instructions tell the reader to run."""
    document = skill / "SKILL.md"
    if not document.is_file():
        return set()
    text = document.read_text(encoding="utf-8")
    return {name for name in names if f"{SCRIPTS_DIRECTORY}/{name}" in text}


def plan(layout: Layout) -> list[tuple[Path, set[str]]]:
    """For each skill, the set of script names its SKILL.md asks for."""
    names = [source.name for source in sources(layout)]
    return [(skill, requested(skill, names)) for skill in layout.skill_dirs()]


def sync(layout: Layout) -> Report:
    """Write every requested copy, remove every copy no skill still asks for."""
    report = Report("sync-skill-scripts")
    by_name = {source.name: source for source in sources(layout)}
    if not by_name:
        report.warning(
            "sync/no-sources",
            f"no {SUFFIX} files under {'/'.join(SOURCE_DIRECTORY)}; nothing to copy",
            None,
        )

    for skill, wanted in plan(layout):
        directory = skill / SCRIPTS_DIRECTORY
        for name in sorted(wanted):
            report.checked += 1
            target = directory / name
            payload = by_name[name].read_bytes()
            if target.is_file() and target.read_bytes() == payload:
                continue
            directory.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            report.warning("sync/written", "copy regenerated from its source", target)

        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(f"*{SUFFIX}")):
            if path.name in by_name and path.name not in wanted:
                path.unlink()
                report.warning(
                    "sync/removed",
                    "the skill no longer names this script, so the copy was removed",
                    path,
                )
        if not any(directory.iterdir()):
            directory.rmdir()
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = sync(layout)
    print(report.render(layout.root))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
