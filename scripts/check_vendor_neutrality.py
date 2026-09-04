#!/usr/bin/env python3
"""Fail when any tracked text, path, branch name or commit message matches the vendor denylist.

The denylist never lives in this repository. It is read, in order of precedence, from
``--denylist PATH``, the ``VENDOR_DENYLIST_FILE`` environment variable, the ``VENDOR_DENYLIST``
environment variable (the list itself, one pattern per line, as CI receives it from a secret),
or ``~/.config/lakehouse-agent-skills/denylist.txt``. Patterns are case-insensitive regular
expressions; lines starting with ``#`` and blank lines are ignored.

Output names the file, line and pattern number only. The matched text is never printed, so a
public CI log cannot leak what the list protects.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

# Defaulting to the checkout rather than the working directory matters: `git ls-files` without a
# pathspec lists only what is below the current directory, so a cwd default would silently scan a
# subset and still print OK. The output stays hand-rolled on purpose, so this script can never
# print the matched text.
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DENYLIST = Path.home() / ".config" / "lakehouse-agent-skills" / "denylist.txt"
GIT = shutil.which("git") or "git"
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2


@dataclass(frozen=True, slots=True)
class Hit:
    """One match: where it is and which pattern (by 1-based index) it tripped."""

    label: str
    line: int
    pattern: int


class DenylistError(ValueError):
    """The denylist is missing, empty or contains an invalid regular expression."""


def load_patterns(text: str) -> list[re.Pattern[str]]:
    """Compile every non-comment line; report bad lines by number, never by content."""
    patterns: list[re.Pattern[str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line, re.IGNORECASE))
        except re.error as error:
            raise DenylistError(
                f"denylist line {number} is not a valid regex ({error.msg})"
            ) from None
    if not patterns:
        raise DenylistError("denylist contains no patterns")
    return patterns


def resolve_denylist(explicit: Path | None, environ: dict[str, str]) -> str:
    """Return the denylist text from the highest-precedence source available."""
    if explicit is not None:
        return _read(explicit)
    file_override = environ.get("VENDOR_DENYLIST_FILE")
    if file_override:
        return _read(Path(file_override))
    inline = environ.get("VENDOR_DENYLIST")
    if inline is not None and inline.strip():
        return inline
    if DEFAULT_DENYLIST.is_file():
        return _read(DEFAULT_DENYLIST)
    raise DenylistError(
        "no denylist found: pass --denylist, set VENDOR_DENYLIST_FILE or VENDOR_DENYLIST, "
        f"or create {DEFAULT_DENYLIST}"
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise DenylistError(f"cannot read denylist {path}: {error.strerror}") from None


def scan_items(items: Iterable[tuple[str, str]], patterns: Sequence[re.Pattern[str]]) -> list[Hit]:
    """Scan ``(label, text)`` pairs line by line."""
    hits: list[Hit] = []
    for label, text in items:
        for number, line in enumerate(text.split("\n"), start=1):
            hits.extend(
                Hit(label, number, index)
                for index, pattern in enumerate(patterns, start=1)
                if pattern.search(line)
            )
    return hits


def git(args: Sequence[str], root: Path) -> str:
    """Run a git plumbing command and return stdout."""
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [GIT, *args],
        cwd=root,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def tree_items(root: Path) -> list[tuple[str, str]]:
    """Tracked and untracked (not ignored) files: their paths and their contents."""
    listing = git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"], root)
    items: list[tuple[str, str]] = []
    for name in sorted(filter(None, listing.split("\0"))):
        path = root / name
        if not path.is_file():
            continue
        items.append((f"path {name}", name))
        items.append((name, path.read_bytes().decode("utf-8", "ignore")))
    return items


def staged_items(root: Path) -> list[tuple[str, str]]:
    """Staged files as they will be committed."""
    listing = git(["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"], root)
    items: list[tuple[str, str]] = []
    for name in sorted(filter(None, listing.split("\0"))):
        items.append((f"path {name}", name))
        content = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [GIT, "show", f":{name}"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
        items.append((name, content.decode("utf-8", "ignore")))
    return items


def history_items(root: Path) -> list[tuple[str, str]]:
    """Every commit message on every ref, plus every ref name."""
    items: list[tuple[str, str]] = []
    if git(["rev-list", "--all", "--max-count=1"], root).strip():
        log = git(["log", "--all", "--format=%H%x1f%B%x1e"], root)
        for record in filter(None, log.split("\x1e")):
            sha, _, message = record.strip("\n").partition("\x1f")
            items.append((f"commit {sha[:12]}", message))
    refs = git(["for-each-ref", "--format=%(refname)"], root)
    items.extend((f"ref {ref}", ref) for ref in refs.split("\n") if ref)
    return items


def commit_message_items(path: Path) -> list[tuple[str, str]]:
    """The message of the commit being created (commit-msg hook)."""
    return [(f"commit-msg {path.name}", path.read_text(encoding="utf-8", errors="ignore"))]


def build_parser() -> argparse.ArgumentParser:
    """CLI options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to scan (default: the checkout this script lives in)",
    )
    parser.add_argument("--denylist", type=Path, help="path to the denylist file")
    parser.add_argument("--tree", action="store_true", help="scan tracked and untracked files")
    parser.add_argument("--staged", action="store_true", help="scan staged changes only")
    parser.add_argument(
        "--history", action="store_true", help="scan all commit messages and ref names"
    )
    parser.add_argument(
        "--commit-msg", type=Path, metavar="FILE", help="scan a commit message file"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        patterns = load_patterns(resolve_denylist(args.denylist, dict(os.environ)))
    except DenylistError as error:
        print(f"vendor-neutrality: {error}", file=sys.stderr)
        return EXIT_CONFIG

    scopes = {"tree": args.tree, "staged": args.staged, "history": args.history}
    if not any(scopes.values()) and args.commit_msg is None:
        scopes["tree"] = True
        scopes["history"] = True

    items: list[tuple[str, str]] = []
    try:
        if scopes["tree"]:
            items.extend(tree_items(root))
        if scopes["staged"]:
            items.extend(staged_items(root))
        if scopes["history"]:
            items.extend(history_items(root))
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"vendor-neutrality: git command failed: {error}", file=sys.stderr)
        return EXIT_CONFIG
    if args.commit_msg is not None:
        items.extend(commit_message_items(args.commit_msg))

    hits = scan_items(items, patterns)
    for hit in hits:
        print(f"{hit.label}:{hit.line}: matches denylist pattern #{hit.pattern}")
    scanned = ", ".join(name for name, enabled in scopes.items() if enabled) or "commit message"
    verdict = "FAIL" if hits else "OK"
    print(
        f"vendor-neutrality: {len(items)} items scanned ({scanned}), {len(hits)} hit(s): {verdict}"
    )
    return EXIT_FINDINGS if hits else EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
