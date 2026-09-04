# Installing

Three routes, in order of how much of the pack they give you. Everything below was run against
this repository rather than written from documentation; where something was not run, it says so.

## The whole catalogue, into one project

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent claude-code -y
```

Verified: thirteen skills land under `.claude/skills/<name>/`, one directory each. Add `--copy` to
copy the files instead of linking them, `-g` to install for the user rather than the project, and
`--agent '*'` to install for every agent the tool knows about.

`npx skills add <path>` works the same way against a local checkout, which is how to try a change
before it is merged.

## One skill

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill etl-before-dashboard --agent claude-code -y
```

Verified: exactly one file arrives, `.claude/skills/etl-before-dashboard/SKILL.md`. Nothing else.

**That is the constraint the whole pack is written against.** A per-skill install carries no
`references/`, so every skill keeps inline the guidance it cannot work without, and says next to
each link what a reader loses when the shared file is absent. If a skill here ever stops making
sense on its own, that is a defect in the skill, not in the installer.

## As a plugin

The repository is also a plugin with a marketplace manifest at
`.claude-plugin/marketplace.json`, so a local checkout can be added as a marketplace and the
plugin installed from it. That route brings the skills, the nine commands, the three reviewer
personas and the session hook together, rather than the skills alone.

The manifest declares:

| Field | Value | Why |
| --- | --- | --- |
| `skills` | `./skills` | One directory per skill, each with its `SKILL.md` |
| `commands` | `./.claude/commands` | The generated markdown copies, not the TOML sources |
| `agents` | a list of the three persona files | The field rejects a directory string; it takes paths to files |
| `hooks` | `./hooks/hooks.json` | The field takes a JSON configuration file, never a directory of scripts |

Those four shapes were checked against the current plugin reference and against the manifest
validator, which rejects the directory form of `agents` outright.

## What the frontmatter has to survive

A skill is found by reading the frontmatter at the top of its `SKILL.md`. Readers differ in how
strict they are, and the strict ones win, because a file they cannot parse is a skill that is
simply not there. No error, no warning, no entry in the list.

That failure was real here. Four skills whose `description` contained a colon followed by a space
were dropped by the installer while every check in this repository passed. A strict reader takes
the colon as a second mapping separator and gives up on the file.

So `scripts/validate_skills.py` now refuses a plain frontmatter value containing `": "` or `" #"`.
Rewrite the sentence, or quote the whole value. A colon with nothing after it, as in a ratio like
`4.5:1` or a time like `09:30`, is unambiguous and stays allowed.

## Verifying an install

```bash
npx skills list
```

Count what came back. Thirteen is the whole catalogue; anything less means a skill was dropped,
and the first place to look is the frontmatter of the ones that are missing.
