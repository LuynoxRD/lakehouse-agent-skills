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
  (`skill/empty-directory`). Files other than markdown next to `SKILL.md` are flagged
  (`skill/unexpected-file`).
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

The body opens with a level-1 title (`skill/title`) and contains these sections, in this order.
Equivalent headings are accepted when they serve the same purpose; the alias list is in
`scripts/lib/skill_lint.py`.

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
contains: a download piped into a shell, `eval` or `Invoke-Expression`, base64 decoding,
recursive deletes outside temporary directories, writes outside the project, environment
variables read or sent anywhere, global package installs, links to installers, instructions to
ignore previous instructions, or invisible characters. Network commands are errors unless the
host is on the documentation allowlist, and even then they warn. Plain links to unknown hosts
warn. Shell scripts under `skills/<name>/scripts/` start with `#!/usr/bin/env bash`, set
`set -euo pipefail` in the first ten lines, install a cleanup `trap`, print status to stderr and
JSON to stdout, and make no network calls.

## Evals

Every skill ships `evals/cases/<name>.json` (`skill/missing-eval-case`, `catalog/orphan-case`)
with at least 3 positive triggers, 2 negative triggers naming the skill that should win, and 1
behavioral eval backed by a synthetic fixture under `evals/fixtures/<name>/` with a `FIXTURE.md`.
`evals/README.md` describes the tiers, the schema and how to run them.
