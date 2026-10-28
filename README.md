# Lakehouse Agent Skills

**15 skills, 9 commands and 4 reviewer subagents** that make an AI coding agent profile a file
before it cleans it, clean it before it charts it, build the dashboard by BI rules rather than by
its own guess, and say what it did not cover instead of inventing it.

![You, the agent's code, the lakehouse pipeline and four subagents, all reading and writing one
shared store of project files. Built on DuckDB, Polars, openpyxl and Parquet.](docs/architecture.webp)

## The lifecycle

Data work runs in one direction. Each stage assumes the one before it happened.

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE
/profile  /clean  /model   /query   /chart     /dashboard  /insight  /disclose
                                                              /redact runs across all of them
```

Run a command to enter a stage by name, or just describe the task and let the router pick.

![A sales page for an online clothing store. Four headline figures, delivered revenue,
delivered orders, average order value and cancellation rate, each stating which of the 200 orders
it covers. Below them, the status of every order, delivered revenue by month, and revenue by
category, product, sales channel, payment method and province.](docs/dashboard-example.webp)

A page an agent built with these skills from a 200-order sales export that holds no names or contact
details. The shipped check traced all 85 figures on it back to the curated table. Every figure says
which of the 200 orders it covers, and the category, channel, payment and province breakdowns each
add up to the $7,316.65 at the top.

## What you get

**A working data architecture in your project, not an answer in a chat.**

**The pipeline**

- **Three layers and a trail.** The file that arrived is never written to. Cleaning happens in its
  own layer, every rule logged with the number of rows it touched. What survives is persisted as
  Parquet under `data/curated/`, and everything downstream reads from there.
- **SQL over Parquet at local speed.** DuckDB queries the curated table directly — no server, no
  load step, and a plan you can read. Grouping, ranking, joins and window functions stop being
  loops.
- **Row work at spreadsheet scale.** A worksheet stops at 1,048,576 rows; Polars handles that
  range in memory on an ordinary laptop, with a schema that is declared rather than guessed from
  whichever rows it saw first. If your project already has a dataframe library, the skills tell the
  agent to use that one rather than add a second.
- **Workbooks that survive the round trip.** Formulas, number formats, named ranges, merged
  regions and validation rules are named before anything is written back — because a library
  returns the last value the spreadsheet computed, not the formula that computed it.

**The output**

- **One page, not a pile of files.** A single self-contained HTML file, with linked filters that
  move every panel at once — no bundler, no build step, nothing to compile. Five files each
  carrying their own copy of the drawing library is five charts, not a dashboard.
- **Charts chosen by a rule with an author.** Cleveland and McGill measured how accurately people
  read visual encodings: position, then length, then angle, then area, and colour last. The skill
  applies that order instead of a preference, which is why nine slices in a pie get refused.
- **A dashboard that starts from your question.** Before any layout, the agent writes down the one
  question the page answers and what the reader must be able to do with it. Panels are ranked
  against that question, and anything answering no part of it is a candidate for removal.

**The guardrails**

- **Four reviewers that cannot edit what they review.** One separates what was *verified* from
  what was *asserted*. One audits a finding against its arithmetic — the base of every percentage,
  whether an average is weighted, whether a comparison reverses once the groups are pooled. One
  classifies every field before anything leaves the project. One names the craft decisions a page
  never made, and says plainly that it did not render the page. They run when the result leaves
  your machine or somebody will act on it, and stay out of the way when it is a first look.
- **Numbers you can trace.** Every figure on the page has a query behind it and a population it
  covers. A number typed by hand fails the check.
- **A written record of what was skipped** — rows, sheets, files, in counts rather than adjectives.
- **Nothing personal leaves the project** without somebody deciding it should.

## Skills (15)

| Stage | Skill | Use it when |
| --- | --- | --- |
| Route | [`using-lakehouse-skills`](skills/using-lakehouse-skills) | It is not obvious which skill applies, or the request jumps straight to a chart |
| Shape | [`structured-vs-unstructured-routing`](skills/structured-vs-unstructured-routing) | You are not sure the source is even a table |
| | [`document-extraction-integrity`](skills/document-extraction-integrity) | The numbers are in a PDF, a scan or a photo |
| Values | [`etl-before-dashboard`](skills/etl-before-dashboard) | Anything is about to be charted, cleaned, joined, or has arrived a second time |
| | [`spreadsheet-integrity`](skills/spreadsheet-integrity) | Results are being written back into a workbook |
| | [`honest-data-limits-disclosure`](skills/honest-data-limits-disclosure) | The file is huge, the batch partly failed, or coverage is not total |
| Storage | [`parquet-to-open-table-format`](skills/parquet-to-open-table-format) | Rows need correcting, two jobs write to one folder, or a column has to survive being added |
| | [`duckdb-for-local-analytics`](skills/duckdb-for-local-analytics) | You are grouping, ranking or joining a persisted table |
| Output | [`chart-type-and-library-selection`](skills/chart-type-and-library-selection) | Pie or bar, and which library the destination needs |
| | [`dashboard-color-and-visual-hierarchy`](skills/dashboard-color-and-visual-hierarchy) | Choosing colours, or checking they read on both backgrounds |
| | [`dashboard-layout-by-widget-mix`](skills/dashboard-layout-by-widget-mix) | A page has more panels than fit, or is a grid of equal tiles |
| | [`dashboard-visual-craft`](skills/dashboard-visual-craft) | The page is styled and nothing on it ranks: one size, one gap, centred numbers, an empty first state |
| | [`insight-narrative-integrity`](skills/insight-narrative-integrity) | Writing takeaways, a ranking, a growth figure or a cause |
| Safety | [`data-privacy-before-llm`](skills/data-privacy-before-llm) | Rows are about to be pasted into a prompt or sent to a service |
| | [`safe-live-database-access`](skills/safe-live-database-access) | Connecting to a database other people use |

## Commands (9)

One command per stage, in the order the stages run. Each one names the skills it invokes and
the artefact it leaves behind, so the next stage starts from a file rather than from memory.

| Stage | Command | What it does |
| --- | --- | --- |
| PROFILE | `/profile` | Profile a dataset before anything is cleaned, charted or claimed about it. |
| CLEAN | `/clean` | Clean a profiled dataset, recording every rule and the number of rows it touched. |
| MODEL | `/model` | Decide what one row means and persist the modelled table to columnar storage. |
| QUERY | `/query` | Answer a question with SQL over the table that was already persisted. |
| VISUALIZE | `/chart` | Choose the chart form the data shape allows, then the library the destination needs. |
| ASSEMBLE | `/dashboard` | Lay out a page by what its panels are and how many of them there are. |
| NARRATE | `/insight` | Write findings that survive their own arithmetic before they become sentences. |
| DISCLOSE | `/disclose` | State what the run did not cover, in numbers, before the result is used. |
| REDACT, across all of them | `/redact` | Decide what may leave the project before any rows are sent anywhere. |

They reach Claude Code, as the plugin's commands, and Gemini CLI, generated into
`.gemini/commands/*.toml` from the same sources. Every other tool gets the same steps by
describing the task: the router names the stage, and the stage names its skills.

## Subagents (4)

Four reviewer personas. They read and report; none of them can edit the work it reviews.

| Persona | What it does |
| --- | --- |
| [`data-work-reviewer`](agents/data-work-reviewer.md) | Separates what was **verified** from what was **asserted**, and says which claims have evidence behind them |
| [`claim-auditor`](agents/claim-auditor.md) | Audits a written finding against its arithmetic: the base of every percentage, whether an average is weighted, whether a comparison reverses once groups are pooled |
| [`outbound-data-gate`](agents/outbound-data-gate.md) | Classifies every field that would leave the project and decides what may go, in what form |
| [`design-reviewer`](agents/design-reviewer.md) | Names the craft decisions a page never made, each with the value from the file, and says plainly that it did not render the page |

They run when the result leaves the project or somebody will act on it. For a first look that
stays on your machine, they stay out of the way.

Two session hooks come with them. One refuses to end a turn while a profiled dataset has no
disclosure written, a published page has not been checked, or a page was written without the
skills that own how it reads.

## Install

**Fastest path — one command, any agent.** The open [skills CLI](https://github.com/vercel-labs/skills)
installs into 77 agents. Name yours after `--agent`:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent claude-code -y
npx skills add LuynoxRD/lakehouse-agent-skills --list       # browse before installing
```

Or one skill on its own:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill etl-before-dashboard --agent cursor -y
```

> A per-skill install copies `skills/<name>/` and nothing above it, so the shared `references/`
> checklists do not come with it. Every skill keeps inline what it cannot work without, and says
> next to each link what you lose when the shared file is absent — if one ever stops making sense
> on its own, that is a defect in the skill.

Prefer a native integration, or want the commands and subagents too? Pick your tool.

<details>
<summary><b>Claude Code</b> — the whole pack: skills, commands, subagents, hooks</summary>

The repository is also a plugin. This is the route that brings the nine commands, the four
reviewer subagents and the two session hooks along with the skills, with nothing to copy by hand:

```bash
claude plugin marketplace add LuynoxRD/lakehouse-agent-skills
claude plugin install lakehouse-agent-skills@lakehouse-skills
claude plugin details lakehouse-agent-skills
```

`marketplace add` takes a GitHub repo, a URL or a path, so a local clone works the same way and is
how to try a change before it is merged:

```bash
git clone https://github.com/LuynoxRD/lakehouse-agent-skills.git
claude plugin marketplace add ./lakehouse-agent-skills
claude plugin install lakehouse-agent-skills@lakehouse-skills
```

That second form is the one verified end to end, in a throwaway project. The inventory that comes
back is 24 skills — the fifteen plus the nine commands, which load through the same mechanism —
4 agents, and 2 hooks. About **3,348 tokens always-on**; each skill costs its own text again only
when it fires.

</details>

<details>
<summary><b>Cursor, opencode, Codex, Copilot, Zed and 14 more</b> — one shared directory</summary>

Nineteen tools read the same project directory, `.agents/skills`, which is the cross-tool
convention rather than any one product's folder: Amp, Antigravity, Antigravity CLI, Cline, Codex,
Cursor, Deep Agents, Dexto, Firebender, Gemini CLI, GitHub Copilot, Kimi Code CLI, Loaf, opencode,
PromptScript, Replit, Universal, Warp and Zed.

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent cursor -y
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent opencode -y
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent cursor,opencode,codex -y
```

**Install for one and the rest find them too**, because they are all reading the same place.

</details>

<details>
<summary><b>Windsurf, Continue, Roo, Kilo, Junie, Goose, Kiro and the long tail</b></summary>

These read their own `.<tool>/skills/` directory, so name yours — or install for every agent the
CLI knows in one go:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent windsurf -y
npx skills add LuynoxRD/lakehouse-agent-skills --all          # every agent, every skill
```

</details>

<details>
<summary><b>Gemini CLI</b> — skills, plus the nine commands</summary>

Gemini reads the shared `.agents/skills` directory, so the universal command covers the skills:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent gemini-cli -y
```

The commands exist for Gemini as well, generated into `.gemini/commands/*.toml` from the same
TOML sources. Copy that directory from a clone into your project to get `/profile`, `/clean` and
the rest.

</details>

<details>
<summary><b>Any other agent</b></summary>

A skill is a directory with a `SKILL.md` and no build step, so it works with anything that reads
instruction files. Clone the repository and point your tool at `skills/`.

</details>

**Nothing updates itself.** Neither route watches this repository, so what you install today stays
as it is until you run:

```bash
npx skills update                              # skills, every source
claude plugin update lakehouse-agent-skills    # the plugin route
```

**How far each piece reaches.** The skills go everywhere above. The nine commands reach Claude Code
and Gemini CLI. The four subagents are generated for Claude Code, opencode, Cursor, Gemini CLI and
Codex from one source, each in the form that tool uses to withhold editing; the two hooks are Claude
Code only. Loading was verified end to end in Claude Code and opencode; elsewhere what was measured
is that the files land, and a file arriving is not a skill running.
[docs/installing.md](docs/installing.md) has the full accounting.

## What it works with

| Source | Handled by |
| --- | --- |
| Delimited text — CSV, TSV, exports and extracts | `etl-before-dashboard` |
| Spreadsheet workbooks, read and written, through `openpyxl` | `spreadsheet-integrity` |
| PDFs, scans and photographs of documents | `document-extraction-integrity` |
| Records that are not all the same shape, and free text | `structured-vs-unstructured-routing` |
| Parquet, and the point where a directory of it stops being enough | `parquet-to-open-table-format` |
| Live databases somebody else is using | `safe-live-database-access` |

Cleaned data lands as Parquet under `data/curated/`, and everything downstream reads from there
rather than from the file that arrived.

## What it runs on

The skills add no dependency of their own. They are markdown, and they point at the tools a data
project already has:

- **DuckDB** for anything expressible as a query against the persisted table — grouping, ranking,
  joins, window functions. It reads Parquet and CSV directly, needs no server, and gives you a
  plan you can read.
- **Polars** as the default for the row work that is not a query, because its schema is declared
  rather than re-derived from whichever rows it happened to see. With one standing exception: **if
  your project already uses a dataframe library, the skills tell the agent to use that one.** Two
  libraries disagreeing about a column is the failure the rule exists to prevent.
- **`openpyxl`** for workbooks, which is where the formatting, formulas and merged cells that a
  dataframe silently drops actually live.

`verify-output.sh` runs on Python 3 with the standard library alone, plus DuckDB when it has to
recompute figures — and if DuckDB is missing it says so and fails, rather than reporting the
figures as checked.

## Why Lakehouse Agent Skills?

Do not point an agent at a spreadsheet before you know two things.

**A workbook is not a table. It is compressed XML.** The `.xlsx` on disk is a zip. The XML inside
it is several times larger, and the object model a library builds from that XML is larger again —
on this repository's own 636-row fixture, 21 KB on disk is 122 KB of XML and 1.2 MB in memory. A
model does not read that format. To reason about the file it is flattened to text, cell by cell,
and the structure goes first: formulas, number formats, merged regions, the second sheet.

**When an agent runs out of room it does not stop. It shrinks the file and keeps going.** Its
context is finite, so it reads part of a large file, and the part quietly becomes "the file" in
every sentence that follows. The hosted fix — run Python in a sandbox — moves that ceiling to the
sandbox's memory limit; it does not remove it, and nothing announces when it is hit. Either way the
output arrives looking finished, because there is no visual difference between a number that was
computed and one that was made up.

That is the failure this pack exists to prevent: an agent that destroys the file's structure,
invents what it could not read, and hands you a dashboard of false figures without saying so.
**Nothing here builds a dashboard before the data is profiled and cleaned**, and every stage leaves
a written record of what it did and did not touch.

In this repository's own audited runs the model reported reading a template it never opened, named
a skill that does not exist, and called a page verified because a parser found no errors in it.
Each of those became a rule.

The rest is what an agent cannot do, and none of it is a bug to be fixed:

- **It cannot see the file's past.** How it was exported, which settings produced it, what a blank
  cell meant to whoever typed it. It sees bytes and infers, and an inference nobody wrote down is
  indistinguishable from a measurement.
- **It cannot see the page it just built.** It emits markup; it does not render it. Text sitting on
  top of other text looks identical to text that does not.
- **It starts every session blind.** Nothing carries over unless it was written down, which is why
  each stage here leaves a note behind instead of a memory.

Meanwhile most data still arrives as a spreadsheet, which is a document that looks like a table: a
`Total` row an aggregate will count twice, dates that could be read two ways, leading zeros eaten
so `007` and `7` are now one store.

None of that is exotic. Every one has a boring answer that data engineers have used for decades,
and nothing in the agent's context was asking for it. These skills ask for it.

## How it is checked

Skills are tested on three levels: that they are structurally sound, that a request reaches the
right one (53 prompts that must, 31 that must not, currently 100% first-place), and that a real run
against fixtures with planted defects catches them.

One check runs in your project rather than ours. `verify-output.sh` reads the page an agent
delivered and recomputes every published figure against the table it came from. It reads markup and
never renders, so it prints what it could **not** verify on every run, including a clean one.

## Project structure

```
lakehouse-agent-skills/
├── skills/                                 # 15 skills, a SKILL.md the only required file
│   ├── using-lakehouse-skills/             #   Route: which skill owns this, and how much review
│   ├── structured-vs-unstructured-routing/ #   Shape: is this even a table
│   ├── document-extraction-integrity/      #   Shape: getting numbers off a page
│   ├── etl-before-dashboard/               #   Values: profile, clean, model, persist  ← ships a script
│   ├── spreadsheet-integrity/              #   Values: what a round trip through a workbook drops
│   ├── honest-data-limits-disclosure/      #   Values: what was read, skipped, sampled
│   ├── parquet-to-open-table-format/       #   Storage: when files stop being enough
│   ├── duckdb-for-local-analytics/         #   Storage: asking the persisted table a question
│   ├── chart-type-and-library-selection/   #   Output: the form, then the library  ← ships a script
│   ├── dashboard-color-and-visual-hierarchy/ # Output: what colour encodes
│   ├── dashboard-layout-by-widget-mix/     #   Output: where panels sit, one file  ← ships a script
│   ├── dashboard-visual-craft/             #   Output: type, spacing, alignment, non-data ink
│   ├── insight-narrative-integrity/        #   Output: does the sentence survive its arithmetic
│   ├── data-privacy-before-llm/            #   Safety: what may leave the project
│   └── safe-live-database-access/          #   Safety: connections and writes others share
├── agents/                                 # 4 reviewer subagents, none able to edit what it reviews
├── commands/                               # 9 lifecycle commands, as TOML — the source of truth
├── .claude/commands/                       #   generated copy, checked for parity
├── .gemini/commands/                       #   generated copy, checked for parity
├── .opencode/agent/                        #   generated personas, edits denied by permission
├── .cursor/agents/                         #   generated personas, readonly
├── .gemini/agents/                         #   generated personas, tools allowlisted
├── .codex/agents/                          #   generated personas, as TOML, sandboxed read-only
├── hooks/                                  # 2 session hooks; one blocks a turn with no disclosure
├── references/                             # 3 checklists shared by more than one skill
├── evals/                                  # cases, synthetic fixtures, results
├── scripts/                                # validators, eval runner, and skill-scripts/ (shipped)
├── tests/                                  # pytest over every validator and the eval runner
├── docs/                                   # skill anatomy, installing, the diagram above
└── .claude-plugin/                         # plugin and marketplace manifests
```

The three skills marked **ships a script** carry their own copy of `verify-output.sh` under
`scripts/`, generated from one source and checked for drift, so a per-skill install brings the
check with it rather than a reference to a file that is not there.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) has the workflow. Skills are code that runs inside somebody
else's agent, so nothing here fetches an installer, pipes a script into a shell, or reads
environment variables — and a validator fails the build on those patterns rather than trusting
review to catch them. Every fixture is synthetic. `CODE_OF_CONDUCT.md` applies to every
interaction here, and `PRIVACY.md` says what the plugin reads and writes: nothing leaves the
machine. Questions go to
[Discussions](https://github.com/LuynoxRD/lakehouse-agent-skills/discussions), anything you would
rather not raise in public to [contacto@luynoxrd.com](mailto:contacto@luynoxrd.com), and security
problems follow `SECURITY.md`. [SUPPORT.md](SUPPORT.md) says where each kind of request goes.

## License

[MIT](LICENSE)
