# lakehouse-agent-skills

Data-engineering discipline for AI coding agents, written in the portable
[`SKILL.md`](docs/skill-anatomy.md) format.

Profile before you clean. Clean before you chart. Persist before you query. Say what the run did
not cover. Fourteen skills that make an agent do those in that order, because the order is what
makes the number trustworthy.

## Why this exists

Two ordinary things collided.

**Most data still arrives as a spreadsheet**, and a spreadsheet is a document that looks like a
table. It carries a title row above the header, merged cells that leave a value only on the first
row of a group, a `Total` row that any aggregate will happily count twice, dates that are
genuinely ambiguous until something proves which component is the day, decimals written with a
comma, and identifier columns whose leading zeros were eaten on the way in — so `007` and `7` are
now the same store. None of that is a bug in the file. It is what the format is, and it is why
the discipline below exists.

**And the thing reading it is now an agent.** An agent writes correct code. That was never the
failure. The failure is that it will read one sheet and report on "the file", average a column of
averages, chart a column it never checked the type of, and present all of it in a finished-looking
page that nobody will question again — because it looks finished.

That is not a hypothetical. In one audited run on a 200-row file, the delivered page carried
**three different customer counts**: one in the profile note, one typed into the HTML by hand, and
one in a headline tile. Only one of the three had been computed from anything. The same run
delivered five separate files where one page was asked for, each embedding its own copy of the
drawing library — twenty megabytes to show what one page shows in one — and text that sat on top
of itself on a narrow screen.

Every one of those is a data-engineering failure with a known, boring answer. Nothing in the
agent's context was asking for it.

## What the discipline actually is

Data work runs in one direction, and every stage assumes the one before it happened:

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE
                          REDACT runs across all of them
```

Skipping forward is the whole problem. A chart built from a file nobody profiled is a chart of
whatever the parser guessed, and it does not look any different from a correct one.

Each stage leaves an artifact behind, which is the part that makes it checkable later: a profile
note, a cleaning log with the row count of every rule, a sentence saying what one row means, a
manifest of every published figure with the query that produces it, and a disclosure stating what
the run did **not** reach — in counts, not adjectives.

## What is in the pack

| | Skill | What it owns |
| --- | --- | --- |
| Route | `using-lakehouse-skills` | Which skill applies, and how much review the stakes justify |
| Shape | `structured-vs-unstructured-routing` | Whether this is a table at all |
| | `document-extraction-integrity` | Getting numbers off a PDF or a photograph, and what that loses |
| Values | `etl-before-dashboard` | The order of operations, the traps, the second arrival, relating two tables |
| | `spreadsheet-integrity` | What happens to a workbook when you write to it |
| | `honest-data-limits-disclosure` | What was read, skipped, sampled, and how that gets stated |
| Storage | `parquet-to-open-table-format` | Whether a directory of files is still enough |
| | `duckdb-for-local-analytics` | Asking a persisted table a question |
| Output | `chart-type-and-library-selection` | The form the data allows, then the library the destination needs |
| | `dashboard-color-and-visual-hierarchy` | What colour encodes, and whether it can be read |
| | `dashboard-layout-by-widget-mix` | Where the panels sit, and that the deliverable is one file |
| | `insight-narrative-integrity` | Whether the sentence survives its own arithmetic |
| Safety | `data-privacy-before-llm` | What may leave the project |
| | `safe-live-database-access` | Connections and writes to a system other people use |

Alongside them: **nine slash commands** for the lifecycle, **three reviewer personas** that read
and report but cannot edit what they review, and **two session hooks**, one of which refuses to
let a turn end while a profiled dataset has no disclosure or an unverified page.

## Install

The skills work in any tool that reads the `SKILL.md` convention:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent claude-code -y
```

One skill on its own, if that is all you want:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill etl-before-dashboard --agent claude-code -y
```

The commands, personas and hooks come with the plugin route instead.
[docs/installing.md](docs/installing.md) has all three, with what each one was measured to deliver.

## How we know it works

Three tiers, because "it seemed to help" is not evidence:

1. **Structural** — every skill has the sections that make it usable, under the length that makes
   it readable.
2. **Routing** — 44 prompts that must reach the right skill and 28 that must not, scored by term
   ranking. The floor is 90% first-place; it currently sits at **100%**.
3. **Behavioral** — real runs against synthetic fixtures with known defects planted in them.

And one thing that runs in your project rather than ours: `verify-output.sh` reads the page an
agent delivered, recomputes every published figure against the curated table, and refuses numbers
in the text that no query produces. It writes a receipt on a clean run, so "I ran the check" stops
being something a run says about itself.

## What this does not do

The check reads markup. **It never renders anything.** It cannot see text sitting on top of other
text, a chart whose labels rotate when its container narrows, or a page pinned against one edge —
so it prints what it did not verify on every run, including a clean one. A green result is not a
page being fine, and it says so itself rather than letting you assume otherwise.

That habit is the point of the whole pack, applied to the pack. We measured it against a real run
and it scored 5 out of 10: strong on data discipline, weak on presentation, and expensive. The
findings became fourteen changes, each one a rule an agent has to satisfy rather than a note
somebody has to remember.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) is the single source of truth for proposing a skill. Search the
catalog first, justify the gap, and prefer extending an existing skill over adding a near-duplicate.

A `SKILL.md` is code that runs inside somebody else's agent. Nothing here fetches an installer,
pipes a script into a shell, reads environment variables, or writes outside the project, and
`scripts/validate_skill_safety.py` fails the build on those patterns rather than trusting review
to catch them. Every fixture is synthetic.

## License

[MIT](LICENSE).
