"""Tests for the persona frontmatter validator.

Two defaults are expensive in a way nothing announces: an agent with no `model` inherits the
caller's, and an agent with no `tools` gets all of them. Four subagent invocations in one audited
run cost 388,699 tokens on a model nobody chose, and three reviewers shipped able to edit the work
they were reviewing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import validate_agents
from conftest import write
from lib.repo import Layout

PERSONA = (
    "---\n"
    "name: a-reviewer\n"
    "description: Reviews a thing. Use before handing it to somebody.\n"
    "model: inherit\n"
    "color: cyan\n"
    'tools: ["Read", "Grep"]\n'
    "---\n\nBody\n"
)


def rules(layout: Layout) -> list[str]:
    return [finding.rule for finding in validate_agents.validate(layout).findings]


def persona(repo: Layout, text: str = PERSONA) -> Path:
    return write(repo.agents / "a-reviewer.md", text)


def test_a_complete_persona_is_clean(repo: Layout) -> None:
    persona(repo)
    assert validate_agents.validate(repo).findings == []


@pytest.mark.parametrize("field", ["model", "color", "tools"])
def test_a_missing_field_is_refused(repo: Layout, field: str) -> None:
    persona(repo, "\n".join(line for line in PERSONA.split("\n") if not line.startswith(field)))
    assert "agents/missing-field" in rules(repo)


def test_a_model_that_is_not_one_of_the_four_is_refused(repo: Layout) -> None:
    persona(repo, PERSONA.replace("model: inherit", "model: gpt"))
    assert "agents/model" in rules(repo)


def test_the_cheap_model_is_allowed(repo: Layout) -> None:
    """The point of declaring it is being able to pick the small one."""
    persona(repo, PERSONA.replace("model: inherit", "model: haiku"))
    assert validate_agents.validate(repo).findings == []


def test_a_reviewer_that_can_write_is_refused(repo: Layout) -> None:
    """A reviewer able to edit the work it reviews can make its own report come true."""
    persona(repo, PERSONA.replace('["Read", "Grep"]', '["Read", "Write"]'))
    assert "agents/tools-write" in rules(repo)


def test_an_empty_tool_list_is_refused(repo: Layout) -> None:
    persona(repo, PERSONA.replace('["Read", "Grep"]', "[]"))
    assert "agents/tools-shape" in rules(repo)


def test_the_real_personas_declare_both() -> None:
    """The check that matters: this repository, as committed."""
    root = Path(__file__).resolve().parents[1]
    assert validate_agents.validate(Layout(root)).exit_code == 0
