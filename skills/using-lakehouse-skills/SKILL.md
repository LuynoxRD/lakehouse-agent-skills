---
name: using-lakehouse-skills
description: Routes a data request to the skill that owns it and states the order the stages have to run in. Use when starting work on a dataset and it is not obvious which skill applies, when a request jumps straight to a chart or a conclusion, or when work spans more than one stage of the data lifecycle.
---

# Using lakehouse skills

This pack exists because the failures that matter with data are not coding failures. An agent
that writes correct pandas can still chart an unprofiled file, average a column of averages,
read one sheet and report on "the file", or paste a customer table into a prompt. Each skill
here removes one of those failures. This page decides which one applies.

## The one rule

**If a skill applies, invoke it and follow it through.** Half a skill is worse than none: it
produces the confident output without the check that made the output trustworthy. Reading the
skill and then doing something else is the failure mode this pack exists to prevent.

## The lifecycle

Data work runs in one direction. Each stage assumes the one before it happened.

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE
   │        │       │       │         │           │          │         │
   └────────┴───────┴───────┴─────────┴───────────┴──────────┴─────────┘
                    REDACT runs across all of them
```

| Stage | Question it answers | Artifact it leaves behind |
| --- | --- | --- |
| PROFILE | What is actually in this file? | `docs/data/profile.md` |
| CLEAN | What did I change, and why? | `docs/data/cleaning-log.md`, `data/clean/` |
| MODEL | What is the shape worth keeping? | `docs/data/model.md`, `data/curated/` |
| QUERY | What does the data answer? | the query and its result |
| VISUALIZE | Which chart does this question deserve? | a chart specification |
| ASSEMBLE | How do the pieces sit together? | a layout |
| NARRATE | What can be said, and how strongly? | insight text with its base stated |
| DISCLOSE | What did this run *not* cover? | `docs/data/disclosure.md` |
| REDACT | What must never leave the project? | masked data and a record of it |

Skipping forward is the common mistake. A chart built from a file nobody profiled is a chart of
whatever the parser guessed.

## Intent to skill

| The request sounds like | Start with |
| --- | --- |
| "Chart this", "build a dashboard from this file", "summarize this export" | `etl-before-dashboard` skill |
| "Clean this up", "the dates look wrong", "the numbers came in as text" | `etl-before-dashboard` skill |
| "This file is huge", "it won't fit in memory", "just read the first few rows" | `honest-data-limits-disclosure` skill |
| "Process all of these files", "read the workbook" | `honest-data-limits-disclosure` skill |
| "Is this even a table?", "the records don't all have the same fields", "find the themes in this text" | `structured-vs-unstructured-routing` skill |
| "Edit this workbook", "write the results back into the spreadsheet" | `spreadsheet-integrity` skill |
| "Connect to the database", "delete the test rows", "run this against production" | `safe-live-database-access` skill |
| "Paste these rows into the model", "send this to the API", "is there anything identifying in here?" | `data-privacy-before-llm` skill |
| "Revenue per channel", "the loop is too slow", "group and rank this" | `duckdb-for-local-analytics` skill |
| "The new column isn't showing up", "two jobs write to the same folder", "we need to correct rows" | `parquet-to-open-table-format` skill |
| "Pie or bar?", "plot this over time", "what kind of chart?" | `chart-type-and-library-selection` skill |
| "Which colours?", "is red and green enough?", "does it work in dark mode?" | `dashboard-color-and-visual-hierarchy` skill |
| "This page is cluttered", "where does the big table go?", "what belongs on the first screen?" | `dashboard-layout-by-widget-mix` skill |
| "What are the key takeaways?", "which segment is winning?", "did it improve?" | `insight-narrative-integrity` skill |
| "Why did it go up?", "what caused this?" | `insight-narrative-integrity` skill |

When two apply, they compose in lifecycle order. A request to chart a very large export is
`honest-data-limits-disclosure` for the pre-flight, then `etl-before-dashboard` for the work,
then `honest-data-limits-disclosure` again for what the run left out.

## How they divide the ground

These boundaries are what keep the skills from overlapping. Read them before deciding.

- **`etl-before-dashboard` skill** owns the *order of operations* and what happens to values on
  the way: types, locale, encoding, persistence. It does not own coverage claims.
- **`honest-data-limits-disclosure` skill** owns *coverage*: what was read, what was skipped,
  what could not fit, and how that gets stated. It does not own how a value was cleaned.
- **`insight-narrative-integrity` skill** owns *the arithmetic of a claim* and the words built
  on it. It assumes the data is already clean and its coverage already disclosed; it checks
  that the sentence follows from the numbers.
- **`structured-vs-unstructured-routing` skill** owns the question of *what shape the source is*,
  and it runs before profiling. Once the answer is "a table", it hands over and stops.
- **`spreadsheet-integrity` skill** owns *what happens to a document* when a workbook is written.
  It does not own the values inside it.
- **`safe-live-database-access` skill** owns *the connection and the writes* to a system other
  people use. Once rows are in hand, it is finished.
- **`data-privacy-before-llm` skill** owns *what may leave the project*. It applies at any stage,
  because any stage can be the one that sends something.
- **`duckdb-for-local-analytics` skill** owns *asking a persisted table a question*.
- **`parquet-to-open-table-format` skill** owns *whether the storage layer still holds*, which is
  a question about change, never about size.
- **`chart-type-and-library-selection` skill** owns *the form a chart takes*;
  **`dashboard-color-and-visual-hierarchy` skill** owns *what its colours encode and whether they
  can be read*; **`dashboard-layout-by-widget-mix` skill** owns *where the panels sit on a page*.
  Three separate decisions that are usually made as one, badly.

The seam is easy to state: shape comes before values, cleaning is about values, disclosure is
about coverage, narrative is about claims, and privacy cuts across all of them.

## When none of them applies

Not every task touching a file is a data task. Reading a configuration file, editing a fixture,
or changing code that happens to mention a CSV is ordinary work. These skills apply when a
dataset is being turned into an answer.

## Verification

- [ ] The stage this request belongs to is named before any work starts.
- [ ] Every applicable skill was invoked in full, not summarized.
- [ ] No stage was skipped, or the skip is stated in the answer with its reason.
- [ ] Every skill named in the answer exists in this catalog. If a request needs something the
      catalog does not cover, say so plainly rather than naming a skill that is not here.
