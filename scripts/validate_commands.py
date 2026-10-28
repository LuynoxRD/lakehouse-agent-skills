#!/usr/bin/env python3
"""Validate slash commands: source TOML shape, per-tool copies in parity, skill references.

`commands/<name>.toml` is the source of truth. `.claude/commands/<name>.md` must carry the same
description in its frontmatter, no other frontmatter key, and the same prompt as its body;
`.gemini/commands/<name>.toml` must be identical to the source. Every command must invoke at
least one existing skill.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from collections.abc import Sequence
from pathlib import Path

from lib import frontmatter
from lib.repo import Layout, add_root_argument, configure_output, read_checked, read_text
from lib.report import Report
from lib.skill_lint import NAME_RE

COMMAND_KEYS = frozenset({"description", "prompt"})
# The only frontmatter a Claude copy is generated with. Any other key changes how the command
# runs without the source knowing: `allowed-tools` grants tools without a prompt, and
# `user-invocable: false` hides the command.
CLAUDE_COPY_KEYS = frozenset({"description"})
SKILL_REFERENCE_RE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`")
MAX_DESCRIPTION_LENGTH = 250


def load_command(path: Path, report: Report) -> dict[str, str] | None:
    """Parse one source command; return its fields or None when it is unusable."""
    try:
        document = tomllib.loads(read_text(path))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        report.error("command/unreadable", f"cannot parse TOML: {error}", path)
        return None
    fields: dict[str, str] = {}
    for key in ("description", "prompt"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            report.error("command/shape", f"'{key}' must be a non-empty string", path)
            return None
        fields[key] = value
    for key in sorted(set(document) - COMMAND_KEYS):
        report.warning("command/shape", f"unexpected key '{key}'", path)
    if "\n" in fields["description"].strip():
        report.error("command/shape", "'description' must be a single line", path)
    if len(fields["description"]) > MAX_DESCRIPTION_LENGTH:
        report.warning(
            "command/shape",
            f"description is {len(fields['description'])} characters; keep it under "
            f"{MAX_DESCRIPTION_LENGTH} so menus can show it",
            path,
        )
    return fields


def check_skill_references(prompt: str, known: Sequence[str], report: Report, path: Path) -> None:
    """A command must hand off to at least one existing skill."""
    referenced = {match.group(1) for match in SKILL_REFERENCE_RE.finditer(prompt)}
    existing = sorted(name for name in referenced if name in known)
    if not existing:
        report.error(
            "command/no-skill-reference",
            "prompt must invoke at least one existing skill by its backticked name",
            path,
        )
    for candidate in sorted(referenced - set(existing)):
        report.warning(
            "command/unknown-skill",
            f"'{candidate}' looks like a skill name but no skill has it",
            path,
        )


def check_claude_copy(name: str, fields: dict[str, str], layout: Layout, report: Report) -> None:
    copy = layout.claude_commands / f"{name}.md"
    if not copy.is_file():
        report.error("command/missing-copy", f"missing per-tool copy {copy.name}", copy)
        return
    text = read_checked(copy, report, "command/encoding")
    if text is None:
        return
    try:
        parsed = frontmatter.parse(text)
    except frontmatter.FrontmatterError as error:
        report.error("command/copy-frontmatter", error.detail, copy, error.line)
        return
    extra = sorted(set(parsed.data) - CLAUDE_COPY_KEYS)
    if extra:
        report.error(
            "command/copy-extra-frontmatter",
            f"frontmatter carries {', '.join(extra)}, which commands/*.toml does not generate",
            copy,
        )
    if parsed.data.get("description") != fields["description"]:
        report.error(
            "command/description-drift",
            "frontmatter description differs from commands/*.toml",
            copy,
        )
    if parsed.body.strip() != fields["prompt"].strip():
        report.error("command/prompt-drift", "body differs from the source prompt", copy)


def check_gemini_copy(name: str, source: Path, layout: Layout, report: Report) -> None:
    copy = layout.gemini_commands / f"{name}.toml"
    if not copy.is_file():
        report.error("command/missing-copy", f"missing per-tool copy {copy.name}", copy)
        return
    copy_text = read_checked(copy, report, "command/encoding")
    if copy_text is not None and copy_text != read_text(source):
        report.error("command/prompt-drift", "copy is not identical to commands/*.toml", copy)


def check_orphans(directory: Path, suffix: str, names: set[str], report: Report) -> None:
    if not directory.is_dir():
        return
    for path in sorted(directory.glob(f"*{suffix}")):
        if path.stem not in names:
            report.error(
                "command/orphan-copy",
                f"no source command commands/{path.stem}.toml for this copy",
                path,
            )


def validate(layout: Layout) -> Report:
    """Validate the command set."""
    report = Report("validate-commands")
    known = layout.skill_names()
    sources = sorted(layout.commands.glob("*.toml")) if layout.commands.is_dir() else []
    names: set[str] = set()
    for source in sources:
        report.checked += 1
        name = source.stem
        names.add(name)
        if not NAME_RE.match(name):
            report.error(
                "command/name-format", f"'{name}' must be lowercase-hyphen-separated", source
            )
        fields = load_command(source, report)
        if fields is None:
            continue
        check_skill_references(fields["prompt"], known, report, source)
        check_claude_copy(name, fields, layout, report)
        check_gemini_copy(name, source, layout, report)
    check_orphans(layout.claude_commands, ".md", names, report)
    check_orphans(layout.gemini_commands, ".toml", names, report)
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
