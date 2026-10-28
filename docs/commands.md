# Commands

Slash commands for the data lifecycle, one TOML file per command in `commands/`. That directory is
the source of truth; the per-tool copies under `.claude/commands/` (markdown with a `description`
frontmatter and the prompt as body) and `.gemini/commands/` (identical TOML) are validated for
parity by `scripts/validate_commands.py`. A Claude copy carries no frontmatter key but
`description`: a key such as `allowed-tools` would change how the command runs without the source
knowing, so the validator refuses it.

This page lives in `docs/` and not in `commands/` because `claude plugin validate` reads every
markdown file in `commands/` as a command definition, and refuses one without frontmatter under
`--strict`. Keep `commands/` to the TOML sources.

```toml
description = "Profile a dataset before cleaning or charting it."

prompt = """
Invoke the `etl-before-dashboard` skill ...
"""
```

Every prompt invokes at least one existing skill by its backticked name and writes its artifacts
to the canonical paths in [docs/skill-anatomy.md](skill-anatomy.md).

**Never edit a copy by hand.** After changing a command, run
`uv run python scripts/sync_commands.py` and commit all three files. The validator can only tell
you that a copy drifted; the sync script is what stops it drifting, because keeping three files in
step by hand is a job nobody wins twice.

| Phase | Command | Artifact |
| --- | --- | --- |
| PROFILE | `/profile` | `docs/data/profile.md` |
| CLEAN | `/clean` | `docs/data/cleaning-log.md`, `data/clean/` |
| MODEL | `/model` | `docs/data/model.md`, `data/curated/` |
| QUERY | `/query` | SQL and its result, with `EXPLAIN` |
| VISUALIZE | `/chart` | chart specification |
| ASSEMBLE | `/dashboard` | layout and widgets |
| NARRATE | `/insight` | insights with sample size and comparison base stated |
| DISCLOSE | `/disclose` | `docs/data/disclosure.md` |
| cross-cutting | `/redact` | masked data and a record of what was masked |
