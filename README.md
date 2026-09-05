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

## Skills

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

## Subagents

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

## Why

An agent writes correct code. That was never the problem.

The problem is that it will read one sheet and report on "the file", average a column of averages,
chart a column whose type it never checked, and hand all of it back in a page that looks finished.
Most data still arrives as a spreadsheet, which is a document that looks like a table: a `Total`
row an aggregate will count twice, dates that could be read two ways, leading zeros eaten so `007`
and `7` are now one store.

None of that is exotic. Every one has a boring answer that data engineers have used for decades,
and nothing in the agent's context was asking for it. These skills ask for it.

## How it is checked

Skills are tested on three levels: that they are structurally sound, that a request reaches the
right one (44 prompts that must, 28 that must not, currently 100% first-place), and that a real run
against fixtures with planted defects catches them.

One check runs in your project rather than ours. `verify-output.sh` reads the page an agent
delivered and recomputes every published figure against the table it came from. It reads markup and
never renders, so it prints what it could **not** verify on every run, including a clean one.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) has the workflow. Skills are code that runs inside somebody
else's agent, so nothing here fetches an installer, pipes a script into a shell, or reads
environment variables — and a validator fails the build on those patterns rather than trusting
review to catch them. Every fixture is synthetic.

## License

[MIT](LICENSE)
