"""Repository layout and file helpers shared by the validators."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

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

    @property
    def manifests(self) -> tuple[Path, ...]:
        """Every file that carries the plugin version."""
        return (
            self.root / "plugin.json",
            self.root / ".claude-plugin" / "plugin.json",
            self.root / ".claude-plugin" / "marketplace.json",
            self.root / ".codex-plugin" / "plugin.json",
            self.root / "pyproject.toml",
        )

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


def relative(path: Path, root: Path) -> str:
    """POSIX-style path relative to *root*, or the absolute path when outside it."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
