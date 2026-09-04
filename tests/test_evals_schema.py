"""Tests for the eval case schema."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import SKILL_A, SKILL_B, case_json, write
from lib.evals_schema import load_case, load_cases
from lib.repo import Layout


def base_case() -> dict[str, object]:
    document: dict[str, object] = json.loads(case_json(SKILL_A, SKILL_B, f"{SKILL_A}/sales.csv"))
    return document


def load(
    tmp_path: Path, document: dict[str, object], name: str = SKILL_A
) -> tuple[object, list[str]]:
    path = write(tmp_path / f"{name}.json", json.dumps(document))
    case, findings = load_case(path)
    return case, [f"{f.rule}:{f.message}" for f in findings]


def test_valid_case_loads(tmp_path: Path) -> None:
    case, findings = load(tmp_path, base_case())
    assert findings == []
    assert case is not None
    assert case.skill_name == SKILL_A  # type: ignore[attr-defined]
    assert case.positives[1].top_k == 3  # type: ignore[attr-defined]
    assert case.evals[0].id == "1"  # type: ignore[attr-defined]
    assert case.evals[0].files == (f"{SKILL_A}/sales.csv",)  # type: ignore[attr-defined]


def test_filename_must_match_skill_name(tmp_path: Path) -> None:
    case, findings = load(tmp_path, base_case(), name="other")
    assert case is None
    assert any(f.startswith("case/skill-name") for f in findings)


def test_minimum_counts(tmp_path: Path) -> None:
    document = base_case()
    trigger = document["trigger"]
    assert isinstance(trigger, dict)
    trigger["positive"] = trigger["positive"][:2]
    trigger["negative"] = trigger["negative"][:1]
    document["evals"] = []
    case, findings = load(tmp_path, document)
    assert case is None
    assert sum(f.startswith("case/minimums") for f in findings) == 3


def test_owner_rules(tmp_path: Path) -> None:
    document = base_case()
    trigger = document["trigger"]
    assert isinstance(trigger, dict)
    trigger["negative"][0]["owner"] = SKILL_A
    del trigger["negative"][1]["owner"]
    _, findings = load(tmp_path, document)
    assert any("different skill" in f for f in findings)
    assert any("owner must name" in f for f in findings)


def test_eval_rules(tmp_path: Path) -> None:
    document = base_case()
    evals = document["evals"]
    assert isinstance(evals, list)
    first = dict(evals[0])
    first.update(id=2, kind="weird")
    second = dict(evals[0])
    second.update(id=3, files=[])
    third = dict(evals[0])
    third.update(id=4, expectations=[])
    fourth = dict(evals[0])
    fourth["id"] = 1
    document["evals"] = [evals[0], first, second, third, fourth]
    _, findings = load(tmp_path, document)
    joined = "\n".join(findings)
    assert "kind must be one of" in joined
    assert "needs at least one fixture" in joined
    assert "expectations must be a non-empty list" in joined
    assert "is duplicated" in joined


def test_dialogue_evals_need_no_files(tmp_path: Path) -> None:
    document = base_case()
    evals = document["evals"]
    assert isinstance(evals, list)
    dialogue = dict(evals[0])
    dialogue.update(id="talk", kind="dialogue", files=[])
    document["evals"] = [evals[0], dialogue]
    case, findings = load(tmp_path, document)
    assert findings == []
    assert case is not None


def test_a_dialogue_eval_alone_does_not_satisfy_the_minimum(tmp_path: Path) -> None:
    # A dialogue eval carries no fixture and is graded by a human, so a skill whose only eval
    # is a dialogue has nothing that actually runs against data.
    document = base_case()
    evals = document["evals"]
    assert isinstance(evals, list)
    only = dict(evals[0])
    only.update(kind="dialogue", files=[])
    document["evals"] = [only]
    case, findings = load(tmp_path, document)
    assert case is None
    assert any("execution eval backed by a fixture" in f for f in findings)


def test_unknown_keys_warn_and_bad_json_errors(tmp_path: Path) -> None:
    document = base_case()
    document["extra"] = 1
    _, findings = load(tmp_path, document)
    assert findings == ["case/unknown-key:unknown top-level key 'extra'"]
    path = write(tmp_path / f"{SKILL_A}.json", "[1, 2]")
    case, raw = load_case(path)
    assert case is None
    assert raw[0].rule == "case/shape"


def test_load_cases_counts(repo: Layout) -> None:
    cases, report = load_cases(repo)
    assert len(cases) == 2
    assert report.checked == 2
    assert report.ok
