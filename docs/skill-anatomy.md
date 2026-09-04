# Skill anatomy

A skill is a `SKILL.md` file that a coding agent loads when a task matches its description. It
is code that runs inside someone else's agent, so it has a fixed shape, a strict linter and an
eval case. This page is the contract; `scripts/validate_skills.py` enforces it and the rule
identifiers below appear in its output.

## Layout

```
skills/<name>/
├── SKILL.md            # required; the only file most skills need
├── references/         # optional, files used by this skill only
├── scripts/            # optional, bash scripts with the header contract below
├── assets/             # optional, templates or images the skill fills in
└── examples/           # optional, worked examples
```

- `<name>` is lowercase-hyphen-separated, at most 64 characters, and equals the frontmatter
  `name` (`skill/name-mismatch`, `skill/name-format`, `skill/name-length`).
- Do not create empty `references/` or `scripts/` directories to mirror other skills
  (`skill/empty-directory`); a directory holding only a `.gitkeep` counts as empty, since that
  placeholder is the only way an empty directory could reach the repository at all. Files other
  than markdown next to `SKILL.md` are flagged (`skill/unexpected-file`).
- Checklists shared by more than one skill live in the top-level `references/` directory, never
  inside a skill (`references/single-use`, `references/unused`). A per-skill install does not
  carry `references/`, so the guidance a skill cannot work without stays inline, and every link
  to a shared reference names what the reader loses without it.
- `SKILL.md` is UTF-8 without a byte-order mark, uses LF line endings, ends with a newline, and
  stays under 500 lines (`skill/encoding`, `skill/too-long`). Move long material to references.

## Frontmatter

```yaml
---
name: etl-before-dashboard
description: >
  Enforces the profile, clean, model, persist, visualize order for tabular data so charts never
  render raw ingest. Use when a task asks to chart, dashboard or analyze a CSV, spreadsheet or
  parquet file that has not been profiled and cleaned yet.
---
```

- `name` and `description` are required (`skill/name-required`, `skill/description-required`).
- The description states what the skill does in third person, then one or more `Use when …`
  triggers. It is at most 1024 characters, contains a trigger (`skill/description-trigger`), and
  does not start with "This skill", "I" or "You" (`skill/description-voice`). Never summarize the
  workflow in the description: agents route on it, and the Tier 2 evals measure it.
- The frontmatter is a strict YAML subset: scalars, quoted scalars, `|` and `>` block scalars,
  lists of scalars, and one level of nested maps. Flow collections (`[a, b]`) are rejected
  (`skill/frontmatter`).
- Keys Claude Code and the Agent Skills specification define are accepted (`allowed-tools`,
  `disable-model-invocation`, `user-invocable`, `argument-hint`, `metadata`, `license`,
  `compatibility` and the rest); unknown keys warn (`skill/frontmatter-key`). Keys that try to
  exempt a skill from linting (`exempt`, `lint`, `validation` …) are errors
  (`skill/exemption-declared`); the only exemption list lives in the linter.

## Body

The body opens with a level-1 title (`skill/title`) and contains these sections, in this order
(`skill/section-order`). Equivalent headings are accepted when they serve the same purpose; the
alias list is in `scripts/lib/skill_lint.py`.

| Section | Purpose | Rule |
| --- | --- | --- |
| Overview | What the skill makes the agent do differently, in a paragraph. | `skill/missing-section` |
| When to Use | Triggers and, always, when *not* to use it or which skill to use instead. | `skill/missing-section`, `skill/when-to-use-exclusions` |
| Core Process | Numbered steps with the exact command, threshold or file. A `Step N` mentioned in prose must have a `Step N` heading. | `skill/missing-section`, `skill/step-heading` |
| Common Rationalizations | A table of `Excuse \| Reality` rows: every skippable step gets its rebuttal. | `skill/rationalizations-table` |
| Red Flags | Concrete signals that the discipline is being skipped (`head()` without disclosure, a chart before a profile note). | `skill/missing-section` |
| Verification | A checklist of `- [ ]` items, each with the evidence that proves it (a file, a query, a count). | `skill/verification-checklist` |

Other sections (Techniques, Examples, References) are welcome between Core Process and Common
Rationalizations. The router skill `using-lakehouse-skills` is the only skill exempt from the
section rules; it is listed by name in the linter.

References to other skills use the backticked name followed by the word skill, as in "hand off
to the `honest-data-limits-disclosure` skill". A reference to a skill that does not exist warns
(`skill/cross-reference`).

## Writing principles

1. **Process over knowledge.** Steps an agent executes, not facts it could look up.
2. **Specific over general.** Name the command, the threshold, the file path.
3. **Evidence over assumption.** Every verification checkbox says what proves it.
4. **Anti-rationalization.** Every step someone would skip has a rebuttal in the table.
5. **Grounded in the discipline.** Every rule cites the documented standard (record linkage,
   visualization theory, accessibility guidelines, open table formats, a tool's own docs), never
   one product's calibration.
6. **Token-conscious.** If removing a paragraph would not change agent behavior, remove it.
7. **Vendor neutral.** Name the tool the skill is literally about; never promote a product.

## Artifact paths

Commands and skills write into the user's project at fixed locations, and every mention of them
must use the canonical spelling (`scripts/validate_artifact_paths.py`, rules `artifacts/note`
and `artifacts/layer`):

| Artifact | Path |
| --- | --- |
| Profile note | `docs/data/profile.md` |
| Cleaning log | `docs/data/cleaning-log.md` |
| Model note | `docs/data/model.md` |
| Disclosure note | `docs/data/disclosure.md` |
| Raw inputs | `data/raw/` |
| Cleaned data | `data/clean/` |
| Curated parquet | `data/curated/` |

## Safety

`scripts/validate_skill_safety.py` fails the build when skill, hook, command or persona content
contains any of the following:

| Rule | What it stops |
| --- | --- |
| `safety/pipe-to-shell` | a download piped into a shell |
| `safety/substituted-download` | the same download run through `<(…)` or `$(…)` substitution |
| `safety/eval` | `eval`, `exec`, `Invoke-Expression` running text as code |
| `safety/base64-decode` | payloads hidden behind an encoder |
| `safety/recursive-delete` | recursive deletes outside a temporary directory the skill created |
| `safety/write-outside-project` | writes to the home directory, `/etc`, `/usr`, `/var`, `/home`, `/root`, `/opt` or `%APPDATA%` |
| `safety/home-directory` | the same reach from Python (`Path.home()`, `expanduser`, `os.environ['HOME']`) |
| `safety/env-secret-read`, `safety/env-exfiltration` | secrets read from the environment, and secrets sent anywhere |
| `safety/global-install` | global installers (`npm -g`, `pipx`, `uv tool install`, `brew`, `apt`, `cargo`, `go install`, `sudo pip`) |
| `safety/remote-installer` | links to a script or installer to download |
| `safety/instruction-override` | text telling the agent to set aside its instructions |
| `safety/invisible-characters` | zero-width characters that hide text from reviewers |
| `safety/script-language` | a file in a skill's `scripts/` directory that is not a `.sh` bash script |

**Every file that decodes as text is scanned, whatever its extension.** A suffix says nothing
about what an agent will run, so a `.ps1`, a `.bash` or an extensionless file gets the same
treatment as a `.md`. A file that is not valid UTF-8 is an error; a genuinely binary file
(one containing NUL bytes) is reported as unscannable and must be reviewed by hand.

Network rules: a network command inside a script shipped with a skill is always an error. In
other content it is an error when the file names a host outside the documentation allowlist,
because the command's target may be assembled from a variable defined on another line, and a
warning otherwise. Host detection ignores URL userinfo, so
`https://allowed.example@evil.example.net/x` is judged on the host that actually serves it.

Shell scripts under `skills/<name>/scripts/` start with `#!/usr/bin/env bash`, set
`set -euo pipefail` within the first ten lines, install a `trap` that runs on `EXIT`, and make
no network calls. Printing status to stderr and JSON to stdout is a review expectation rather
than a validator rule.

The rules are written to catch the phrasing, not one spelling of it: the test suite feeds them
realistic bypass attempts (process substitution, `exec` instead of `eval`, Python reaching into
`~`, injection wording that names no keyword) alongside legitimate data guidance that uses the
same verbs ("ignore all rows before 2020"), and asserts that the first set fails and the second
passes untouched.

## Evals

Every skill ships `evals/cases/<name>.json` (`skill/missing-eval-case`, `catalog/orphan-case`)
with at least 3 positive triggers, 2 negative triggers naming the skill that should win, and 1
**execution** eval backed by a synthetic fixture. A `dialogue` eval carries no fixture and is
graded by a human, so it never satisfies that minimum on its own. Every skill also owns a
fixture folder at `evals/fixtures/<name>/` with a `FIXTURE.md` (`fixture/missing-folder`), and
the files an eval names must stay inside the fixture tree (`fixture/outside-tree`): the runner
copies them into the agent's workspace. `evals/README.md` describes the tiers, the schema and
how to run them.
