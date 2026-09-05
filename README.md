# lakehouse-agent-skills

Data engineering discipline for AI coding agents. **14 skills, 9 commands and 3 reviewer
subagents** that make an agent profile a file before it cleans it, clean it before it charts it,
and say plainly what it did not cover.

## What you get

- **Numbers you can trace.** Every figure on a delivered page has a query behind it and a
  population it covers. A number typed by hand fails the check.
- **A page, not a pile of files.** One self-contained HTML file, laid out by what its panels are,
  with filters that move every panel at once.
- **The chart the data allows**, not the one that was easiest to reach.
- **A written record of what was skipped** — rows, sheets, files, in counts rather than adjectives.
- **Nothing personal leaves the project** without somebody deciding it should.

## The lifecycle

Data work runs in one direction. Each stage assumes the one before it happened.

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE
/profile  /clean  /model   /query   /chart     /dashboard  /insight  /disclose
                                                              /redact runs across all of them
```

Run a command to enter a stage by name, or just describe the task and let the router pick.

## Skills (14)

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
| | [`insight-narrative-integrity`](skills/insight-narrative-integrity) | Writing takeaways, a ranking, a growth figure or a cause |
| Safety | [`data-privacy-before-llm`](skills/data-privacy-before-llm) | Rows are about to be pasted into a prompt or sent to a service |
| | [`safe-live-database-access`](skills/safe-live-database-access) | Connecting to a database other people use |

## Subagents (3)

Three reviewer personas. They read and report; none of them can edit the work it reviews.

| Persona | What it does |
| --- | --- |
| [`data-work-reviewer`](agents/data-work-reviewer.md) | Separates what was **verified** from what was **asserted**, and says which claims have evidence behind them |
| [`claim-auditor`](agents/claim-auditor.md) | Audits a written finding against its arithmetic: the base of every percentage, whether an average is weighted, whether a comparison reverses once groups are pooled |
| [`outbound-data-gate`](agents/outbound-data-gate.md) | Classifies every field that would leave the project and decides what may go, in what form |

They run when the result leaves the project or somebody will act on it. For a first look that
stays on your machine, they stay out of the way.

Two session hooks come with them. One refuses to end a turn while a profiled dataset has no
disclosure written, or a published page has not been checked.

## Install

The universal CLI knows 77 agents. Put yours after `--agent`:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill '*' --agent claude-code -y
```

One skill on its own:

```bash
npx skills add LuynoxRD/lakehouse-agent-skills --skill etl-before-dashboard --agent cursor -y
```

The commands, subagents and hooks arrive together through the plugin route instead — see
[docs/installing.md](docs/installing.md), which also says exactly how far each piece reaches and
what was verified by running it rather than by reading documentation.

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

## Why

An agent writes correct code. That was never the problem.

The problem is what it cannot do, and none of it is a bug to be fixed:

- **It cannot see the file's past.** How it was exported, which settings produced it, what a blank
  cell meant to whoever typed it. It sees bytes and infers, and an inference nobody wrote down is
  indistinguishable from a measurement.
- **It cannot see the page it just built.** It emits markup; it does not render it. Text sitting on
  top of other text looks identical to text that does not.
- **Its context is finite**, so it reads part of a large file, and the part quietly becomes "the
  file" in every sentence that follows.
- **It starts every session blind.** Nothing carries over unless it was written down, which is why
  each stage here leaves a note behind instead of a memory.
- **Its output looks finished either way.** There is no visual difference between a number that was
  computed and one that was guessed, and the whole risk of this work lives in that sentence.

Meanwhile most data still arrives as a spreadsheet, which is a document that looks like a table: a
`Total` row an aggregate will count twice, dates that could be read two ways, leading zeros eaten
so `007` and `7` are now one store.

None of that is exotic. Every one has a boring answer that data engineers have used for decades,
and nothing in the agent's context was asking for it. These skills ask for it.

## How it is checked

Skills are tested on three levels: that they are structurally sound, that a request reaches the
right one (44 prompts that must, 28 that must not, currently 100% first-place), and that a real run
against fixtures with planted defects catches them.

One check runs in your project rather than ours. `verify-output.sh` reads the page an agent
delivered and recomputes every published figure against the table it came from. It reads markup and
never renders, so it prints what it could **not** verify on every run, including a clean one.

## Project structure

```
skills/       14 skills, one directory each, a SKILL.md as the only required file
agents/       3 reviewer subagents
commands/     9 lifecycle commands (source of truth; per-tool copies are checked for parity)
hooks/        2 session hooks
references/   checklists shared by more than one skill
evals/        eval cases, synthetic fixtures, results
scripts/      validators, the eval runner, and the script the skills ship
tests/        pytest suite over every validator
docs/         skill anatomy and installing
```

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) has the workflow. Skills are code that runs inside somebody
else's agent, so nothing here fetches an installer, pipes a script into a shell, or reads
environment variables — and a validator fails the build on those patterns rather than trusting
review to catch them. Every fixture is synthetic.

## License

[MIT](LICENSE)
