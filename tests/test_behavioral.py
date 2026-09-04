"""Tests for the Tier 3 behavioral runner, with a fake headless agent."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

import run_evals
from conftest import SKILL_A
from lib import behavioral
from lib.evals_schema import BehavioralEval, load_cases
from lib.repo import Layout

STREAM = "\n".join(
    [
        json.dumps({"type": "system", "subtype": "init"}),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "I will profile first."},
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "docs/data/profile.md"},
                        },
                    ]
                },
            }
        ),
        "not json at all",
        json.dumps({"type": "result", "result": "Done: profile written, 2 rows not processed."}),
    ]
)


class FakeRunner:
    """Records calls and answers as the agent, then as the judge."""

    def __init__(self, judge_output: str, *, agent_returncode: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.judge_output = judge_output
        self.agent_returncode = agent_returncode

    def __call__(self, args: Sequence[str], cwd: Path, _timeout: int) -> behavioral.CommandResult:
        self.calls.append(list(args))
        if "stream-json" in args:
            (cwd / "docs" / "data").mkdir(parents=True, exist_ok=True)
            (cwd / "docs" / "data" / "profile.md").write_text("# Profile\n", encoding="utf-8")
            return behavioral.CommandResult(self.agent_returncode, STREAM, "")
        return behavioral.CommandResult(0, self.judge_output, "")


def judge_envelope(met: Sequence[bool]) -> str:
    verdict = {
        "results": [
            {"expectation": text, "met": flag, "evidence": "quoted"}
            for text, flag in zip(
                [
                    "The agent writes docs/data/profile.md before any chart.",
                    "The agent discloses row counts it did not process.",
                ],
                met,
                strict=True,
            )
        ]
    }
    return json.dumps({"type": "result", "result": "```json\n" + json.dumps(verdict) + "\n```"})


def test_extract_transcript_flattens_events() -> None:
    transcript = behavioral.extract_transcript(STREAM)
    assert "[assistant] I will profile first." in transcript
    assert '[tool_use Write] {"file_path": "docs/data/profile.md"}' in transcript
    assert "[unparsed] not json at all" in transcript
    assert transcript.endswith("[result] Done: profile written, 2 rows not processed.")


def test_parse_judgement_matches_by_text_then_order() -> None:
    expectations = ["first", "second", "third"]
    output = json.dumps(
        {
            "result": json.dumps(
                {
                    "results": [
                        {"expectation": "second", "met": True, "evidence": "e2"},
                        {"expectation": "???", "met": False, "evidence": "e1"},
                    ]
                }
            )
        }
    )
    judgements = behavioral.parse_judgement(output, expectations)
    assert [(j.expectation, j.met) for j in judgements] == [
        ("first", False),
        ("second", True),
        ("third", False),
    ]
    assert judgements[0].evidence == "e1"
    assert judgements[2].evidence == "judge did not return a verdict"
    assert all(not j.met for j in behavioral.parse_judgement("garbage", expectations))


def test_build_args_and_prompt() -> None:
    settings = behavioral.BehavioralSettings(model="m1", judge_model="m2")
    agent = behavioral.build_agent_args("do it", settings)
    assert agent[:3] == ["claude", "-p", "do it"]
    assert "--permission-mode" in agent
    assert "acceptEdits" in agent
    assert agent[-1] == "m1"
    judge = behavioral.build_judge_args("judge it", settings)
    assert judge[-1] == "m2"
    assert "json" in judge
    prompt = behavioral.build_judge_prompt(
        BehavioralEval("1", "execution", "task", "expected", ("f",), ("exp one",)),
        "transcript text",
        ["docs/data/profile.md"],
    )
    assert "1. exp one" in prompt
    assert "- docs/data/profile.md" in prompt
    assert "JSON only" in prompt


def test_run_case_stages_runs_and_persists(repo: Layout) -> None:
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    runner = FakeRunner(judge_envelope([True, True]))
    outcomes = behavioral.run_case(repo, case, behavioral.BehavioralSettings(), runner)
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.passed
    assert [j.met for j in outcome.judgements] == [True, True]
    assert outcome.transcript_path.is_file()
    assert outcome.verdict_path.is_file()
    verdict = json.loads(outcome.verdict_path.read_text())
    assert verdict["changed_files"] == ["docs/data/profile.md"]
    assert len(runner.calls) == 2
    assert runner.calls[0][2] == case.evals[0].prompt
    judge_prompt = runner.calls[1][2]
    assert "I will profile first." in judge_prompt
    assert "- docs/data/profile.md" in judge_prompt


def test_failed_expectation_or_agent_error_fails(repo: Layout) -> None:
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    outcome = behavioral.run_case(
        repo, case, behavioral.BehavioralSettings(), FakeRunner(judge_envelope([True, False]))
    )[0]
    assert not outcome.passed
    outcome = behavioral.run_case(
        repo,
        case,
        behavioral.BehavioralSettings(),
        FakeRunner(judge_envelope([True, True]), agent_returncode=1),
    )[0]
    assert not outcome.passed
    assert outcome.agent_returncode == 1


def test_stage_workspace_copies_skill_and_fixtures(repo: Layout, tmp_path: Path) -> None:
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    behavioral.stage_workspace(repo, case, case.evals[0], workspace, with_references=True)
    assert (workspace / ".claude" / "skills" / SKILL_A / "SKILL.md").is_file()
    assert (workspace / "sales.csv").is_file()
    assert (workspace / "references" / "data-quality-checklist.md").is_file()
    missing = BehavioralEval("9", "execution", "p", "e", ("nowhere/x.csv",), ("x",))
    with pytest.raises(FileNotFoundError):
        behavioral.stage_workspace(repo, case, missing, tmp_path / "ws2", with_references=False)


@pytest.mark.parametrize("escape", ["../../pyproject.toml", "C:/Windows/win.ini", "/etc/passwd"])
def test_stage_workspace_refuses_paths_outside_the_fixture_tree(
    repo: Layout, tmp_path: Path, escape: str
) -> None:
    # The path comes from a JSON file a contributor writes. An absolute path would replace the
    # base in `eval_fixtures / fixture` and copy anything on the machine into the workspace.
    # All three are rejected on every platform, including the drive-letter form that is only
    # dangerous on Windows: the rule must not mean one thing locally and another in CI.
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    hostile = BehavioralEval("1", "execution", "p", "e", (escape,), ("x",))
    workspace = tmp_path / f"ws-{abs(hash(escape))}"
    workspace.mkdir()
    with pytest.raises(ValueError, match="escapes evals/fixtures"):
        behavioral.stage_workspace(repo, case, hostile, workspace, with_references=False)


def test_the_eval_id_cannot_walk_out_of_the_results_directory(repo: Layout) -> None:
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    hostile = BehavioralEval(
        "../../../pwned", "execution", "p", "e", (f"{SKILL_A}/sales.csv",), ("x",)
    )
    outcome = behavioral.run_eval(
        repo,
        case,
        hostile,
        behavioral.BehavioralSettings(),
        FakeRunner(judge_envelope([True, True])),
    )
    assert outcome.transcript_path.resolve().is_relative_to(repo.eval_results.resolve())
    assert outcome.verdict_path.resolve().is_relative_to(repo.eval_results.resolve())
    # The separators are what would walk out; the remaining dots are just characters in a name.
    assert "/" not in outcome.transcript_path.name
    assert "\\" not in outcome.transcript_path.name


def test_run_command_handles_missing_executable(tmp_path: Path) -> None:
    result = behavioral.run_command(["definitely-not-a-real-binary-xyz"], tmp_path, 5)
    assert result.returncode == 127
    assert "command not found" in result.stderr


def test_cli_behavioral_uses_runner(
    repo: Layout, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner(judge_envelope([True, True]))
    monkeypatch.setattr(behavioral, "run_command", runner)
    monkeypatch.setattr(
        run_evals,
        "run_case",
        lambda layout, case, settings: behavioral.run_case(layout, case, settings, runner),
    )
    assert run_evals.main(["--root", str(repo.root), "--behavioral", SKILL_A]) == 0
    out = capsys.readouterr().out
    assert f"{SKILL_A} eval 1: PASS" in out
    assert "tier3: 1/1" in out
    assert run_evals.main(["--root", str(repo.root), "--behavioral", "ghost"]) == 1
