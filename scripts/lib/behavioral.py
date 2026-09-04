"""Tier 3 behavioral evals: run a skill against a fixture with a headless agent, then judge.

Each eval stages a throwaway workspace containing the skill (installed the way a
per-skill install would place it), the fixture files, and nothing else. A headless
agent session runs the prompt; its transcript is judged against the case's
expectations by a second headless session that answers with JSON only. Raw
transcripts and verdicts are written under ``evals/results/`` (gitignored).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from lib.evals_schema import BehavioralEval, EvalCase
from lib.repo import Layout, confined_path

_MAX_TOOL_INPUT_CHARS = 600
_MAX_TRANSCRIPT_CHARS = 60_000
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_UNSAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Captured output of one subprocess."""

    returncode: int
    stdout: str
    stderr: str


Runner = Callable[..., CommandResult]


@dataclass(frozen=True, slots=True)
class BehavioralSettings:
    """Knobs for a behavioral run."""

    claude_command: str = "claude"
    model: str | None = None
    judge_model: str | None = None
    timeout_seconds: int = 900
    with_references: bool = False
    with_catalog: bool = False
    allow_execution: bool = False


@dataclass(frozen=True, slots=True)
class Judgement:
    """One expectation and whether the transcript met it."""

    expectation: str
    met: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class EvalOutcome:
    """Result of one behavioral eval.

    ``blocked`` separates a run that never happened from a skill that fell short. A quota
    limit, a network failure or a missing binary produces no evidence either way, and
    reporting it as unmet expectations is how an infrastructure failure gets mistaken for a
    result.
    """

    skill: str
    eval_id: str
    passed: bool
    judgements: tuple[Judgement, ...]
    transcript_path: Path
    verdict_path: Path
    duration_seconds: float
    agent_returncode: int
    blocked: str | None = None


def run_command(
    args: Sequence[str], cwd: Path, timeout: int, stdin_text: str | None = None
) -> CommandResult:
    """Run a command with a timeout, never through a shell.

    A long prompt is passed on stdin rather than in argv: Windows caps a whole command line at
    about 32,767 characters, and a judge prompt carrying a transcript is comfortably past that,
    which makes the process fail to start at all.
    """
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv built by this module, no shell
            list(args),
            cwd=cwd,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        stdout = (
            expired.stdout.decode("utf-8", "replace")
            if isinstance(expired.stdout, bytes)
            else (expired.stdout or "")
        )
        return CommandResult(returncode=-1, stdout=stdout, stderr=f"timed out after {timeout}s")
    except FileNotFoundError:
        return CommandResult(returncode=127, stdout="", stderr=f"command not found: {args[0]}")
    except OSError as error:
        return CommandResult(
            returncode=126, stdout="", stderr=f"could not start {args[0]}: {error}"
        )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def stage_workspace(  # noqa: PLR0913 - one argument per thing staged, all named at the call site
    layout: Layout,
    case: EvalCase,
    behavioral: BehavioralEval,
    workspace: Path,
    *,
    with_references: bool,
    with_catalog: bool = False,
) -> None:
    """Copy the skill and the fixture files into an empty workspace.

    Fixture paths come from a JSON file a contributor writes, so they are confined to the
    fixture tree here as well as in the validator: an absolute path would otherwise replace
    the base and copy anything on the machine into the agent's workspace.

    ``with_catalog`` installs every skill instead of only the one under test. A skill that
    routes to other skills cannot be judged alone: on its own, the names it points at do not
    resolve, and an agent correctly reports them as missing.
    """
    skill_source = layout.skills / case.skill_name
    if not skill_source.is_dir():
        raise FileNotFoundError(f"skill directory not found: {skill_source}")
    installed = workspace / ".claude" / "skills"
    if with_catalog:
        for directory in layout.skill_dirs():
            shutil.copytree(directory, installed / directory.name)
    else:
        shutil.copytree(skill_source, installed / case.skill_name)
    if with_references and layout.references.is_dir():
        shutil.copytree(layout.references, workspace / "references")
    for fixture in behavioral.files:
        source = confined_path(layout.eval_fixtures, fixture)
        if source is None:
            raise ValueError(f"fixture path escapes evals/fixtures/: {fixture}")
        if source.is_dir():
            shutil.copytree(source, workspace / source.name, dirs_exist_ok=True)
        elif source.is_file():
            shutil.copy2(source, workspace / source.name)
        else:
            raise FileNotFoundError(f"fixture not found: {source}")


def build_agent_args(prompt: str, settings: BehavioralSettings) -> list[str]:
    """Command line for the agent under test.

    The permission mode decides what the eval can measure at all. Under ``acceptEdits`` the
    agent reads and writes files but every command that starts a program is held for an
    approval no headless session can give, so it cannot run a profile, a query or a checksum.
    A skill whose Verification section asks for machine evidence is unfalsifiable in that mode:
    the agent has no way to comply, and the run still returns a verdict. ``allow_execution``
    lifts that, and it stays off by default because the commands an agent writes then run with
    the invoking user's rights, outside the workspace's reach to contain them.
    """
    args = [
        settings.claude_command,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "bypassPermissions" if settings.allow_execution else "acceptEdits",
    ]
    if settings.model:
        args.extend(["--model", settings.model])
    return args


def build_judge_args(settings: BehavioralSettings) -> list[str]:
    """Command line for the judge session; the prompt itself arrives on stdin."""
    args = [settings.claude_command, "-p", "--output-format", "json"]
    model = settings.judge_model or settings.model
    if model:
        args.extend(["--model", model])
    return args


def detect_run_failure(stream_json: str) -> str | None:
    """Return why the run could not produce evidence, or None when it ran.

    The agent reports an API failure inside its own result event, so a quota limit arrives as a
    successful process with an error payload. Reading it here keeps a blocked run from being
    scored as a skill that did nothing.
    """
    for raw_line in stream_json.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "result":
            continue
        if event.get("is_error") or event.get("terminal_reason") == "api_error":
            status = event.get("api_error_status")
            detail = str(event.get("result", "")).strip() or event.get("terminal_reason", "error")
            return f"HTTP {status}: {detail}" if status else str(detail)
    return None


def extract_transcript(stream_json: str) -> str:
    """Flatten a stream-json trace into readable text: assistant prose, tool calls, final result."""
    parts: list[str] = []
    for raw_line in stream_json.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parts.append(f"[unparsed] {line[:200]}")
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "assistant":
            message = event.get("message")
            content = message.get("content", []) if isinstance(message, dict) else []
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    parts.append(f"[assistant] {block.get('text', '')}")
                elif block.get("type") == "tool_use":
                    payload = json.dumps(block.get("input", {}), ensure_ascii=False)
                    parts.append(
                        f"[tool_use {block.get('name', '?')}] {payload[:_MAX_TOOL_INPUT_CHARS]}"
                    )
        elif kind == "result":
            parts.append(f"[result] {event.get('result', '')}")
    transcript = "\n".join(parts)
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        head = transcript[: _MAX_TRANSCRIPT_CHARS // 2]
        tail = transcript[-_MAX_TRANSCRIPT_CHARS // 2 :]
        transcript = f"{head}\n[... transcript truncated ...]\n{tail}"
    return transcript


def list_workspace_changes(workspace: Path, staged: set[Path]) -> list[str]:
    """Files present after the run that were not staged, relative to the workspace."""
    changed: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path in staged:
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative.startswith(".claude/"):
            continue
        changed.append(relative)
    return changed


def build_judge_prompt(behavioral: BehavioralEval, transcript: str, changes: Sequence[str]) -> str:
    """Instruct the judge to return JSON only."""
    expectations = "\n".join(
        f"{index}. {text}" for index, text in enumerate(behavioral.expectations, 1)
    )
    changed = "\n".join(f"- {name}" for name in changes) or "- (none)"
    return (
        "You are grading a transcript of an AI coding agent working on a data task.\n"
        "Judge each expectation strictly against the transcript and the files it produced. "
        "An expectation is met only when the transcript shows it, not when it is merely "
        "plausible.\n\n"
        f"Task given to the agent:\n{behavioral.prompt}\n\n"
        f"Expected output (guidance, not a literal match):\n{behavioral.expected_output}\n\n"
        f"Expectations:\n{expectations}\n\n"
        f"Files the agent created or modified:\n{changed}\n\n"
        f"Transcript:\n<transcript>\n{transcript}\n</transcript>\n\n"
        "Answer with JSON only, no prose, in exactly this shape:\n"
        '{"results": [{"expectation": "<text>", "met": true, '
        '"evidence": "<short quote or reason>"}]}\n'
        "Include one entry per expectation, in the same order."
    )


def parse_judgement(output: str, expectations: Sequence[str]) -> tuple[Judgement, ...]:
    """Turn the judge's output into one Judgement per expectation; missing entries fail closed."""
    text = output
    try:
        envelope = json.loads(output)
    except json.JSONDecodeError:
        envelope = None
    if isinstance(envelope, dict) and isinstance(envelope.get("result"), str):
        text = envelope["result"]
    results: list[dict[str, object]] = []
    match = _JSON_OBJECT_RE.search(text)
    if match is not None:
        try:
            verdict = json.loads(match.group(0))
        except json.JSONDecodeError:
            verdict = None
        if isinstance(verdict, dict) and isinstance(verdict.get("results"), list):
            results = [item for item in verdict["results"] if isinstance(item, dict)]
    usable = [item for item in results if "met" in item]
    matched: dict[int, dict[str, object]] = {}
    consumed: set[int] = set()
    for position, expectation in enumerate(expectations):
        for index, item in enumerate(usable):
            if index in consumed:
                continue
            if str(item.get("expectation", "")).strip() == expectation:
                matched[position] = item
                consumed.add(index)
                break
    leftovers = iter(item for index, item in enumerate(usable) if index not in consumed)
    judgements: list[Judgement] = []
    for position, expectation in enumerate(expectations):
        chosen: dict[str, object] | None = matched.get(position)
        if chosen is None:
            chosen = next(leftovers, None)
        if chosen is None:
            judgements.append(
                Judgement(expectation, met=False, evidence="judge did not return a verdict")
            )
            continue
        judgements.append(
            Judgement(
                expectation,
                met=bool(chosen.get("met")),
                evidence=str(chosen.get("evidence", "")).strip(),
            )
        )
    return tuple(judgements)


def run_eval(
    layout: Layout,
    case: EvalCase,
    behavioral: BehavioralEval,
    settings: BehavioralSettings,
    runner: Runner = run_command,
) -> EvalOutcome:
    """Stage, run, judge and persist one behavioral eval."""
    started = time.monotonic()
    stamp = time.strftime("%Y%m%dT%H%M%S")
    results_dir = layout.eval_results / case.skill_name
    results_dir.mkdir(parents=True, exist_ok=True)
    # The eval id becomes a file name, so it is reduced to a safe token here as well as being
    # constrained by the schema: an id of "../../x" would otherwise write outside the results.
    safe_id = _UNSAFE_ID_RE.sub("_", behavioral.id) or "eval"
    transcript_path = results_dir / f"{safe_id}-{stamp}.transcript.jsonl"
    verdict_path = results_dir / f"{safe_id}-{stamp}.verdict.json"

    with tempfile.TemporaryDirectory(prefix="lakehouse-eval-") as temporary:
        # The temporary directory can come back in Windows 8.3 short form, such as
        # C:\Users\LUISCA~1\..., which an agent treats as a suspicious path and refuses to read
        # or write without manual approval. Every tool call is then blocked and the eval
        # measures nothing while still producing a verdict. Resolving expands it.
        workspace = Path(temporary).resolve()
        stage_workspace(
            layout,
            case,
            behavioral,
            workspace,
            with_references=settings.with_references,
            with_catalog=settings.with_catalog,
        )
        staged = {path for path in workspace.rglob("*") if path.is_file()}
        agent = runner(
            build_agent_args(behavioral.prompt, settings), workspace, settings.timeout_seconds
        )
        transcript_path.write_text(agent.stdout, encoding="utf-8")
        transcript = extract_transcript(agent.stdout)
        if agent.returncode != 0:
            transcript = (
                f"{transcript}\n[agent exited with {agent.returncode}: {agent.stderr.strip()}]"
            )
        changes = list_workspace_changes(workspace, staged)
        judge_prompt = build_judge_prompt(behavioral, transcript, changes)
        judge = runner(
            build_judge_args(settings), workspace, settings.timeout_seconds, judge_prompt
        )
    blocked = detect_run_failure(agent.stdout)
    if blocked is not None:
        judgements = tuple(
            Judgement(text, met=False, evidence=f"the run did not complete: {blocked}")
            for text in behavioral.expectations
        )
    elif judge.returncode != 0:
        reason = f"the judge did not run (exit {judge.returncode}): {judge.stderr.strip()[:200]}"
        judgements = tuple(
            Judgement(text, met=False, evidence=reason) for text in behavioral.expectations
        )
    else:
        judgements = parse_judgement(judge.stdout, behavioral.expectations)
    passed = (
        blocked is None
        and agent.returncode == 0
        and judge.returncode == 0
        and all(j.met for j in judgements)
    )
    duration = time.monotonic() - started
    verdict_path.write_text(
        json.dumps(
            {
                "skill": case.skill_name,
                "eval_id": behavioral.id,
                "passed": passed,
                "agent_returncode": agent.returncode,
                "judge_returncode": judge.returncode,
                "blocked": blocked,
                # A verdict is only readable next to the capability that produced it: the same
                # skill scores differently when the agent can run a command and when it cannot.
                "execution_allowed": settings.allow_execution,
                "duration_seconds": round(duration, 1),
                "changed_files": changes,
                "judgements": [asdict(j) for j in judgements],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return EvalOutcome(
        skill=case.skill_name,
        eval_id=behavioral.id,
        passed=passed,
        judgements=judgements,
        transcript_path=transcript_path,
        verdict_path=verdict_path,
        duration_seconds=duration,
        agent_returncode=agent.returncode,
        blocked=blocked,
    )


def run_case(
    layout: Layout,
    case: EvalCase,
    settings: BehavioralSettings,
    runner: Runner = run_command,
) -> list[EvalOutcome]:
    """Run every eval of a case.

    ``kind`` says whether an eval needs fixture files staged, not whether it runs. A dialogue
    eval carries its data in the prompt, the way a connector hands rows to an agent that never
    touches a file, and that path deserves the same automatic check as the file path.
    """
    return [run_eval(layout, case, behavioral, settings, runner) for behavioral in case.evals]
