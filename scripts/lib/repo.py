"""Repository layout and file helpers shared by the validators."""

from __future__ import annotations

import argparse
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from lib.report import Report

REPO_ROOT = Path(__file__).resolve().parents[2]
BOM = b"\xef\xbb\xbf"

TEXT_SUFFIXES = frozenset(
    {".md", ".toml", ".json", ".yml", ".yaml", ".sh", ".py", ".txt", ".csv", ".sql", ".cfg"}
)
TEXT_NAMES = frozenset(
    {"CODEOWNERS", ".gitattributes", ".gitignore", ".editorconfig", ".python-version"}
)
SKIPPED_DIRECTORIES = frozenset({"__pycache__", ".git", ".venv", "node_modules"})


@dataclass(frozen=True, slots=True)
class Layout:
    """Where every kind of asset lives, relative to one repository root."""

    root: Path

    @property
    def skills(self) -> Path:
        return self.root / "skills"

    @property
    def references(self) -> Path:
        return self.root / "references"

    @property
    def commands(self) -> Path:
        return self.root / "commands"

    @property
    def claude_commands(self) -> Path:
        return self.root / ".claude" / "commands"

    @property
    def gemini_commands(self) -> Path:
        return self.root / ".gemini" / "commands"

    @property
    def opencode_skills(self) -> Path:
        return self.root / ".opencode" / "skills"

    @property
    def agents(self) -> Path:
        return self.root / "agents"

    @property
    def hooks(self) -> Path:
        return self.root / "hooks"

    @property
    def evals(self) -> Path:
        return self.root / "evals"

    @property
    def eval_cases(self) -> Path:
        return self.evals / "cases"

    @property
    def eval_fixtures(self) -> Path:
        return self.evals / "fixtures"

    @property
    def eval_config(self) -> Path:
        return self.evals / "config.json"

    @property
    def eval_results(self) -> Path:
        return self.evals / "results"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    def skill_dirs(self) -> list[Path]:
        """Directories under ``skills/``, sorted; files such as a README are ignored."""
        if not self.skills.is_dir():
            return []
        return sorted(p for p in self.skills.iterdir() if p.is_dir())

    def skill_names(self) -> list[str]:
        """Names of every skill directory."""
        return [p.name for p in self.skill_dirs()]

    def case_files(self) -> list[Path]:
        """Eval case files under ``evals/cases/``."""
        if not self.eval_cases.is_dir():
            return []
        return sorted(self.eval_cases.glob("*.json"))


def add_root_argument(parser: argparse.ArgumentParser) -> None:
    """Attach the shared ``--root`` option."""
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to validate (default: the checkout this script lives in)",
    )


def read_text(path: Path) -> str:
    """Read a UTF-8 text file strictly; invalid bytes raise instead of being replaced."""
    return path.read_text(encoding="utf-8")


def configure_output() -> None:
    """Make stdout and stderr able to carry any text these tools print.

    Findings quote file content, and a behavioral verdict quotes an agent's own words, so the
    output can contain any character. On Windows the console defaults to a legacy code page and
    printing an arrow or an accented word raises UnicodeEncodeError, which turns a passing run
    into a traceback after the work is already done.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with suppress(ValueError, OSError):  # a detached stream cannot be reconfigured
                reconfigure(encoding="utf-8", errors="replace")


def confined_path(root: Path, relative: str) -> Path | None:
    """Resolve *relative* under *root*, or None when it escapes.

    Paths that come from a data file are attacker-controlled the moment the repository accepts
    contributions. An absolute path silently replaces the base in ``root / relative``, and a
    parent traversal walks out of it, so both are rejected and the result is checked again
    after resolution to catch symlinks and drive-relative Windows paths such as ``/etc/x``.

    A colon anywhere in the path is rejected on every platform, not only where it is a drive
    separator. ``C:/Windows/win.ini`` escapes the tree on Windows but is an ordinary relative
    directory on Linux, and a rule that means different things on the maintainer's machine and
    on the runner is a rule nobody can rely on.
    """
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    if any(":" in part for part in candidate.parts):
        return None
    try:
        resolved = (root / candidate).resolve()
        return resolved if resolved.is_relative_to(root.resolve()) else None
    except OSError:
        return None


def read_checked(path: Path, report: Report, rule: str) -> str | None:
    """Read a text file, reporting encoding problems under *rule*.

    Returns None when the file cannot be decoded, so a caller reports one finding instead of
    aborting the whole run with a traceback. Byte-order marks and CRLF endings are errors
    everywhere: `.gitattributes` normalizes to LF, and a bash script with CRLF fails in CI.
    """
    raw = path.read_bytes()
    if raw.startswith(BOM):
        report.error(rule, "file starts with a UTF-8 byte-order mark", path, 1)
        raw = raw[len(BOM) :]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        report.error(rule, f"file is not valid UTF-8: {error.reason}", path)
        return None
    if "\r\n" in text:
        report.error(rule, "file uses CRLF line endings; use LF", path)
        text = text.replace("\r\n", "\n")
    return text


def is_text_file(path: Path) -> bool:
    """Whether a file is safe to scan as text."""
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES


def iter_files(directory: Path) -> list[Path]:
    """Every file below *directory*, sorted, skipping caches and version-control internals."""
    if not directory.is_dir():
        return []
    found: list[Path] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIPPED_DIRECTORIES for part in path.relative_to(directory).parts):
            continue
        found.append(path)
    return sorted(found)
