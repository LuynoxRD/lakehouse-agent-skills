# Contributing

Thank you for helping agents handle data honestly. This document is the single source of truth
for how work enters the repository. `CLAUDE.md` and `AGENTS.md` configure coding agents that work
here; `docs/skill-anatomy.md` describes what a skill must contain; `evals/README.md` describes how
skills are measured.

## Ground rules

- **English only**, in every file, commit message and comment.
- **Vendor neutral.** Skills, docs, fixtures, commands and commit messages never promote or name a
  commercial product, company or service as origin, sponsor or recommendation, and never compare
  analytics or BI products. Naming the tool a skill is literally about (DuckDB, openpyxl, a
  charting library) is fine. CI enforces this with a denylist that is not part of the repository.
- **Skill content is code.** Read `SECURITY.md` before writing a skill, hook or command.
- **Fixtures are 100 % synthetic.** Every `evals/fixtures/<skill>/` folder carries a `FIXTURE.md`
  explaining how the data was generated and which traps it contains. No real personal data, no
  real company data, nothing downloaded from the internet.
- **Zero debt at merge.** A real gap is a blocker, a fix in the same pull request, or an explicit
  issue linked from the pull request. "Approve with minor comments" is not an outcome.

## Development setup

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), `git`, and the
[`gitleaks`](https://github.com/gitleaks/gitleaks) binary on your `PATH` (the version CI pins is in
`.github/workflows/gitleaks.yml`). Node is only needed to run Claude Code's plugin validator and the
`skills` CLI; this repository has no `package.json`.

```bash
uv sync --extra dev          # never plain `uv sync`: it drops the dev extra
uv run pre-commit install    # installs the pre-commit and commit-msg hooks
bash scripts/ci-local.sh     # the whole suite; run it before every push
```

The vendor-neutrality hook and `ci-local.sh` read the denylist from
`~/.config/lakehouse-agent-skills/denylist.txt` (override with `VENDOR_DENYLIST_FILE`). Maintainers
receive that file out of band; the repository never contains it.

Windows users: work from Git Bash. Line endings are LF everywhere (`.gitattributes`), and bash
scripts with CRLF fail in CI.

## Workflow

1. Branch from an up-to-date `main`. One unit of work per branch: a skill with its eval and fixture,
   a validator with its test, a command with its per-tool copies, a documentation page.
2. Commit atomically by kind of change so each commit can be audited on its own. Commit messages
   are in English, imperative mood, and explain why when the diff does not.
3. Run `bash scripts/ci-local.sh` before pushing. All of it, not only the validator you touched.
4. Open the pull request as a **draft**. Read every automated finding and adjudicate it with
   evidence; automated reviewers hallucinate. Fix what is real, answer what is not.
5. Mark the pull request ready when your own audit is clean. CI must be green.
6. Pull requests are **squash-merged**. The pull-request title becomes the commit subject and the
   body becomes the commit message, so write both for the reader of `git log`. Branches are
   deleted after merge. Stacked pull requests are not used.
7. Reference issues with `Closes #N`.

Commands live in `commands/*.toml` and are copied per tool. Run
`uv run python scripts/sync_commands.py` after any change and commit the source together with both
copies; editing a copy directly only produces a parity failure later.

Changes to `skills/`, `hooks/`, `scripts/`, `commands/`, `agents/` and `.github/` require
code-owner review (`.github/CODEOWNERS`).

The protection rules for `main` (required checks, linear history, no force pushes, code-owner
review) live in `.github/branch-protection.json` and are applied with
`gh api -X PUT repos/<owner>/<repo>/branches/main/protection --input .github/branch-protection.json`.
GitHub only enforces them on a private repository under a paid plan, so while the repository is
private the pre-commit hooks, `scripts/ci-local.sh` and the pull-request flow above are the gate;
the rules are applied the moment the repository becomes public.

## Proposing a new skill

Before writing anything:

1. Search the catalog and the open pull requests. A near-duplicate is extended, not added.
2. Open an issue that states the gap: what a generic agent does wrong today, which documented
   standard of the discipline says otherwise, and why no existing skill covers it.
3. Wait for the maintainer to confirm the gap. Skills are expensive to keep coherent; the catalog
   grows on evidence, not enthusiasm.

Then build the skill with the full anatomy in `docs/skill-anatomy.md`, its eval case in
`evals/cases/<name>.json` (at least 3 positive triggers, 2 negative triggers with an `owner`, and
1 behavioral eval backed by a fixture), and its fixture folder with `FIXTURE.md`. Run the Tier 3
behavioral eval at least once with `uv run scripts/run_evals.py --behavioral <name>` and read the
result before asking for review.

## Modifying an existing skill

Descriptions drive routing. If you change one, run the Tier 2 evals and report the before-and-after
rank-1 rate in the pull request. Changes rejected on eval evidence are recorded in
`evals/skill-impact.md`. The rank-1 floor in `evals/config.json` is never lowered to make a
regression pass.

## Commands, agents and hooks

`commands/*.toml` is the source of truth for slash commands; the per-tool copies under `.claude/`
and `.gemini/` must stay identical in description and prompt, and `scripts/validate_commands.py`
enforces it. Hooks are minimal, make no network calls, and ship with a test.

## Validators and the eval runner

Every validator lives in `scripts/`, imports only the standard library, is typed for
`mypy --strict`, and has a test in `tests/`. A validator without a test does not merge. If you
add a rule, document it in `docs/skill-anatomy.md` in the same pull request.

## Reporting problems

Bugs in a skill's guidance, wrong thresholds, missing exclusions and routing mistakes are regular
issues. Security problems follow `SECURITY.md`.

## License

By contributing you agree that your contributions are licensed under the MIT License in `LICENSE`.
