#!/usr/bin/env python3
"""Write the per-tool command copies from `commands/*.toml`, the single source of truth.

`scripts/validate_commands.py` fails when a copy drifts from its source. This script is how a copy
stops drifting: it regenerates both from the source rather than asking anyone to edit three files
and keep them in step. Run it after changing any command, then commit all three.

Standard library only. It writes nothing outside `.claude/commands/` and `.gemini/commands/`, and
it removes copies whose source command no longer exists.
"""

from __future__ import annotations

import argparse
import tomllib
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report


def claude_copy(description: str, prompt: str) -> str:
    """The markdown form: description in frontmatter, prompt as the body."""
    return f"---\ndescription: {description}\n---\n\n{prompt.strip()}\n"


def sync(layout: Layout) -> Report:
    """Regenerate every copy; report what changed."""
    report = Report("sync-commands")
    sources = sorted(layout.commands.glob("*.toml")) if layout.commands.is_dir() else []
    names = {source.stem for source in sources}
    layout.claude_commands.mkdir(parents=True, exist_ok=True)
    layout.gemini_commands.mkdir(parents=True, exist_ok=True)

    for source in sources:
        report.checked += 1
        raw = read_text(source)
        try:
            document = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as error:
            report.error("sync/unreadable", f"cannot parse TOML: {error}", source)
            continue
        description = document.get("description")
        prompt = document.get("prompt")
        if not isinstance(description, str) or not isinstance(prompt, str):
            report.error("sync/shape", "needs a string 'description' and 'prompt'", source)
            continue

        target = layout.claude_commands / f"{source.stem}.md"
        _write(target, claude_copy(description, prompt), report)
        target = layout.gemini_commands / f"{source.stem}.toml"
        _write(target, raw, report)

    for directory, suffix in ((layout.claude_commands, ".md"), (layout.gemini_commands, ".toml")):
        for path in sorted(directory.glob(f"*{suffix}")):
            if path.stem not in names:
                path.unlink()
                report.warning("sync/removed", "copy had no source command; removed", path)
    return report


def _write(path: Path, content: str, report: Report) -> None:
    """Write with LF endings, and say so only when the bytes actually change."""
    encoded = content.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return
    path.write_bytes(encoded)
    report.warning("sync/written", "copy regenerated from its source", path)


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
