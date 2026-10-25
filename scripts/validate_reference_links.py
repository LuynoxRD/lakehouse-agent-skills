#!/usr/bin/env python3
"""Validate relative links and the use of shared references.

Every relative markdown link in skills, commands, agents, docs, references and the root
documents must resolve to a file, and every listed root document must exist. Every file in
references/ must be used by more than one skill: a reference used by a single skill belongs
inside that skill, and one used by none is dead weight.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lib.markdown import markdown_links
from lib.repo import Layout, add_root_argument, configure_output, iter_files, read_checked
from lib.report import Report

ROOT_DOCUMENTS = ("README.md", "CONTRIBUTING.md", "SECURITY.md", "AGENTS.md", ".claude/CLAUDE.md")
SCANNED_SUFFIXES = frozenset({".md", ".toml"})
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:")
REFERENCE_MENTION_RE = re.compile(r"(?<![\w/.-])references/([A-Za-z0-9_.-]+\.md)")
REFERENCES_README = "README.md"


def scanned_files(layout: Layout) -> list[Path]:
    """Every markdown and TOML file the validator inspects."""
    files: list[Path] = []
    for directory in (
        layout.skills,
        layout.commands,
        layout.claude_commands,
        layout.gemini_commands,
        layout.agents,
        layout.docs,
        layout.references,
        layout.evals,
    ):
        files.extend(p for p in iter_files(directory) if p.suffix.lower() in SCANNED_SUFFIXES)
    files.extend(p for name in ROOT_DOCUMENTS if (p := layout.root / name).is_file())
    return sorted(set(files))


def _resolve(target: str, source: Path, root: Path) -> Path:
    clean = target.split("#", 1)[0].split("?", 1)[0]
    if clean.startswith("/"):
        return (root / clean.lstrip("/")).resolve()
    return (source.parent / clean).resolve()


def _skill_of(path: Path, layout: Layout) -> str | None:
    try:
        parts = path.relative_to(layout.skills).parts
    except ValueError:
        return None
    return parts[0] if len(parts) > 1 else None


def validate(layout: Layout) -> Report:
    """Check links and reference usage."""
    report = Report("validate-reference-links")
    shared: dict[str, Path] = {}
    if layout.references.is_dir():
        shared = {p.name: p for p in layout.references.glob("*.md") if p.name != REFERENCES_README}
    scan = _Scan(
        layout=layout, shared=shared, usage={name: set() for name in shared}, report=report
    )

    # A root document that moved without this list following it would drop out of the scan in
    # silence, and its links would go unchecked while this validator still passed.
    for name in ROOT_DOCUMENTS:
        if not (layout.root / name).is_file():
            report.error(
                "links/missing-root-document",
                "listed as a root document but not found; update ROOT_DOCUMENTS if it moved",
                layout.root / name,
            )

    for path in scanned_files(layout):
        report.checked += 1
        text = read_checked(path, report, "links/encoding")
        if text is None:
            continue
        skill = _skill_of(path, layout)
        _check_links(text, path, skill, scan)
        _check_mentions(text, path, skill, scan)

    for name, path in sorted(shared.items()):
        consumers = scan.usage.get(name, set())
        if not consumers:
            report.error("references/unused", "shared reference is not used by any skill", path)
        elif len(consumers) == 1:
            report.warning(
                "references/single-use",
                f"only '{next(iter(consumers))}' uses this reference; shared references serve "
                "more than one skill, otherwise move it into the skill",
                path,
            )
    return report


@dataclass(slots=True)
class _Scan:
    """State shared by the per-file checks."""

    layout: Layout
    shared: dict[str, Path]
    usage: dict[str, set[str]]
    report: Report


def _check_links(text: str, path: Path, skill: str | None, scan: _Scan) -> None:
    for link in markdown_links(text):
        target = link.target
        if target.startswith(EXTERNAL_PREFIXES) or target.startswith("#") or not target:
            continue
        resolved = _resolve(target, path, scan.layout.root)
        if not resolved.exists():
            scan.report.error(
                "links/broken", f"link target '{target}' does not exist", path, link.line
            )
        elif skill and resolved.parent == scan.layout.references.resolve():
            scan.usage.setdefault(resolved.name, set()).add(skill)


def _check_mentions(text: str, path: Path, skill: str | None, scan: _Scan) -> None:
    for number, line in enumerate(text.split("\n"), start=1):
        for match in REFERENCE_MENTION_RE.finditer(line):
            name = match.group(1)
            if (path.parent / "references" / name).is_file():
                continue
            if name in scan.shared:
                if skill:
                    scan.usage[name].add(skill)
                continue
            if skill and (scan.layout.skills / skill / "references" / name).is_file():
                continue
            scan.report.error(
                "links/broken",
                f"'references/{name}' does not exist in references/ or next to the skill",
                path,
                number,
            )


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
