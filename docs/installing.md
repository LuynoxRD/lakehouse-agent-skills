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

```bash
claude plugin marketplace add /path/to/lakehouse-agent-skills
claude plugin install lakehouse-agent-skills@lakehouse-skills
claude plugin details lakehouse-agent-skills
```

Verified end to end in a throwaway project. The inventory that comes back is **23 skills**, which
is the fourteen skills plus the nine commands, since commands load through the same mechanism;
**3 agents**; and **1 SessionStart hook**. The pack costs about **2,535 tokens always-on**, and
each skill costs its own text again only when it fires.

The manifest declares:

| Field | Value | Why |
| --- | --- | --- |
| `skills` | `./skills` | One directory per skill, each with its `SKILL.md` |
| `commands` | `./.claude/commands` | The generated markdown copies, not the TOML sources |
| `agents` | **not declared** | See below. The default `agents/` directory is what works. |
| `hooks` | `./hooks/hooks.json` | The field takes a JSON configuration file, never a directory of scripts |

### The agents field, and why it is absent

This one cost a real defect and is worth writing down.

A directory string, `"agents": "./agents"`, is **rejected by the manifest validator**. An array of
file paths, `["./agents/claim-auditor.md", ...]`, **passes validation and loads nothing**: the
inventory came back `Agents (0)` while every check was green. Omitting the field entirely, so the
default `agents/` directory applies, loads all three.

So the validator and the loader do not agree, and the validator is the one that says yes. The only
way to know which shape works is to install the plugin and read the inventory, which is why that
is a step in this document and not an assumption in it.

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
