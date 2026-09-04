"""Canonical artifact paths that commands and skills must agree on.

The lifecycle commands write notes and data into the user's project. Every skill,
command and reviewer persona that mentions one of those locations must use the
same spelling, otherwise a `/profile` note lands where `/clean` never looks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

NOTES_DIR = "docs/data/"
NOTE_FILES: tuple[str, ...] = ("profile.md", "cleaning-log.md", "model.md", "disclosure.md")
CANONICAL_NOTE_PATHS: tuple[str, ...] = tuple(f"{NOTES_DIR}{name}" for name in NOTE_FILES)

DATA_DIR = "data/"
DATA_LAYERS: tuple[str, ...] = ("raw", "clean", "curated")
CANONICAL_DATA_PATHS: tuple[str, ...] = tuple(f"{DATA_DIR}{layer}/" for layer in DATA_LAYERS)

# A mention counts only when `docs/data/` or `data/` starts a path: `evals/fixtures/x/data/raw/`
# is a fixture, not an artifact convention.
_NOTE_RE = re.compile(r"(?<![\w/.-])docs/data/([A-Za-z0-9_.-]+)")
_DATA_RE = re.compile(r"(?<![\w/.-])data/([A-Za-z0-9_.-]+)/")


@dataclass(frozen=True, slots=True)
class Violation:
    """A non-canonical artifact path mention."""

    kind: str
    value: str
    line: int
    expected: tuple[str, ...]


def find_violations(text: str) -> list[Violation]:
    """Return every `docs/data/<file>` or `data/<layer>/` mention that is not canonical."""
    violations: list[Violation] = []
    for number, line in enumerate(text.split("\n"), start=1):
        for match in _NOTE_RE.finditer(line):
            name = match.group(1).rstrip(".,;:)")
            if name and name not in NOTE_FILES:
                violations.append(
                    Violation("note", f"{NOTES_DIR}{name}", number, CANONICAL_NOTE_PATHS)
                )
        for match in _DATA_RE.finditer(line):
            layer = match.group(1)
            if layer not in DATA_LAYERS:
                violations.append(
                    Violation("layer", f"{DATA_DIR}{layer}/", number, CANONICAL_DATA_PATHS)
                )
    return violations
