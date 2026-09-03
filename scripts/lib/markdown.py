"""Markdown structure helpers: headings, sections, links, tables and checklists."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+\S")
_NON_WORD_RE = re.compile(r"[^a-z0-9/&' -]+")


@dataclass(frozen=True, slots=True)
class Heading:
    """A markdown heading with its 1-based line number."""

    level: int
    text: str
    line: int


@dataclass(frozen=True, slots=True)
class Section:
    """A heading and the text under it, up to the next heading of equal or higher level."""

    heading: Heading
    body: str


@dataclass(frozen=True, slots=True)
class Link:
    """A markdown link target with its 1-based line number."""

    target: str
    line: int


def strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks while preserving line numbers."""
    result: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        match = _FENCE_RE.match(line)
        if fence is None and match is not None:
            fence = match.group(1)
            result.append("")
            continue
        if fence is not None:
            if match is not None and match.group(1) == fence:
                fence = None
            result.append("")
            continue
        result.append(line)
    return "\n".join(result)


def headings(text: str) -> list[Heading]:
    """Every ATX heading outside fenced code, with 1-based line numbers."""
    found: list[Heading] = []
    for number, line in enumerate(strip_code_fences(text).split("\n"), start=1):
        match = _HEADING_RE.match(line)
        if match is not None:
            found.append(
                Heading(level=len(match.group(1)), text=match.group(2).strip(), line=number)
            )
    return found


def sections(text: str) -> list[Section]:
    """Split into sections; each body runs to the next heading of equal or higher level."""
    lines = text.split("\n")
    heads = headings(text)
    result: list[Section] = []
    for position, head in enumerate(heads):
        end = len(lines)
        for later in heads[position + 1 :]:
            if later.level <= head.level:
                end = later.line - 1
                break
        result.append(Section(heading=head, body="\n".join(lines[head.line : end])))
    return result


def normalize_heading(text: str) -> str:
    """Lowercase heading text with emojis, numbering and punctuation removed."""
    lowered = text.lower().strip().lstrip("#").strip()
    lowered = re.sub(r"^\d+[.)]\s*", "", lowered)
    lowered = _NON_WORD_RE.sub(" ", lowered)
    return re.sub(r"\s+", " ", lowered).strip(" -")


def markdown_links(text: str) -> list[Link]:
    """Inline link targets outside fenced code, with 1-based line numbers."""
    found: list[Link] = []
    for number, line in enumerate(strip_code_fences(text).split("\n"), start=1):
        found.extend(Link(target=m.group(1), line=number) for m in _LINK_RE.finditer(line))
    return found


def has_table(text: str) -> bool:
    """Whether the text contains a pipe table (header row followed by a separator row)."""
    lines = strip_code_fences(text).split("\n")
    for index in range(len(lines) - 1):
        if "|" in lines[index] and _TABLE_SEPARATOR_RE.match(lines[index + 1]):
            return True
    return False


def table_header(text: str) -> list[str]:
    """Cells of the first pipe table header, lowercased; empty when there is no table."""
    lines = strip_code_fences(text).split("\n")
    for index in range(len(lines) - 1):
        if "|" in lines[index] and _TABLE_SEPARATOR_RE.match(lines[index + 1]):
            cells = [cell.strip().lower() for cell in lines[index].strip().strip("|").split("|")]
            return [cell for cell in cells if cell]
    return []


def checkbox_count(text: str) -> int:
    """Number of task-list items (``- [ ] …`` or ``- [x] …``) outside fenced code."""
    return sum(1 for line in strip_code_fences(text).split("\n") if _CHECKBOX_RE.match(line))


def line_of(text: str, offset: int) -> int:
    """1-based line number of a character offset."""
    return text.count("\n", 0, offset) + 1
