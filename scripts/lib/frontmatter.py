"""Minimal, strict frontmatter parser for SKILL.md and command files.

Supports the subset of YAML that skill frontmatter needs: plain and quoted scalars,
block scalars (``|`` and ``>``), lists of scalars, and one level of nested maps.
Anything else is rejected with a line number so the author fixes the file instead
of the parser guessing. No third-party YAML library is involved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

Value = str | list[str] | dict[str, str]

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$")
_ITEM_RE = re.compile(r"^(\s+)-\s+(.*)$")
_NESTED_RE = re.compile(r"^(\s+)([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$")
_BLOCK_INDICATORS = frozenset({"|", ">", "|-", ">-", "|+", ">+"})
_MIN_QUOTED_LENGTH = 2
_RESERVED_PREFIXES = ("[", "{", "&", "*", "!", "%", "@", "`")


class FrontmatterError(ValueError):
    """Raised when the frontmatter is missing or uses unsupported syntax."""

    def __init__(self, message: str, line: int) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.detail = message


@dataclass(frozen=True, slots=True)
class Frontmatter:
    """Parsed frontmatter plus the markdown body that follows it."""

    data: dict[str, Value]
    body: str
    end_line: int


def has_frontmatter(text: str) -> bool:
    """Whether the text starts with a frontmatter delimiter."""
    return text.split("\n", 1)[0].strip() == "---"


def parse(text: str) -> Frontmatter:
    """Parse frontmatter at the start of *text*.

    Raises :class:`FrontmatterError` when the block is missing, unterminated,
    indented unexpectedly, repeats a key, or uses YAML features outside the
    supported subset.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file must start with a '---' frontmatter delimiter", 1)
    close = _find_closing(lines)
    data: dict[str, Value] = {}
    index = 1
    while index < close:
        raw = lines[index]
        line_no = index + 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            index += 1
            continue
        if raw[0].isspace():
            raise FrontmatterError("unexpected indentation", line_no)
        match = _KEY_RE.match(raw)
        if match is None:
            raise FrontmatterError("expected 'key: value'", line_no)
        key = match.group(1)
        rest = (match.group(2) or "").strip()
        if key in data:
            raise FrontmatterError(f"duplicate key '{key}'", line_no)
        if rest in _BLOCK_INDICATORS:
            value, index = _read_block(
                lines, index + 1, close, key_line=line_no, folded=rest.startswith(">")
            )
            data[key] = value
            continue
        if rest == "":
            children, index = _read_children(lines, index + 1, close, line_no)
            data[key] = children
            continue
        data[key] = _scalar(rest, line_no)
        index += 1
    body = "\n".join(lines[close + 1 :])
    return Frontmatter(data=data, body=body, end_line=close + 1)


def _find_closing(lines: list[str]) -> int:
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    last_line = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
    raise FrontmatterError("closing '---' delimiter not found", max(last_line, 1))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _read_block(
    lines: list[str], start: int, close: int, *, key_line: int, folded: bool
) -> tuple[str, int]:
    collected: list[str] = []
    index = start
    while index < close:
        line = lines[index]
        if line.strip() and not line[0].isspace():
            break
        collected.append(line)
        index += 1
    indents = [_indent(line) for line in collected if line.strip()]
    if not indents:
        raise FrontmatterError("block scalar has no content", key_line)
    base = min(indents)
    dedented = [line[base:] if line.strip() else "" for line in collected]
    while dedented and not dedented[-1]:
        dedented.pop()
    if folded:
        paragraphs: list[str] = []
        current: list[str] = []
        for line in dedented:
            if line:
                current.append(line.strip())
            elif current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        return "\n".join(paragraphs), index
    return "\n".join(dedented), index


def _read_children(
    lines: list[str], start: int, close: int, key_line: int
) -> tuple[list[str] | dict[str, str], int]:
    index = start
    while index < close and not lines[index].strip():
        index += 1
    if index >= close or not lines[index][0].isspace():
        raise FrontmatterError("key has no value; use a scalar, a list or a nested map", key_line)
    first = lines[index]
    if _ITEM_RE.match(first):
        return _read_list(lines, index, close)
    if _NESTED_RE.match(first):
        return _read_map(lines, index, close)
    raise FrontmatterError("expected a '- item' list or 'key: value' map", index + 1)


def _read_list(lines: list[str], start: int, close: int) -> tuple[list[str], int]:
    items: list[str] = []
    index = start
    indent = _indent(lines[start])
    while index < close:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line[0].isspace():
            break
        match = _ITEM_RE.match(line)
        if match is None or len(match.group(1)) != indent:
            raise FrontmatterError("list items must share one indentation", index + 1)
        items.append(_scalar(match.group(2).strip(), index + 1))
        index += 1
    return items, index


def _read_map(lines: list[str], start: int, close: int) -> tuple[dict[str, str], int]:
    mapping: dict[str, str] = {}
    index = start
    indent = _indent(lines[start])
    while index < close:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line[0].isspace():
            break
        match = _NESTED_RE.match(line)
        if match is None or len(match.group(1)) != indent:
            raise FrontmatterError("nested keys must share one indentation", index + 1)
        key = match.group(2)
        rest = (match.group(3) or "").strip()
        if key in mapping:
            raise FrontmatterError(f"duplicate key '{key}'", index + 1)
        if rest == "" or rest in _BLOCK_INDICATORS:
            raise FrontmatterError("nested maps hold scalars only", index + 1)
        mapping[key] = _scalar(rest, index + 1)
        index += 1
    return mapping, index


def _scalar(raw: str, line_no: int) -> str:
    if raw.startswith(('"', "'")):
        quote = raw[0]
        if len(raw) < _MIN_QUOTED_LENGTH or not raw.endswith(quote):
            raise FrontmatterError("unterminated quoted scalar", line_no)
        inner = raw[1:-1]
        if quote == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    if raw.startswith(_RESERVED_PREFIXES):
        raise FrontmatterError(
            f"values starting with {raw[0]!r} are not supported; quote the value", line_no
        )
    # A plain scalar holding a colon and a space, or a space and a hash, is ambiguous: a strict
    # reader takes the first as a second mapping separator and the second as a comment. Tools that
    # use one drop the whole file, and they do it silently, so this has to be an error here rather
    # than something a lenient parser waves through.
    for ambiguity, reads_as in ((": ", "another key"), (" #", "a comment")):
        if ambiguity in raw:
            raise FrontmatterError(
                f"a plain value containing {ambiguity!r} is ambiguous, since a strict YAML "
                f"reader takes it as the start of {reads_as}; rewrite the value or quote it",
                line_no,
            )
    return raw
