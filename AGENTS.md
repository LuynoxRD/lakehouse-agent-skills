# AGENTS.md

Guidance for AI coding agents (Codex, Cursor, OpenCode, Copilot, Gemini CLI and others) working on
**this repository**. Claude Code reads the same rules from `CLAUDE.md`, which is the full version;
this file is the condensed contract.

> **Scope:** this file configures agents that develop `lakehouse-agent-skills` itself. It is not
> meant to be copied into other projects. The reusable assets are the skills in `skills/`.

## What this repository is

Portable data-engineering discipline skills for AI coding agents, in the open `SKILL.md` format:
profile before you clean, clean before you chart, persist to columnar storage, query it with SQL,
pick the chart the data deserves, lay the dashboard out by widget mix, and disclose exactly what
was and was not processed. Everything here is vendor-neutral and written in English.

## Non-negotiable rules

1. **English everywhere.** Skills, docs, commit messages, comments, fixtures, CI output.
2. **Vendor neutrality.** Never name a commercial product, company or service as origin, sponsor
   or recommendation, and never compare analytics or BI products. Tools a skill is literally about
   (DuckDB, openpyxl, a charting library) may be named. CI enforces this.
3. **Skill content is code.** No network calls to undocumented hosts, no `curl … | sh`, no `eval`,
   no decoded payloads, no writes outside the user's project, no reading or sending environment
   variables. `scripts/validate_skill_safety.py` fails the build on these.
4. **Synthetic fixtures only**, each folder with a `FIXTURE.md` describing how it was generated.
5. **Python tooling, standard library only** for validators and the eval runner. Manage the
   environment with `uv sync --extra dev`; never `pip install`. No `package.json`.
6. **One skill per directory** under `skills/<name>/SKILL.md`, frontmatter `name` equal to the
   directory, a description in third person ending with `Use when …` triggers, and the standard
   sections (Overview, When to Use, Core Process, Common Rationalizations, Red Flags,
   Verification). Every skill ships an eval case and a fixture.
7. **Run `bash scripts/ci-local.sh` before every push.** It runs ruff, mypy, pytest, every
   validator, the Tier 2 evals, the secret scan and the vendor-neutrality check.
8. **Never lower an eval floor to make a regression pass.** Fix the description; record rejected
   changes in `evals/skill-impact.md`.

## Where things live

| Path | Purpose |
| --- | --- |
| `skills/<name>/SKILL.md` | one skill per directory, the only required file |
| `references/` | checklists shared by more than one skill |
| `commands/*.toml` | slash commands for the data lifecycle; per-tool copies are validated for parity |
| `agents/` | reviewer personas used by the lifecycle commands |
| `hooks/` | session lifecycle hooks: minimal, tested, no network |
| `evals/` | eval cases, synthetic fixtures, framework docs |
| `scripts/` | validators and the eval runner |
| `tests/` | pytest suite for every validator and the runner |
| `docs/` | skill anatomy, getting started, per-tool setup |

The contributor workflow (branching, pull-request unit, review, squash merge) is in
`CONTRIBUTING.md`. The security policy is in `SECURITY.md`.
