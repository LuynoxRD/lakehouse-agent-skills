"""Tests for the strict frontmatter parser."""

from __future__ import annotations

import pytest

from lib import frontmatter


def test_parses_scalars_and_body() -> None:
    parsed = frontmatter.parse(
        "---\nname: demo\ndescription: Does things. Use when needed.\n---\n\n# Title\n"
    )
    assert parsed.data == {"name": "demo", "description": "Does things. Use when needed."}
    assert parsed.body == "\n# Title\n"
    assert parsed.end_line == 4


def test_quoted_scalars_are_unquoted() -> None:
    text = '---\na: "with: colon"\nb: \'it\'\'s\'\nc: "say \\"hi\\""\n---\n'
    parsed = frontmatter.parse(text)
    assert parsed.data == {"a": "with: colon", "b": "it's", "c": 'say "hi"'}


def test_literal_and_folded_block_scalars() -> None:
    text = (
        "---\nliteral: |\n  line one\n  line two\n"
        "folded: >\n  part one\n  part two\n\n  next paragraph\n---\n"
    )
    parsed = frontmatter.parse(text)
    assert parsed.data["literal"] == "line one\nline two"
    assert parsed.data["folded"] == "part one part two\nnext paragraph"


def test_lists_and_nested_maps() -> None:
    text = (
        "---\nallowed-tools:\n  - Read\n  - Grep\n"
        "metadata:\n  author: someone\n  version: '1'\n---\n"
    )
    parsed = frontmatter.parse(text)
    assert parsed.data["allowed-tools"] == ["Read", "Grep"]
    assert parsed.data["metadata"] == {"author": "someone", "version": "1"}


def test_comments_and_blank_lines_are_ignored() -> None:
    parsed = frontmatter.parse("---\n# a comment\n\nname: demo\n---\n")
    assert parsed.data == {"name": "demo"}


@pytest.mark.parametrize(
    ("text", "line", "fragment"),
    [
        ("name: demo\n", 1, "must start"),
        ("---\nname: demo\n", 2, "closing"),
        ("---\n  name: demo\n---\n", 2, "indentation"),
        ("---\nname demo\n---\n", 2, "key: value"),
        ("---\nname: a\nname: b\n---\n", 3, "duplicate"),
        ("---\nname: 'open\n---\n", 2, "unterminated"),
        ("---\ntags: [a, b]\n---\n", 2, "not supported"),
        ("---\nempty:\n---\n", 2, "no value"),
        ("---\nblock: |\n---\n", 2, "no content"),
        ("---\nitems:\n  - a\n    - b\n---\n", 4, "indentation"),
        ("---\nmeta:\n  key: |\n---\n", 3, "scalars only"),
    ],
)
def test_errors_carry_line_numbers(text: str, line: int, fragment: str) -> None:
    with pytest.raises(frontmatter.FrontmatterError) as raised:
        frontmatter.parse(text)
    assert raised.value.line == line
    assert fragment in raised.value.detail


def test_has_frontmatter() -> None:
    assert frontmatter.has_frontmatter("---\nname: x\n---\n")
    assert not frontmatter.has_frontmatter("# Title\n")


def test_a_plain_value_that_a_strict_reader_would_reject_is_an_error() -> None:
    """Found by installing the pack, not by any check in this repository.

    Four skills whose description held a colon and a space were dropped by the standard installer,
    silently, while every validator here passed: this parser accepted the plain scalar and a strict
    YAML reader did not. Four of thirteen skills were invisible and nothing said so.
    """
    for value in ("Declares what a run missed: rows, sheets and files.", "A note # not a comment"):
        with pytest.raises(frontmatter.FrontmatterError) as error:
            frontmatter.parse("---\nname: a-skill\ndescription: " + value + "\n---\n\nbody\n")
        assert "ambiguous" in error.value.detail
        assert error.value.line == 3

    # Quoting is the escape hatch, and it still yields the value the author meant.
    parsed = frontmatter.parse(
        '---\nname: a-skill\ndescription: "Declares what a run missed: rows."\n---\n\nbody\n'
    )
    assert parsed.data["description"] == "Declares what a run missed: rows."


def test_a_colon_without_a_following_space_is_still_a_plain_value() -> None:
    """A ratio or a time is not ambiguous, and rejecting it would be a worse rule than none."""
    parsed = frontmatter.parse(
        "---\nname: a-skill\ndescription: Holds text to a contrast ratio of 4.5:1 at 09:30.\n"
        "---\n\nbody\n"
    )
    assert parsed.data["description"] == "Holds text to a contrast ratio of 4.5:1 at 09:30."
