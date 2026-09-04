"""Tests for the Tier 3 behavioral runner, with a fake headless agent."""

from __future__ import annotations

import json
import sys
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

    def __init__(
        self, judge_output: str, *, agent_returncode: int = 0, judge_returncode: int = 0
    ) -> None:
        self.calls: list[list[str]] = []
        self.stdin: list[str | None] = []
        self.workspaces: list[Path] = []
        self.judge_output = judge_output
        self.agent_returncode = agent_returncode
        self.judge_returncode = judge_returncode

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        _timeout: int,
        stdin_text: str | None = None,
    ) -> behavioral.CommandResult:
        self.calls.append(list(args))
        self.stdin.append(stdin_text)
        self.workspaces.append(cwd)
        if "stream-json" in args:
            (cwd / "docs" / "data").mkdir(parents=True, exist_ok=True)
            (cwd / "docs" / "data" / "profile.md").write_text("# Profile\n", encoding="utf-8")
            return behavioral.CommandResult(self.agent_returncode, STREAM, "")
        return behavioral.CommandResult(self.judge_returncode, self.judge_output, "judge stderr")


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
    judge = behavioral.build_judge_args(settings)
    assert judge[-1] == "m2"
    assert "json" in judge
    # The judge prompt carries a transcript, so it travels on stdin, never in argv.
    assert not any(len(part) > 200 for part in judge)
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
    judge_prompt = runner.stdin[1]
    assert judge_prompt is not None
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


def test_a_dialogue_eval_runs_and_stages_no_fixture(repo: Layout) -> None:
    """Data that arrives in the prompt gets the same automatic check as data in a file.

    A connector hands an agent rows it never reads from disk. The discipline claims to be
    agnostic to where data came from, so that path is executed rather than skipped.
    """
    case_path = repo.eval_cases / f"{SKILL_A}.json"
    document = json.loads(case_path.read_text(encoding="utf-8"))
    document["evals"].append(
        {
            "id": "from-a-connector",
            "kind": "dialogue",
            "prompt": 'Rows already in hand: [{"d": "03/04/2025", "amount": "1,5"}]. Chart them.',
            "expected_output": "The same discipline, applied to rows that are not a file.",
            "files": [],
            "expectations": ["Profiles the rows before charting"],
        }
    )
    case_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    runner = FakeRunner(judge_envelope([True, True]))
    outcomes = behavioral.run_case(repo, case, behavioral.BehavioralSettings(), runner)
    assert len(outcomes) == 2, "the dialogue eval was skipped"
    assert {o.eval_id for o in outcomes} == {"1", "from-a-connector"}


def test_with_catalog_installs_every_skill(repo: Layout, tmp_path: Path) -> None:
    """A skill that routes to other skills cannot be judged alone.

    Installed on its own, the names it points at do not resolve, and an agent correctly
    reports them as missing, which reads as an invented name in the verdict.
    """
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    alone = tmp_path / "alone"
    alone.mkdir()
    behavioral.stage_workspace(
        repo, case, case.evals[0], alone, with_references=False, with_catalog=False
    )
    assert sorted(p.name for p in (alone / ".claude" / "skills").iterdir()) == [SKILL_A]

    whole = tmp_path / "whole"
    whole.mkdir()
    behavioral.stage_workspace(
        repo, case, case.evals[0], whole, with_references=False, with_catalog=True
    )
    assert sorted(p.name for p in (whole / ".claude" / "skills").iterdir()) == repo.skill_names()


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


def test_the_workspace_path_is_resolved_before_the_agent_sees_it(repo: Layout) -> None:
    """A short Windows path makes an agent refuse every tool call.

    The temporary directory can come back as C:\\Users\\LUISCA~1\\..., which is treated as a
    suspicious path needing manual approval. Reads and writes are then blocked, and the eval
    still produces a verdict, so it looks like a skill that did nothing rather than a runner
    that fenced the agent out of its own workspace.
    """
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    runner = FakeRunner(judge_envelope([True, True]))
    behavioral.run_case(repo, case, behavioral.BehavioralSettings(), runner)
    assert runner.workspaces, "the runner never staged a workspace"
    for workspace in runner.workspaces:
        assert "~" not in str(workspace), workspace
        assert workspace == workspace.resolve()


def test_a_judge_that_never_ran_is_reported_as_such(repo: Layout) -> None:
    """A launch failure must not read as an agent that fell short.

    The judge prompt carries a transcript. When it travelled in argv it exceeded the Windows
    command-line limit, the process never started, and every expectation was reported as
    unmet with no hint that the judge was the thing that failed.
    """
    cases, _ = load_cases(repo)
    case = next(c for c in cases if c.skill_name == SKILL_A)
    runner = FakeRunner("", judge_returncode=126)
    outcome = behavioral.run_case(repo, case, behavioral.BehavioralSettings(), runner)[0]
    assert not outcome.passed
    assert all("the judge did not run (exit 126)" in j.evidence for j in outcome.judgements)


def test_run_command_carries_a_large_prompt_and_unicode_through_a_real_process(
    tmp_path: Path,
) -> None:
    """Exercise the real subprocess path, not a stand-in.

    Every runner defect found so far lived here rather than in the logic: a prompt too long for
    a Windows command line, output the console encoding could not carry, a workspace path the
    agent refused. A fake runner validates the logic and cannot see any of them, so this test
    spawns a real process, feeds it a prompt far past the 32,767-character command-line limit,
    and has it echo a character outside the legacy code page.
    """
    script = tmp_path / "echo_prompt.py"
    script.write_text(
        "import sys\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        "text = sys.stdin.read()\n"
        "print(len(text), '\\u2192', sys.argv[1:], sep='|')\n",
        encoding="utf-8",
    )
    prompt = "x" * 100_000
    result = behavioral.run_command(
        [sys.executable, str(script), "-p"], tmp_path, 60, stdin_text=prompt
    )
    assert result.returncode == 0, result.stderr
    length, arrow, argv = result.stdout.strip().split("|")
    assert int(length) == len(prompt)
    assert arrow == "→"
    assert "-p" in argv


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
