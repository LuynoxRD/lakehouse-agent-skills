#!/usr/bin/env python3
"""Fail the build when skill content contains constructs that must never run inside an agent.

Scans skills/, hooks/, commands/, agents/ and the per-tool copies for the patterns in
lib/safety_patterns.py. Every file that decodes as text is scanned, whatever its extension:
an agent runs what a file says, not what its suffix promises. Network commands, links to
undocumented hosts and the header contract for shell scripts are checked here too.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, configure_output, iter_files, read_checked
from lib.report import Report
from lib.safety_patterns import (
    NETWORK_COMMAND_RULE,
    UNKNOWN_HOST_RULE,
    network_commands,
    scan_text,
    unknown_hosts,
)

BASH_SHEBANG = "#!/usr/bin/env bash"
STRICT_MODE = "set -euo pipefail"
HEADER_WINDOW = 10
SCRIPT_SUFFIX = ".sh"
SCRIPTS_DIRECTORY = "scripts"
NUL_BYTE = b"\x00"


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


def in_skill_scripts(path: Path, layout: Layout) -> bool:
    """Whether the file sits in a skill's own ``scripts/`` directory."""
    return layout.skills in path.parents and path.parent.name == SCRIPTS_DIRECTORY


def read_scannable(path: Path, report: Report) -> str | None:
    """Return the file's text, or None when it is binary or not valid UTF-8."""
    raw = path.read_bytes()
    if NUL_BYTE in raw:
        report.warning(
            "safety/binary-file",
            "binary file in agent-facing content; it cannot be scanned, so review it by hand",
            path,
        )
        return None
    return read_checked(path, report, "safety/encoding")


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
    if require_trap and not any(
        line.lstrip().startswith("trap ") and "EXIT" in line for line in lines
    ):
        report.error(
            "safety/script-cleanup-trap",
            "script must install a cleanup trap that runs on EXIT",
            path,
        )


def check_network(path: Path, text: str, report: Report, *, inside_skill_script: bool) -> None:
    """Flag network commands, escalating when the file also links an undocumented host."""
    network_lines = set(network_commands(text))
    hosts = sorted({host for host, _ in unknown_hosts(text)})
    for number in sorted(network_lines):
        if inside_skill_script:
            report.error(
                NETWORK_COMMAND_RULE,
                "scripts shipped with a skill make no network calls",
                path,
                number,
            )
        elif hosts:
            # The command's target may be built from a variable defined elsewhere in the file,
            # so an undocumented host anywhere in the file makes every network call suspect.
            report.error(
                NETWORK_COMMAND_RULE,
                f"network command in a file that names undocumented host(s) {', '.join(hosts)}",
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
    if network_lines and hosts:
        # Already reported as errors above; repeating them as warnings adds noise.
        return
    for host, number in unknown_hosts(text):
        if number in network_lines:
            continue
        report.warning(
            UNKNOWN_HOST_RULE,
            f"link to '{host}', which is not on the documentation allowlist "
            "(see ALLOWED_HOSTS in lib/safety_patterns.py)",
            path,
            number,
        )


def scan_file(path: Path, report: Report, layout: Layout) -> None:
    """Apply every safety rule to one file."""
    text = read_scannable(path, report)
    if text is None:
        return
    for match in scan_text(text):
        report.add(
            match.pattern.severity, match.pattern.rule, match.pattern.message, path, match.line
        )

    inside_skill_script = in_skill_scripts(path, layout)
    check_network(path, text, report, inside_skill_script=inside_skill_script)

    if inside_skill_script and path.suffix.lower() != SCRIPT_SUFFIX:
        report.error(
            "safety/script-language",
            f"scripts shipped with a skill are bash with a '{SCRIPT_SUFFIX}' suffix so the "
            "header contract can be checked",
            path,
        )
    if path.suffix.lower() == SCRIPT_SUFFIX:
        check_shell_script(path, text, report, require_trap=layout.skills in path.parents)


def validate(layout: Layout) -> Report:
    """Scan every file that runs inside an agent."""
    report = Report("validate-skill-safety")
    for directory in scanned_directories(layout):
        for path in iter_files(directory):
            report.checked += 1
            scan_file(path, report, layout)
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
