#!/usr/bin/env python3
"""Fail when the plugin loads something other than what this repository ships.

`claude plugin install` exits zero whether it loaded fourteen skills or none, and that is not a
hypothetical: an `agents` field that passed the manifest validator loaded zero agents, the install
went green, and the three reviewer personas shipped in the package with nothing reading them. It
was found by a person running the install and reading the output, which is a habit, and habits are
how the same defect comes back.

So the counting happens here. Expected components come from the tree; actual components come from
`claude plugin details`, whose output is fed to this script on standard input. Names are compared
rather than totals, because a component silently replaced by another keeps the total right.

Standard library only.

    claude plugin details lakehouse-agent-skills | python scripts/check_plugin_inventory.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
SECTION_RE = re.compile(r"^\s*(Skills|Agents|Hooks|MCP servers|LSP servers)\s*\((\d+)\)\s*(.*)$")
# The inventory prints a parenthesised aside after the hook names; nothing else needs stripping.
ASIDE_RE = re.compile(r"\(.*?\)")


def expected_components(layout: Layout) -> dict[str, set[str]]:
    """What this repository ships, read from the tree rather than from a manifest.

    Commands are counted among the skills because the plugin loads them through the same
    mechanism and the inventory reports them together. That coupling is the inventory's, not this
    repository's, and it is asserted here so a change to it is a failure somebody reads rather
    than a number nobody checks.
    """
    skills = {path.name for path in layout.skill_dirs()}
    commands = {path.stem for path in sorted(layout.commands.glob("*.toml"))}
    agents = {path.stem for path in sorted(layout.agents.glob("*.md"))}
    hooks: set[str] = set()
    hooks_file = layout.hooks / "hooks.json"
    if hooks_file.is_file():
        document = json.loads(read_text(hooks_file))
        declared = document.get("hooks")
        if isinstance(declared, dict):
            hooks = set(declared)
    return {"Skills": skills | commands, "Agents": agents, "Hooks": hooks}


def parse_inventory(text: str) -> dict[str, set[str]]:
    """Read the component inventory a plugin install reports."""
    found: dict[str, set[str]] = {}
    for raw_line in ANSI_RE.sub("", text).split("\n"):
        match = SECTION_RE.match(raw_line)
        if match is None:
            continue
        section, declared, listed = match.group(1), int(match.group(2)), match.group(3)
        names = {name.strip() for name in ASIDE_RE.sub("", listed).split(",") if name.strip()}
        # A section that names nothing still reports its count, and a count without names is the
        # shape that hid the defect, so an unnamed non-zero count is kept as a placeholder rather
        # than read as an empty section.
        if not names and declared:
            names = {f"<{declared} unnamed>"}
        found[section] = names
    return found


def compare(expected: dict[str, set[str]], actual: dict[str, set[str]], report: Report) -> None:
    """Report every section whose loaded names differ from what the tree ships."""
    for section, wanted in expected.items():
        report.checked += 1
        if section not in actual:
            report.error(
                "inventory/section-missing",
                f"the install reported no '{section}' section at all; {len(wanted)} were expected",
                None,
            )
            continue
        got = actual[section]
        if got == wanted:
            continue
        missing = sorted(wanted - got)
        extra = sorted(got - wanted)
        detail = []
        if missing:
            detail.append(f"loaded none of: {', '.join(missing)}")
        if extra:
            detail.append(f"loaded unexpectedly: {', '.join(extra)}")
        report.error(
            "inventory/mismatch",
            f"{section}: {len(wanted)} shipped, {len(got)} loaded; " + "; ".join(detail),
            None,
        )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; the inventory arrives on standard input."""
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    parser.add_argument(
        "--inventory",
        type=Path,
        metavar="FILE",
        help="read the inventory from a file instead of standard input",
    )
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    text = read_text(args.inventory) if args.inventory is not None else sys.stdin.read()

    report = Report("check-plugin-inventory")
    actual = parse_inventory(text)
    if not actual:
        report.error(
            "inventory/unreadable",
            "no component inventory found in the input; the install printed nothing this "
            "script could count, which is exactly the state it exists to refuse",
            None,
        )
    else:
        compare(expected_components(layout), actual, report)

    print(report.render(layout.root))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
