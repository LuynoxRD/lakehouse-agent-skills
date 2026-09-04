#!/usr/bin/env python3
"""Run the skill evals.

Tier 2 (default, free, runs in CI): rank every skill description against the trigger prompts in
evals/cases/*.json with TF-IDF over stemmed tokens. Positive prompts must rank the skill within
`top_k`; negative prompts must rank their `owner` above the skill; descriptions that collide are
reported. The rank-1 rate is compared against the floor in evals/config.json.

Tier 3 (`--behavioral <skill>`, spends tokens): run the skill's behavioral evals with a headless
agent against the fixtures and judge the transcript. Results land in evals/results/.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lib import frontmatter
from lib.behavioral import BehavioralSettings, EvalOutcome, run_case
from lib.evals_schema import EvalCase, load_cases
from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report
from lib.tfidf import Index, build_index

DEFAULT_CONFIG: dict[str, float] = {
    "min_rank1_percent": 0.0,
    "collision_error": 0.75,
    "collision_warning": 0.5,
}
CONFIG_KEYS = frozenset({*DEFAULT_CONFIG, "notes"})


@dataclass(frozen=True, slots=True)
class Config:
    """Thresholds read from evals/config.json."""

    min_rank1_percent: float
    collision_error: float
    collision_warning: float


@dataclass(slots=True)
class Tier2Result:
    """Aggregated Tier 2 outcome."""

    report: Report
    positives_total: int = 0
    positives_passed: int = 0
    rank1_hits: int = 0
    negatives_total: int = 0
    negatives_passed: int = 0
    collision_errors: int = 0
    collision_warnings: int = 0

    @property
    def rank1_percent(self) -> float | None:
        """Share of positive prompts whose skill ranked first, or None without prompts."""
        if self.positives_total == 0:
            return None
        return 100.0 * self.rank1_hits / self.positives_total


def load_config(layout: Layout, report: Report) -> Config:
    """Read thresholds; fall back to defaults with a warning when the file is missing."""
    values = dict(DEFAULT_CONFIG)
    path = layout.eval_config
    if not path.is_file():
        report.warning("config/missing", "evals/config.json not found; using defaults", path)
    else:
        try:
            document = json.loads(read_text(path))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            report.error("config/unreadable", f"cannot parse JSON: {error}", path)
            document = {}
        if not isinstance(document, dict):
            report.error("config/shape", "top level must be a JSON object", path)
            document = {}
        for key, value in document.items():
            if key not in CONFIG_KEYS:
                report.warning("config/unknown-key", f"unknown key '{key}'", path)
            elif key in DEFAULT_CONFIG:
                if isinstance(value, bool) or not isinstance(value, int | float):
                    report.error("config/shape", f"'{key}' must be a number", path)
                else:
                    values[key] = float(value)
    return Config(
        min_rank1_percent=values["min_rank1_percent"],
        collision_error=values["collision_error"],
        collision_warning=values["collision_warning"],
    )


def load_catalog(layout: Layout, report: Report) -> dict[str, str]:
    """Skill name to description, from every SKILL.md frontmatter."""
    catalog: dict[str, str] = {}
    for skill_dir in layout.skill_dirs():
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            report.error("catalog/missing-skill-md", "directory has no SKILL.md", skill_dir)
            continue
        try:
            parsed = frontmatter.parse(read_text(skill_file))
        except (frontmatter.FrontmatterError, UnicodeDecodeError) as error:
            report.error("catalog/frontmatter", str(error), skill_file)
            continue
        description = parsed.data.get("description")
        if not isinstance(description, str) or not description.strip():
            report.error("catalog/description", "skill has no description to rank", skill_file)
            continue
        catalog[skill_dir.name] = description
    return catalog


def build_catalog_index(catalog: dict[str, str]) -> Index:
    """Index descriptions; the skill name (with hyphens split) is part of its document."""
    return build_index(
        {name: f"{name.replace('-', ' ')} {description}" for name, description in catalog.items()}
    )


def run_tier2(
    cases: Sequence[EvalCase], catalog: dict[str, str], config: Config, report: Report
) -> Tier2Result:
    """Score every case against the catalog."""
    result = Tier2Result(report=report)
    if not catalog:
        return result
    index = build_catalog_index(catalog)
    for case in cases:
        if case.skill_name not in catalog:
            report.error("tier2/unknown-skill", "case has no skill in the catalog", case.path)
            continue
        _score_positives(case, index, result)
        _score_negatives(case, index, catalog, result)
    _check_collisions(index, catalog, config, result)
    return result


def _score_positives(case: EvalCase, index: Index, result: Tier2Result) -> None:
    for trigger in case.positives:
        ranking = index.rank(trigger.prompt)
        names = [name for name, _ in ranking]
        position = names.index(case.skill_name) + 1
        result.positives_total += 1
        if position == 1:
            result.rank1_hits += 1
        if position <= trigger.top_k:
            result.positives_passed += 1
        else:
            result.report.error(
                "tier2/positive",
                f"'{trigger.prompt[:80]}' ranked {case.skill_name} at #{position} "
                f"(top_k={trigger.top_k}); leaders: {', '.join(names[:3])}",
                case.path,
            )


def _score_negatives(
    case: EvalCase, index: Index, catalog: dict[str, str], result: Tier2Result
) -> None:
    for negative in case.negatives:
        result.negatives_total += 1
        if negative.owner not in catalog:
            result.report.error(
                "tier2/owner-unknown",
                f"negative trigger owner '{negative.owner}' is not in the catalog",
                case.path,
            )
            continue
        scores = dict(index.rank(negative.prompt))
        if scores[negative.owner] > scores[case.skill_name]:
            result.negatives_passed += 1
        else:
            result.report.error(
                "tier2/negative",
                f"'{negative.prompt[:80]}' scored {case.skill_name} "
                f"({scores[case.skill_name]:.3f}) at or above owner {negative.owner} "
                f"({scores[negative.owner]:.3f})",
                case.path,
            )


def _check_collisions(
    index: Index, catalog: dict[str, str], config: Config, result: Tier2Result
) -> None:
    names = sorted(catalog)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            similarity = index.similarity(left, right)
            if similarity >= config.collision_error:
                result.collision_errors += 1
                result.report.error(
                    "tier2/collision",
                    f"descriptions of {left} and {right} are {similarity:.0%} similar; "
                    "agents cannot tell them apart",
                )
            elif similarity >= config.collision_warning:
                result.collision_warnings += 1
                result.report.warning(
                    "tier2/collision",
                    f"descriptions of {left} and {right} are {similarity:.0%} similar",
                )


def tier2_summary(result: Tier2Result, floor: float) -> str:
    """One line with the numbers a reviewer needs."""
    rank1 = result.rank1_percent
    rank1_text = "n/a" if rank1 is None else f"{rank1:.1f}%"
    verdict = "OK" if result.report.ok else "FAIL"
    return (
        f"tier2: rank-1 {rank1_text} (floor {floor:.0f}%), "
        f"positives {result.positives_passed}/{result.positives_total}, "
        f"negatives {result.negatives_passed}/{result.negatives_total}, "
        f"collisions {result.collision_errors} error(s) {result.collision_warnings} warning(s): "
        f"{verdict}"
    )


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Persist a result document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_outcome(outcome: EvalOutcome, root: Path) -> str:
    """Human-readable Tier 3 outcome."""
    verdict = "PASS" if outcome.passed else ("BLOCKED" if outcome.blocked else "FAIL")
    header = (
        f"{outcome.skill} eval {outcome.eval_id}: {verdict} "
        f"({outcome.duration_seconds:.0f}s, agent exit {outcome.agent_returncode})"
    )
    lines = [header]
    if outcome.blocked:
        # No evidence either way: say so instead of listing expectations as unmet.
        lines.append(f"  the run did not complete, so nothing was measured: {outcome.blocked}")
        return "\n".join(lines)
    for judgement in outcome.judgements:
        marker = "met" if judgement.met else "MISSED"
        evidence = f" -- {judgement.evidence}" if judgement.evidence else ""
        lines.append(f"  [{marker}] {judgement.expectation}{evidence}")
    if outcome.outside_catalogue:
        # A pass that leans on a skill the pack does not ship is not a pass for the pack.
        lines.append(
            "  invoked from the host machine, not from this catalogue: "
            + ", ".join(outcome.outside_catalogue)
        )
    lines.append(f"  transcript: {outcome.transcript_path.relative_to(root).as_posix()}")
    lines.append(f"  verdict:    {outcome.verdict_path.relative_to(root).as_posix()}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """CLI options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_root_argument(parser)
    parser.add_argument(
        "--min-rank1",
        type=float,
        metavar="PERCENT",
        help="rank-1 floor in percent (default: evals/config.json)",
    )
    parser.add_argument("--json", type=Path, metavar="FILE", help="write results as JSON")
    parser.add_argument("--behavioral", metavar="SKILL", help="run Tier 3 for one skill")
    parser.add_argument("--model", help="model for the agent under test")
    parser.add_argument("--judge-model", help="model for the judge (default: --model)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per headless run")
    parser.add_argument(
        "--with-catalog",
        action="store_true",
        help="install every skill, not only the one under test; required for a skill that "
        "routes to other skills, whose names cannot resolve when it is installed alone",
    )
    parser.add_argument(
        "--with-references",
        action="store_true",
        help="also stage references/ (default simulates a per-skill install without them)",
    )
    parser.add_argument(
        "--allow-execution",
        action="store_true",
        help="let the agent under test run commands; without it every command that starts a "
        "program is denied, so a skill that asks for machine-checked evidence cannot comply",
    )
    parser.add_argument("--claude-command", default="claude", help="headless agent executable")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    configure_output()
    args = build_parser().parse_args(argv)
    layout = Layout(args.root.resolve())
    report = Report("run-evals")
    cases, schema_report = load_cases(layout)
    report.extend(schema_report.findings)
    report.checked = schema_report.checked
    catalog = load_catalog(layout, report)

    if args.behavioral:
        return _run_tier3(args, layout, cases, report)

    config = load_config(layout, report)
    floor = config.min_rank1_percent if args.min_rank1 is None else args.min_rank1
    result = run_tier2(cases, catalog, config, report)
    rank1 = result.rank1_percent
    if rank1 is not None and rank1 < floor:
        report.error(
            "tier2/rank1-floor",
            f"rank-1 rate {rank1:.1f}% is below the floor of {floor:.0f}%; fix descriptions, "
            "never lower the floor",
        )
    if not catalog and not cases:
        report.info("tier2/empty", "no skills and no cases yet; nothing to rank")

    print(report.render(layout.root))
    print(tier2_summary(result, floor))
    if args.json is not None:
        payload = report.to_dict(layout.root)
        payload["tier"] = 2
        payload["rank1_percent"] = rank1
        payload["floor_percent"] = floor
        payload["positives"] = {"passed": result.positives_passed, "total": result.positives_total}
        payload["negatives"] = {"passed": result.negatives_passed, "total": result.negatives_total}
        write_json(args.json, payload)
    return report.exit_code


def _run_tier3(
    args: argparse.Namespace, layout: Layout, cases: Sequence[EvalCase], report: Report
) -> int:
    matching = [case for case in cases if case.skill_name == args.behavioral]
    if not matching:
        print(report.render(layout.root))
        print(f"run-evals: no valid eval case for skill '{args.behavioral}'", file=sys.stderr)
        return 1
    settings = BehavioralSettings(
        claude_command=args.claude_command,
        model=args.model,
        judge_model=args.judge_model,
        timeout_seconds=args.timeout,
        with_references=args.with_references,
        with_catalog=args.with_catalog,
        allow_execution=args.allow_execution,
    )
    outcomes = run_case(layout, matching[0], settings)
    for outcome in outcomes:
        print(format_outcome(outcome, layout.root))
    passed = sum(1 for o in outcomes if o.passed)
    blocked = sum(1 for o in outcomes if o.blocked)
    measured = len(outcomes) - blocked
    capability = "commands allowed" if args.allow_execution else "no command execution"
    summary = (
        f"tier3: {passed}/{measured} behavioral eval(s) passed for {args.behavioral} ({capability})"
    )
    if blocked:
        summary += f"; {blocked} did not run and measured nothing"
    print(summary)
    if args.json is not None:
        write_json(
            args.json,
            {
                "tier": 3,
                "skill": args.behavioral,
                "passed": passed,
                "total": len(outcomes),
                "blocked": blocked,
                "execution_allowed": args.allow_execution,
                "outcomes": [
                    {
                        "eval_id": o.eval_id,
                        "passed": o.passed,
                        "blocked": o.blocked,
                        "verdict": o.verdict_path.relative_to(layout.root).as_posix(),
                    }
                    for o in outcomes
                ],
            },
        )
    return 0 if outcomes and passed == len(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
