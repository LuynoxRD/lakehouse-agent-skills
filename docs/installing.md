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

## Which tools this reaches

Measured by installing one skill with `--agent '*'` into an empty project and listing what
appeared.

**Skills reach 77 tools.** That breadth is the format's, not this pack's: a `SKILL.md` is markdown
with frontmatter, so anything that reads one can use these.

They do not all read the same place, and the split is worth knowing.

**Nineteen of them share `.agents/skills`**, which is the cross-tool convention rather than any
one product's directory: Amp, Antigravity, Antigravity CLI, Cline, Codex, **Cursor**, Deep Agents,
Dexto, Firebender, Gemini CLI, GitHub Copilot, Kimi Code CLI, Loaf, **OpenCode**, PromptScript,
Replit, Universal, Warp and Zed. One directory, nineteen tools, and it is where most of the
familiar names live.

**The rest read their own**, as `.<tool>/skills/`: Windsurf, Continue, Roo, Kilo Code, Junie,
Trae, Goose, OpenHands, Crush, Kiro, Qoder and a long tail.

The practical consequence is that looking for a `.cursor/` or `.opencode/` directory after an
install finds nothing and means nothing. `.cursor/skills` exists, but as Cursor's **global**
directory; its project directory is the shared one. Check `.agents/skills/` before concluding a
tool was skipped.

**The rest of the pack is narrower, and deliberately so.**

| Component | Reaches |
| --- | --- |
| The 14 skills | All 77 tools above, through `.agents/skills` or the tool's own directory, and anything else that reads a `SKILL.md` |
| The 9 commands | Claude Code, as `.claude/commands/*.md`, and Gemini, as `.gemini/commands/*.toml`. Both are generated from `commands/*.toml` by `scripts/sync_commands.py`. |
| The 3 reviewer personas | Claude Code, through the plugin's default `agents/` directory. Other tools have their own subagent mechanisms and none of them has been verified here. |
| The session hook | Claude Code, through `hooks/hooks.json` |

The skills are the portable part and the pack is built that way on purpose: everything a skill
cannot work without is inside its own `SKILL.md`, so the tools that get only the skills still get
the discipline. The commands are a convenience for reaching a stage by name, and the personas and
the hook are Claude Code affordances layered on top.

## Verifying an install

```bash
npx skills list
```

Count what came back. Fourteen is the whole catalogue; anything less means a skill was dropped,
and the first place to look is the frontmatter of the ones that are missing.

For the plugin, CI does the counting on every pull request: it installs, reads the component
inventory, and fails when the names loaded differ from the names this repository ships. That step
exists because an install exits zero whether it loaded everything or nothing, which is how three
reviewer personas once shipped with nothing reading them.
