# lakehouse-agent-skills

Data-engineering discipline for AI coding agents: profile before you clean, clean before you chart, persist to columnar storage, query it with SQL, then build the dashboard by BI rules rather than by taste — the chart the data allows, colour that encodes, panels placed by what they hold — and disclose exactly what was and was not processed.

> **Scope:** this file configures agents working on *this repository itself*. It is not meant to be copied into other projects or into a global agent configuration; the reusable assets are the skills in `skills/`.

## Project structure

```
skills/            → one directory per skill, each with a SKILL.md (the only required file)
references/        → checklists shared by more than one skill (never inside a skill directory)
commands/          → slash commands for the data lifecycle (source of truth; per-tool copies are validated for parity)
agents/            → reviewer personas used by the lifecycle commands
hooks/             → session lifecycle hooks (minimal, tested, no network)
evals/             → eval cases, synthetic fixtures, framework docs (see evals/README.md)
scripts/           → validators and the eval runner, Python standard library only
scripts/skill-scripts/ → the one copy of each script a skill ships; `sync_skill_scripts.py` copies it into every skill whose SKILL.md names it
tests/             → pytest suite covering every validator and the eval runner
docs/              → skill anatomy, getting started, per-tool setup guides
.github/           → CI workflows, Dependabot, CODEOWNERS
```

## The data lifecycle

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE
/profile  /clean   /model   /query   /chart      /dashboard /insight  /disclose        (+ /redact, cross-cutting)
```

The meta-skill `using-lakehouse-skills` routes a task to the right skill. If a task matches a skill, invoke it and follow it completely; never apply a skill halfway.

## Conventions (enforced by `scripts/validate_*.py`)

- Every skill lives in `skills/<name>/SKILL.md`; `name` in the frontmatter equals the directory name, lowercase-hyphen-separated.
- The `description` states what the skill does in third person, then one or more `Use when …` triggers. Maximum 1024 characters. Never summarize the workflow in the description.
- Standard sections: Overview, When to Use (with exclusions), Core Process, Common Rationalizations (excuse | reality), Red Flags, Verification (evidence-backed checklist). Equivalent headings are fine when they serve the same purpose.
- Keep `SKILL.md` under 500 lines. Move long reference material to `references/` (shared) or a supporting file inside the skill (used by that skill only). Keep critical guidance inline: a per-skill install does not carry `references/`. A per-skill install carries the skill's own directory and nothing above it, so a script the skill tells the reader to run lives in `skills/<name>/scripts/`, generated from `scripts/skill-scripts/` and checked for drift by `validate_skill_scripts.py`.
- Every skill ships `evals/cases/<name>.json`: at least 3 positive triggers, 2 negative triggers with `owner`, and 1 behavioral eval backed by a fixture under `evals/fixtures/<name>/` with a `FIXTURE.md` describing how it was generated.
- Commands live in `commands/*.toml`; per-tool copies must stay in parity and share descriptions.
- Manifest versions (`plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`) must match.
- All content, code comments, commit messages, and fixtures are in English.

## Writing principles

1. Process over knowledge: steps, not facts.
2. Specific over general: name the command, the threshold, the file.
3. Evidence over assumption: every verification checkbox needs proof.
4. Anti-rationalization: every skippable step gets a rebuttal in the rationalizations table.
5. Ground every rule in the documented standard of the discipline (record linkage, visualization theory, accessibility, open table formats, the tools' own docs), never in one product's calibration.
6. Token-conscious: if removing a section would not change agent behavior, remove it.

## The one description, and its short form

Six places carry the sentence that says what this pack is, and `validate_versions.py` refuses a
tree where the four manifests disagree (`manifest/description-mismatch`). Two more carry a
deliberately shorter form: the README's opening line and the repository's About, both of which a
person reads at a glance and a listing truncates.

**The short form is the long one with the parenthetical clause removed, and nothing else.** Same
words, same order, one clause fewer. Rewording it instead is how two descriptions of one package
drift into saying different things, which is what happened before the rule existed. Neither the
README nor the About is a file any validator can compare, so this is the record of the decision.

## Vendor neutrality

Skills, docs, fixtures, commands, and commit messages never promote or name a commercial product, company, or service as origin, sponsor, or recommendation, and never compare analytics or BI products. Naming a tool a skill is literally about (DuckDB, openpyxl, a charting library) is fine. CI enforces this policy.

## Security rules for content

A `SKILL.md` is code that runs inside someone else's agent. Treat it that way.

- No skill or script instructs network calls to undocumented hosts, `curl … | sh`, `eval`, base64-decoded payloads, writes outside the project directory, deletion of user data, or reading and sending environment variables. `scripts/validate_skill_safety.py` fails the build on these patterns.
- Skills point at the user's own package manager and a minimum version; they never fetch installers.
- Scripts under `skills/<name>/scripts/` use `#!/usr/bin/env bash`, `set -euo pipefail`, status on stderr, JSON on stdout, a cleanup trap, and no network.
- Fixtures are 100% synthetic. No real personal data, no real company data, nothing downloaded from the internet.
- Examples never paste raw rows containing personal data into a prompt; see the `data-privacy-before-llm` skill.
- Changes to `skills/`, `hooks/`, `scripts/`, `commands/`, `agents/`, and `.github/` require code-owner review.

## Working on the repo

- Tooling is Python 3.12+ managed with `uv` (`uv sync --extra dev --extra fixtures`), linted with `ruff`, type-checked with `mypy --strict`, tested with `pytest`. The `fixtures` extra is installed for tests too, because the shipped `verify-output.sh` needs the query engine it documents and a skipped test is not a test. Validators and the eval runner use the standard library only; third-party packages exist solely to generate fixtures and are locked in `uv.lock`. Never `pip install` directly. Node is only needed to run Claude Code's plugin validator and the `skills` CLI; this repository has no `package.json`.
- Run `bash scripts/ci-local.sh` before every push. It runs ruff, mypy, pytest, every validator, the Tier 2 evals, the secret scan, and the vendor-neutrality check.
- Tier 3 behavioral evals spend tokens: run them on demand with `uv run scripts/run_evals.py --behavioral <skill>` and read the results before trusting a skill.
- Never lower the Tier 2 rank-1 floor to make a regression pass. Fix the description instead and, if a change is rejected on eval evidence, add a row to `evals/skill-impact.md`.
- Line endings are LF everywhere (`.gitattributes`); bash scripts with CRLF fail in CI.
- Do not create empty `scripts/` or `references/` directories to mirror other skills.
- Before proposing a new skill, search the catalog and open PRs, justify the gap, and prefer extending an existing skill over adding a near-duplicate. `CONTRIBUTING.md` is the single source of truth for that workflow.
