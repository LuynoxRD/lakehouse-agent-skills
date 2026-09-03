"""Tests for the markdown structure helpers."""

from __future__ import annotations

from lib.markdown import (
    checkbox_count,
    has_table,
    headings,
    line_of,
    markdown_links,
    normalize_heading,
    sections,
    strip_code_fences,
    table_header,
)

DOCUMENT = """# Title

## Overview
Intro text.

```bash
## not a heading
- [ ] not a checkbox
```

## Verification
- [ ] first
- [x] second
* [ ] third

### Nested
Deep [link](../other.md) and [external](https://example.com/x).

## Common Rationalizations
| Excuse | Reality |
| --- | --- |
| "Later" | Never |
"""


def test_headings_skip_code_fences_and_report_lines() -> None:
    found = headings(DOCUMENT)
    assert [(h.level, h.text) for h in found] == [
        (1, "Title"),
        (2, "Overview"),
        (2, "Verification"),
        (3, "Nested"),
        (2, "Common Rationalizations"),
    ]
    assert found[1].line == 3
    assert found[2].line == 11


def test_sections_extend_to_next_heading_of_same_or_higher_level() -> None:
    by_name = {s.heading.text: s for s in sections(DOCUMENT)}
    assert "first" in by_name["Verification"].body
    assert "Deep [link]" in by_name["Verification"].body
    assert "Deep [link]" in by_name["Nested"].body
    assert "Excuse" not in by_name["Verification"].body


def test_normalize_heading() -> None:
    assert normalize_heading("## 3. When to Use ✅") == "when to use"
    assert normalize_heading("Core Process:") == "core process"
    assert normalize_heading("Step 2: Clean") == "step 2 clean"


def test_links_ignore_code_fences() -> None:
    links = markdown_links(DOCUMENT)
    assert [link.target for link in links] == ["../other.md", "https://example.com/x"]
    assert links[0].line == 17


def test_tables_and_checkboxes() -> None:
    assert has_table(DOCUMENT)
    assert table_header(DOCUMENT) == ["excuse", "reality"]
    assert checkbox_count(DOCUMENT) == 3
    assert not has_table("no | table\nhere")
    assert table_header("plain") == []


def test_strip_code_fences_keeps_line_count() -> None:
    stripped = strip_code_fences(DOCUMENT)
    assert stripped.count("\n") == DOCUMENT.count("\n")
    assert "not a heading" not in stripped


def test_line_of() -> None:
    assert line_of("a\nb\nc", 0) == 1
    assert line_of("a\nb\nc", 3) == 2
