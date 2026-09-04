"""Schema for ``evals/cases/<skill>.json`` files.

The shape follows the skill-creator eval convention: trigger prompts that must
rank the skill (positive) or another owner (negative), plus behavioral evals that
run against fixtures and are judged by expectations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from lib.repo import Layout
from lib.report import Finding, Report

MIN_POSITIVE_TRIGGERS = 3
MIN_NEGATIVE_TRIGGERS = 2
# Every skill owes one eval that actually runs against a fixture. A `dialogue` eval is reviewed
# by a human and carries no fixture, so it never satisfies this minimum on its own.
MIN_EXECUTION_EVALS = 1
DEFAULT_TOP_K = 3
KINDS = frozenset({"execution", "dialogue"})
# At least one alphanumeric, so an id can never be a bare "." or ".." directory reference.
EVAL_ID_RE = re.compile(r"^(?=.*[A-Za-z0-9])[A-Za-z0-9._-]{1,64}$")
TOP_LEVEL_KEYS = frozenset({"skill_name", "trigger", "evals"})


@dataclass(frozen=True, slots=True)
class PositiveTrigger:
    """A prompt that must rank the skill within ``top_k``."""

    prompt: str
    top_k: int


@dataclass(frozen=True, slots=True)
class NegativeTrigger:
    """A prompt where ``owner`` must outrank the skill."""

    prompt: str
    owner: str


@dataclass(frozen=True, slots=True)
class BehavioralEval:
    """A fixture-backed task whose transcript is judged against expectations."""

    id: str
    kind: str
    prompt: str
    expected_output: str
    files: tuple[str, ...]
    expectations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalCase:
    """Everything the runner needs for one skill."""

    skill_name: str
    path: Path
    positives: tuple[PositiveTrigger, ...]
    negatives: tuple[NegativeTrigger, ...]
    evals: tuple[BehavioralEval, ...]


def load_case(path: Path) -> tuple[EvalCase | None, list[Finding]]:
    """Parse and validate one case file. Returns the case (or None) and the findings."""
    report = Report("evals-schema")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        report.error("case/unreadable", f"cannot parse JSON: {error}", path)
        return None, report.findings
    if not isinstance(document, dict):
        report.error("case/shape", "top level must be a JSON object", path)
        return None, report.findings

    for key in sorted(document):
        if key not in TOP_LEVEL_KEYS:
            report.warning("case/unknown-key", f"unknown top-level key '{key}'", path)

    skill_name = document.get("skill_name")
    if not isinstance(skill_name, str) or not skill_name:
        report.error("case/skill-name", "'skill_name' must be a non-empty string", path)
        skill_name = path.stem
    elif skill_name != path.stem:
        report.error(
            "case/skill-name",
            f"'skill_name' is '{skill_name}' but the file is named '{path.stem}.json'",
            path,
        )

    positives, negatives = _load_triggers(document.get("trigger"), skill_name, report, path)
    evals = _load_evals(document.get("evals"), report, path)

    if report.errors:
        return None, report.findings
    case = EvalCase(
        skill_name=skill_name,
        path=path,
        positives=tuple(positives),
        negatives=tuple(negatives),
        evals=tuple(evals),
    )
    return case, report.findings


def load_cases(layout: Layout) -> tuple[list[EvalCase], Report]:
    """Load every case under ``evals/cases/``."""
    report = Report("evals-schema")
    cases: list[EvalCase] = []
    for path in layout.case_files():
        report.checked += 1
        case, findings = load_case(path)
        report.extend(findings)
        if case is not None:
            cases.append(case)
    return cases, report


def _string(
    item: dict[str, object], key: str, where: str, report: Report, path: Path
) -> str | None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        report.error("case/trigger", f"{where}.{key} must be a non-empty string", path)
        return None
    return value.strip()


def _load_triggers(
    trigger: object, skill_name: str, report: Report, path: Path
) -> tuple[list[PositiveTrigger], list[NegativeTrigger]]:
    if not isinstance(trigger, dict):
        report.error(
            "case/trigger", "'trigger' must be an object with 'positive' and 'negative'", path
        )
        return [], []
    positives = _load_positive(trigger.get("positive"), report, path)
    negatives = _load_negative(trigger.get("negative"), skill_name, report, path)
    return positives, negatives


def _load_positive(raw: object, report: Report, path: Path) -> list[PositiveTrigger]:
    if not isinstance(raw, list):
        report.error("case/trigger", "'trigger.positive' must be a list", path)
        return []
    positives: list[PositiveTrigger] = []
    for index, item in enumerate(raw):
        where = f"trigger.positive[{index}]"
        if not isinstance(item, dict):
            report.error("case/trigger", f"{where} must be an object", path)
            continue
        prompt = _string(item, "prompt", where, report, path)
        if prompt is None:
            continue
        top_k = item.get("top_k", DEFAULT_TOP_K)
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            report.error("case/trigger", f"{where}.top_k must be a positive integer", path)
            continue
        positives.append(PositiveTrigger(prompt=prompt, top_k=top_k))
    if len(raw) < MIN_POSITIVE_TRIGGERS:
        report.error(
            "case/minimums",
            f"at least {MIN_POSITIVE_TRIGGERS} positive triggers are required (found {len(raw)})",
            path,
        )
    return positives


def _load_negative(
    raw: object, skill_name: str, report: Report, path: Path
) -> list[NegativeTrigger]:
    if not isinstance(raw, list):
        report.error("case/trigger", "'trigger.negative' must be a list", path)
        return []
    negatives: list[NegativeTrigger] = []
    for index, item in enumerate(raw):
        where = f"trigger.negative[{index}]"
        if not isinstance(item, dict):
            report.error("case/trigger", f"{where} must be an object", path)
            continue
        prompt = _string(item, "prompt", where, report, path)
        if prompt is None:
            continue
        owner = item.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            report.error(
                "case/trigger",
                f"{where}.owner must name the skill that should win this prompt",
                path,
            )
            continue
        if owner == skill_name:
            report.error("case/trigger", f"{where}.owner must be a different skill", path)
            continue
        negatives.append(NegativeTrigger(prompt=prompt, owner=owner.strip()))
    if len(raw) < MIN_NEGATIVE_TRIGGERS:
        report.error(
            "case/minimums",
            f"at least {MIN_NEGATIVE_TRIGGERS} negative triggers are required (found {len(raw)})",
            path,
        )
    return negatives


def _load_evals(raw: object, report: Report, path: Path) -> list[BehavioralEval]:
    if not isinstance(raw, list):
        report.error("case/evals", "'evals' must be a list", path)
        return []
    evals: list[BehavioralEval] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        where = f"evals[{index}]"
        if not isinstance(item, dict):
            report.error("case/evals", f"{where} must be an object", path)
            continue
        behavioral = _load_eval_item(item, where, seen_ids, report, path)
        if behavioral is not None:
            evals.append(behavioral)
    executions = sum(
        1 for item in raw if isinstance(item, dict) and item.get("kind", "execution") == "execution"
    )
    if executions < MIN_EXECUTION_EVALS:
        report.error(
            "case/minimums",
            f"at least {MIN_EXECUTION_EVALS} execution eval backed by a fixture is required "
            f"(found {executions} among {len(raw)} eval(s)); a dialogue eval does not count",
            path,
        )
    return evals


def _eval_id(
    item: dict[str, object], where: str, seen_ids: set[str]
) -> tuple[str | None, str | None]:
    """Return ``(eval_id, problem)``; exactly one of the two is None."""
    identifier = item.get("id")
    if isinstance(identifier, bool) or not isinstance(identifier, int | str):
        return None, f"{where}.id must be an integer or string"
    eval_id = str(identifier)
    if not EVAL_ID_RE.match(eval_id):
        # The id becomes part of a result file name, so it is restricted to a safe token.
        return None, (f"{where}.id must be 1 to 64 characters of letters, digits, '.', '_' or '-'")
    if eval_id in seen_ids:
        return None, f"{where}.id '{eval_id}' is duplicated"
    seen_ids.add(eval_id)
    return eval_id, None


def _string_list(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(e, str) and e.strip() for e in value):
        return None
    return [str(e) for e in value]


def _load_eval_item(
    item: dict[str, object], where: str, seen_ids: set[str], report: Report, path: Path
) -> BehavioralEval | None:
    problems: list[str] = []
    eval_id, problem = _eval_id(item, where, seen_ids)
    if problem is not None:
        problems.append(problem)

    kind = item.get("kind", "execution")
    if kind not in KINDS:
        problems.append(f"{where}.kind must be one of {sorted(KINDS)}")

    prompt = item.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        problems.append(f"{where}.prompt must be a non-empty string")
        prompt = None
    expected = item.get("expected_output")
    if not isinstance(expected, str) or not expected.strip():
        problems.append(f"{where}.expected_output must be a non-empty string")
        expected = None

    files = _string_list(item.get("files", []))
    if files is None:
        problems.append(f"{where}.files must be a list of fixture paths")
    elif kind == "execution" and not files:
        problems.append(f"{where} is an execution eval and needs at least one fixture in 'files'")

    expectations = _string_list(item.get("expectations"))
    if not expectations:
        problems.append(f"{where}.expectations must be a non-empty list of strings")

    for text in problems:
        report.error("case/evals", text, path)
    if (
        problems
        or eval_id is None
        or prompt is None
        or expected is None
        or files is None
        or not expectations
    ):
        return None
    return BehavioralEval(
        id=eval_id,
        kind=str(kind),
        prompt=prompt.strip(),
        expected_output=expected.strip(),
        files=tuple(files),
        expectations=tuple(e.strip() for e in expectations),
    )
