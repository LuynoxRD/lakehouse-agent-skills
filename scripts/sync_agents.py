#!/usr/bin/env python3
"""Write each reviewer persona into the format every supported tool actually loads.

`agents/*.md` is the source and Claude Code reads it directly. No other tool does. Each of the
others has its own directory, its own frontmatter, and — the part that matters — its own way of
saying that a reviewer may not edit what it reviews. Hand-copying four personas into three
formats is how a persona ends up shipped to one tool and forgotten in another, so the copies are
generated and `scripts/validate_agent_copies.py` fails the build when one drifts.

**The guarantee is expressed differently in every one of them, and that is the whole reason this
is a translation rather than a copy.**

* **opencode** has no `tools` field at all. An unrecognised key is not rejected: it is routed into
  `options` in silence, so writing `tools` here would look right in the file and restrict nothing.
  The restriction is `permission.edit: deny`. It also takes the name from the filename and has no
  `inherit` model, so both fields are dropped rather than translated.
* **Cursor** has `readonly`, which refuses file edits *and* state-changing shell commands. That is
  stronger than the source, whose own text says a shell can still write; the copies understate
  what Cursor enforces, which is the safe direction for a claim to be wrong in.
* **Gemini CLI** takes an allowlist of tool names in its own vocabulary. Only the identifiers
  confirmed in its documentation are used — `read_file`, `grep_search`, `run_shell_command` — and
  a fourth for globbing is deliberately absent rather than guessed, because an unknown name in an
  allowlist is a tool the persona silently does not get.

Codex has no agent component in its plugin specification, so nothing is generated for it. An
empty directory would read as support that does not exist.

Standard library only. It writes nothing outside the three target directories.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from lib.frontmatter import FrontmatterError, parse
from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report

SUFFIX = ".md"

# The loaders below take a colour, and each names it in its own way. Claude Code takes a word;
# opencode takes hex. The five here are the palette the personas use, at one shade so two
# reviewers never arrive looking like the same one.
COLOUR_HEX = {
    "purple": "#8B5CF6",
    "cyan": "#06B6D4",
    "orange": "#F97316",
    "green": "#22C55E",
    "blue": "#3B82F6",
    "red": "#EF4444",
    "yellow": "#EAB308",
    "pink": "#EC4899",
}

# Confirmed in the loader's own documentation. Globbing is left out on purpose: its identifier is
# not stated there, and a name that does not exist removes a tool instead of granting one.
GEMINI_TOOLS = ("read_file", "grep_search", "run_shell_command")


def scalar(value: str) -> str:
    """Emit a YAML scalar that survives a round trip through an ordinary parser."""
    if (
        value
        and not any(character in value for character in ":#'\"\n")
        and value[0] not in "-?&*!|>%@`[{"
    ):
        return value
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True)
class Target:
    """One tool's directory and the frontmatter it understands."""

    directory: tuple[str, ...]
    render: Callable[[str, Mapping[str, object]], str]


def _description(data: Mapping[str, object]) -> str:
    return str(data.get("description", ""))


def render_opencode(_name: str, data: Mapping[str, object]) -> str:
    """opencode reads the name from the filename and refuses edits through `permission`."""
    colour = COLOUR_HEX.get(str(data.get("color", "")), "#6B7280")
    return (
        f"description: {scalar(_description(data))}\n"
        "mode: subagent\n"
        f"color: {scalar(colour)}\n"
        "permission:\n"
        "  edit: deny\n"
    )


def render_cursor(name: str, data: Mapping[str, object]) -> str:
    """Cursor's `readonly` covers file edits and state-changing shell commands alike."""
    return (
        f"name: {scalar(name)}\n"
        f"description: {scalar(_description(data))}\n"
        "model: inherit\n"
        "readonly: true\n"
    )


def render_gemini(name: str, data: Mapping[str, object]) -> str:
    """Gemini CLI restricts by allowlist, in its own tool vocabulary."""
    tools = "".join(f"  - {tool}\n" for tool in GEMINI_TOOLS)
    return (
        f"name: {scalar(name)}\n"
        f"description: {scalar(_description(data))}\n"
        "model: inherit\n"
        f"tools:\n{tools}"
    )


TARGETS: dict[str, Target] = {
    "opencode": Target(directory=(".opencode", "agent"), render=render_opencode),
    "cursor": Target(directory=(".cursor", "agents"), render=render_cursor),
    "gemini": Target(directory=(".gemini", "agents"), render=render_gemini),
}


def sources(layout: Layout) -> list[Path]:
    """Every persona this repository maintains, sorted."""
    directory = layout.agents
    return sorted(directory.glob(f"*{SUFFIX}")) if directory.is_dir() else []


def plan(layout: Layout, report: Report) -> dict[Path, str]:
    """Every per-tool file that should exist, with the bytes it should hold."""
    wanted: dict[Path, str] = {}
    for source in sources(layout):
        text = read_text(source)
        try:
            parsed = parse(text)
        except FrontmatterError as error:
            report.error("agents/frontmatter", str(error), source)
            continue
        name = str(parsed.data.get("name", source.stem))
        for target in TARGETS.values():
            path = layout.root.joinpath(*target.directory) / source.name
            wanted[path] = "---\n" + target.render(name, parsed.data) + "---\n" + parsed.body
    return wanted


def existing(layout: Layout) -> set[Path]:
    """Every file currently sitting in a target directory."""
    found: set[Path] = set()
    for target in TARGETS.values():
        directory = layout.root.joinpath(*target.directory)
        if directory.is_dir():
            found.update(directory.glob(f"*{SUFFIX}"))
    return found


def sync(layout: Layout) -> Report:
    """Regenerate every per-tool copy and remove the ones no persona owns."""
    report = Report("sync-agents")
    wanted = plan(layout, report)
    if report.errors:
        return report

    for path, content in sorted(wanted.items()):
        report.checked += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        path.write_text(content, encoding="utf-8", newline="\n")
        report.warning("sync/written", "copy regenerated from its source", path)

    for stray in sorted(existing(layout) - set(wanted)):
        stray.unlink()
        report.warning("sync/removed", "no persona owns this copy", stray)
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
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
