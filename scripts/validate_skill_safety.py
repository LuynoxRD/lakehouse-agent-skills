#!/usr/bin/env python3
"""Fail the build when skill content contains constructs that must never run inside an agent.

Scans skills/, hooks/, commands/, agents/ and the per-tool copies for the patterns in
lib/safety_patterns.py, flags network commands and links to undocumented hosts, and enforces
the header rules for shell scripts (bash shebang, `set -euo pipefail`, a cleanup trap).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, is_text_file, iter_files
from lib.report import Report
from lib.safety_patterns import (
    ALLOWED_HOSTS,
    NETWORK_COMMAND_RULE,
    UNKNOWN_HOST_RULE,
    network_commands,
    scan_text,
    unknown_hosts,
)

BASH_SHEBANG = "#!/usr/bin/env bash"
STRICT_MODE = "set -euo pipefail"
HEADER_WINDOW = 10


def scanned_directories(layout: Layout) -> tuple[Path, ...]:
    """Directories whose content runs inside an agent."""
    return (
        layout.skills,
        layout.hooks,
        layout.commands,
        layout.agents,
        layout.claude_commands,
        layout.gemini_commands,
        layout.opencode_skills,
    )


def check_shell_script(path: Path, text: str, report: Report, *, require_trap: bool) -> None:
    """Shell scripts shipped with skills or hooks follow one header contract."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != BASH_SHEBANG:
        report.error("safety/script-shebang", f"first line must be '{BASH_SHEBANG}'", path, 1)
    header = [line.strip() for line in lines[:HEADER_WINDOW]]
    if STRICT_MODE not in header:
        report.error(
            "safety/script-strict-mode",
            f"'{STRICT_MODE}' must appear within the first {HEADER_WINDOW} lines",
            path,
        )
    if require_trap and not any(line.lstrip().startswith("trap ") for line in lines):
        report.error("safety/script-cleanup-trap", "script must install a cleanup trap", path)


def _hosts_on_line(line: str) -> set[str]:
    return {host for host, _ in unknown_hosts(line)}


def scan_file(path: Path, report: Report, layout: Layout) -> None:
    """Apply every safety rule to one file."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        report.error("safety/encoding", f"file is not valid UTF-8: {error.reason}", path)
        return
    for match in scan_text(text):
        report.add(
            match.pattern.severity, match.pattern.rule, match.pattern.message, path, match.line
        )

    lines = text.split("\n")
    network_lines = set(network_commands(text))
    for number in sorted(network_lines):
        line = lines[number - 1]
        unknown = _hosts_on_line(line)
        if unknown:
            report.error(
                NETWORK_COMMAND_RULE,
                f"network call to undocumented host(s) {', '.join(sorted(unknown))}",
                path,
                number,
            )
        else:
            report.warning(
                NETWORK_COMMAND_RULE,
                "network command in skill content; make sure the skill documents why",
                path,
                number,
            )
    for host, number in unknown_hosts(text):
        if number in network_lines:
            continue
        report.warning(
            UNKNOWN_HOST_RULE,
            f"link to '{host}', which is not on the documentation allowlist "
            f"({len(ALLOWED_HOSTS)} hosts in lib/safety_patterns.py)",
            path,
            number,
        )

    if path.suffix.lower() == ".sh":
        inside_skill = layout.skills in path.parents
        check_shell_script(path, text, report, require_trap=inside_skill)


def validate(layout: Layout) -> Report:
    """Scan every text file that runs inside an agent."""
    report = Report("validate-skill-safety")
    for directory in scanned_directories(layout):
        for path in iter_files(directory):
            if not is_text_file(path):
                report.warning(
                    "safety/binary-file",
                    "non-text file in agent-facing content; skills ship text only",
                    path,
                )
                continue
            report.checked += 1
            scan_file(path, report, layout)
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
