# Installing

Three routes, in order of how much of the pack they give you. Everything below was run against
this repository rather than written from documentation; where something was not run, it says so.

## The whole catalogue, into one project

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent claude-code -y
```

Verified: fourteen skills land under `.claude/skills/<name>/`, one directory each, and the
three that tell you to run `verify-output.sh` bring their own copy of it under
`scripts/`, executable. Re-measured by running the command, not by counting the catalogue. Add `--copy` to
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
personas and the two session hooks together, rather than the skills alone.

```bash
claude plugin marketplace add /path/to/lakehouse-agent-skills
claude plugin install lakehouse-agent-skills@lakehouse-skills
claude plugin details lakehouse-agent-skills
```

Verified end to end in a throwaway project. The inventory that comes back is **23 skills**, which
is the fourteen skills plus the nine commands, since commands load through the same mechanism;
**3 agents**; and **2 hooks**, one on `SessionStart` and one on `Stop`. The pack costs about
**2,794 tokens always-on**, and each skill costs its own text again only when it fires.

The manifest declares:

| Field | Value | Why |
| --- | --- | --- |
| `skills` | `./skills` | One directory per skill, each with its `SKILL.md` |
| `commands` | `./.claude/commands` | The generated markdown copies, not the TOML sources |
| `agents` | **not declared** | See below. The default `agents/` directory is what works. |
| `hooks` | **not declared** | `hooks/hooks.json` is loaded by convention. Declaring it makes the plugin fail to load as a duplicate. |

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

### Cursor, opencode, Codex, Copilot and fifteen others

They all work, and they all take the same command. Name your tool, or name several:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent cursor -y
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent opencode -y
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent cursor,opencode,codex -y
```

Nineteen tools share one project directory, `.agents/skills`, which is the cross-tool convention
rather than any single product's folder: Amp, Antigravity, Antigravity CLI, Cline, Codex,
**Cursor**, Deep Agents, Dexto, Firebender, Gemini CLI, GitHub Copilot, Kimi Code CLI, Loaf,
**OpenCode**, PromptScript, Replit, Universal, Warp and Zed. Install for one of them and the rest
find the skills too, because they are all reading the same place.

**The rest read their own**, as `.<tool>/skills/`: Windsurf, Continue, Roo, Kilo Code, Junie,
Trae, Goose, OpenHands, Crush, Kiro, Qoder and a long tail. Those need naming individually, or
`--agent '*'` for all of them at once.

One thing that trips people up, including whoever wrote this document the first time: after
installing for Cursor there is no `.cursor/` directory in the project, and that is correct rather
than a failure. `.cursor/skills` is Cursor's **global** directory; its project directory is the
shared one. Look in `.agents/skills/`.

**The rest of the pack is narrower, and deliberately so.**

| Component | Reaches |
| --- | --- |
| The 14 skills | The installer writes them for any of the 77 names above, into `.agents/skills` or the tool's own directory. **Loading was verified only in Claude Code**; elsewhere what was measured is that the files arrive, and a file arriving is not a skill running. |
| The 9 commands | Claude Code, as `.claude/commands/*.md`, and Gemini, as `.gemini/commands/*.toml`. Both are generated from `commands/*.toml` by `scripts/sync_commands.py`. |
| The 3 reviewer personas | Claude Code, through the plugin's default `agents/` directory. Other tools have their own subagent mechanisms and none of them has been verified here. |
| The 2 session hooks | Claude Code, through `hooks/hooks.json` |

The skills travel furthest and the pack is built that way on purpose: everything a skill cannot
work without is inside its own `SKILL.md` — or, for the three that ship a script, inside their own
directory — so a tool that gets only the skills still gets the discipline. The commands are a
convenience for reaching a stage by name, and the personas and the hooks are Claude Code
affordances layered on top.

That last row is a gap in this repository rather than a limit of those tools. Cursor, opencode,
Codex and Gemini CLI all have a subagent mechanism; what is missing is a generator that writes the
persona into each one's format. It is on the list, not in the box.

## Updating

**Nothing updates itself.** Neither route watches this repository, so a skill installed today stays
exactly as it is until somebody runs a command. That is worth knowing before you rely on a fix
reaching anyone.

```bash
npx skills update                              # skills, every source
npx skills update etl-before-dashboard         # one of them
claude plugin update lakehouse-agent-skills    # the plugin route
```

Two behaviours of `skills update` are worth knowing because neither is obvious:

- **A local-path install is never updated.** Installing from a directory records the source as
  local, and the updater skips local and `node_modules` sources by design. Only an install from
  GitHub is refreshed. If you installed from a checkout to try it, reinstall from GitHub before
  expecting updates.
- **It notices skills that disappeared upstream.** If a skill is removed from this repository, the
  updater lists it and offers to delete the local copy, so a retired skill does not linger in a
  project that once installed it.

### What that means for a security fix

A fix landing on `main` reaches nobody by itself. So on this side of it:

- The version in the manifests moves, and a release is tagged, which is what the security policy
  points at when it says older tags are not patched.
- A vulnerability gets a **GitHub security advisory**, which is the mechanism that actually
  notifies people rather than assuming they check.
- Reporting one goes through private vulnerability reporting, never a public issue. `SECURITY.md`
  has the terms and the response times.

**Dependabot does not do this job**, and it is worth being precise because the name suggests
otherwise. It watches this repository's own toolchain, the pinned GitHub Actions and the locked
Python packages, and it opens pull requests here. It does not look at skill content, and it does
not tell anyone who installed the pack that anything changed. The content is guarded by
`scripts/validate_skill_safety.py` on every pull request; the people who installed it are reached
by advisories and a release.

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
