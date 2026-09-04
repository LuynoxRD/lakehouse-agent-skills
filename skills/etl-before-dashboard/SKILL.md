---
name: etl-before-dashboard
description: Enforces the profile, clean, model and persist order before anything is charted, so a visualization never renders raw ingest. Use when a request asks to chart, dashboard or summarize a CSV, spreadsheet or extract, when a chart is being built straight from a source file, or when values arrive as text, with mixed date formats, comma decimals or lost leading zeros.
---

# ETL before dashboard

## Overview

A chart is a claim about data. Building one directly from a source file makes a claim about
whatever the parser guessed: dates read in the wrong order, identifiers stripped of leading
zeros, numbers parsed as text, a total row counted as an observation. The chart looks finished,
which is precisely the problem, because nothing downstream will question it again.

This skill imposes one order and refuses to reverse it:

```
PROFILE ──► CLEAN ──► MODEL ──► PERSIST ──► VISUALIZE
   │           │         │          │
data/raw/  data/clean/   │    data/curated/
                    the grain
```

The layered arrangement is the ordinary one for analytical data: an untouched landing area, a
cleaned area where every change is recorded, and a curated area holding the shape that answers
questions. Each layer is derived from the one before it and none is edited in place, so any
number can be traced back to the bytes that produced it.

## When to Use

Use this skill whenever a dataset arrives as a file and is expected to produce a chart, a
dashboard, a table of figures or a summary. That includes the requests that sound too small to
need it: "just plot this", "give me the totals", "which month was highest".

Use it when values show any of the symptoms in Step 1: text where numbers belong, dates that
could be read two ways, identifiers that lost their leading zeros, a decimal comma read as a
thousands separator.

Do **not** use it for data that is already curated and documented, such as a table this pipeline
produced earlier with its profile note still valid. Do not use it for streaming or event data
that never lands as a file; the ordering holds but the persistence advice does not. It does not
own coverage claims: what was read, sampled or skipped belongs to the
`honest-data-limits-disclosure` skill. It does not own the wording of a finding, which belongs
to the `insight-narrative-integrity` skill.

## Core Process

### Step 1: Profile before touching anything

Write `docs/data/profile.md` before a single value is changed. Without that file there is
nothing to clean against, and "I looked at it" is not a profile. Record, per column:

- **Name, inferred type, and the type it should be.** These differ more often than not.
- **Null count and null spelling.** Empty string, `NA`, `N/A`, `-`, `null`, `0` and a single
  space are different things and none of them is automatically missing.
- **Distinct count**, plus the full value list when it is small enough to read.
- **Minimum, maximum and a few real examples**, copied verbatim, including the quotes and the
  whitespace.

Then answer these about the file as a whole, because each one silently changes every number
that follows:

| Trap | How to detect it | What it does if missed |
| --- | --- | --- |
| Ambiguous dates | Any first component above 12 proves day-first; if none exists, the order is genuinely undecidable from the data | Days and months swap for the first twelve days of every month |
| Serial dates | A date column arriving as integers around 40000–50000 | Dates become meaningless integers, or shift by a day |
| Decimal comma | Values like `1.234,56`, or a "number" column parsed as text | Values inflate or collapse by three orders of magnitude |
| Lost leading zeros | Identifier-like columns whose values differ in length | Codes silently merge; joins produce wrong matches |
| Encoding and byte-order mark | Mojibake in the first column name, or three unexpected bytes before it | The first column cannot be addressed by name |
| Header not on row 1 | A title row, a blank row, then the real header | Every column is named after a data value |
| Total and subtotal rows | A row whose label is "Total" or is blank across dimensions | Aggregates are counted twice |
| Merged cells | Repeated values appearing only on the first row of a group | Groups lose all rows but their first |

State the decision you made for each ambiguity, and state it as a decision. "Dates are day-first
because 23/04/2025 appears in row 118" is a profile entry. "Dates parsed fine" is not.

### Step 2: Clean, one recorded rule at a time

Every change is a rule with a reason, appended to `docs/data/cleaning-log.md`: what it matched,
what it did, how many rows it touched. A cleaning step whose row count you cannot state is a
step you cannot defend.

- **Fix types explicitly.** Read identifier-like columns as text from the start rather than
  repairing them afterwards; a leading zero removed on read cannot be recovered, because
  nothing records how many digits were there.
- **Parse dates with the format you proved**, not with an inference that may switch per row.
- **Normalize the null spellings** you found, and say which ones you treated as missing.
- **Remove aggregate rows** and record how many, because their absence changes every total.
- **Deduplicate on a stated key**, and report how many rows collapsed. If the key was not
  obvious, that uncertainty belongs in the log.
- **Never edit the source file.** Write to `data/clean/`, leaving `data/raw/` untouched. When
  the source is a spreadsheet, opening and re-saving it destroys more than it changes.

Ambiguity is recorded, not resolved by preference. If a column cannot be interpreted with
confidence, the log says so and the chart says so.

### Step 3: Model the grain

Decide what one row means, and write it in `docs/data/model.md` as a sentence: "one row is one
order line per day per store". Everything downstream depends on that sentence being true.

- Name the key that makes a row unique, and verify it: duplicates on the key mean the grain is
  not what you wrote.
- Keep the columns the questions need. Dropping the rest is a decision worth recording, not a
  cleanup to hide.
- Where an aggregate is stored, store the components too: a sum and its count, not a mean.
  A mean cannot be re-aggregated correctly later, which is the failure the
  `insight-narrative-integrity` skill exists to catch.

### Step 4: Persist to columnar storage

Write the modelled table to `data/curated/` as Parquet before any query or chart runs.

This is not a performance preference. A CSV carries no types, so every consumer re-guesses them
and each guess can differ; Parquet stores the schema in the file, which is what stops Step 1
from having to happen again. It also holds column statistics that let a reader skip data it does
not need.

- Partition by the column that queries filter on, usually a date, only when the data is large
  enough that skipping matters. Partitioning a small table just creates many small files.
- Treat the written file as the input to everything after it. Re-cleaning per question is how
  two charts in one report end up disagreeing.
- Adding data means writing another file into the directory. Parquet files are not edited in
  place; if the task needs updates, deletes or concurrent writers, that is a different problem
  than a directory of files solves.

### Step 5: Only now, visualize

The chart reads from `data/curated/`. If a chart specification needs a value that is not in the
curated table, the answer is to go back to Step 3, not to patch the value into the chart.

State, next to the chart, which curated table it came from and the date it was built. A chart
whose provenance is unstated becomes a screenshot with no way back to the data.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "It's a quick chart, not a pipeline." | Quick charts are the ones that get pasted into decisions. The profile is the cheap part; being wrong in public is not. |
| "The data looks clean." | Looking clean is what unprofiled data does. Leading zeros, decimal commas and day-first dates all render as ordinary values. |
| "pandas figured out the types." | It guessed, per column, sometimes per chunk. A guess that is right on the sample and wrong on row 40,000 is worse than an error. |
| "Parquet is overkill for one file." | The cost is one line. The benefit is that the next reader inherits the types you proved instead of re-guessing them. |
| "I'll clean it later if something looks off." | Nothing will look off. Wrong numbers plot as smoothly as right ones. |
| "The user just wants the chart." | They want the chart to be true. Delivering the untrue one faster is not service. |
| "I already cleaned it in the notebook." | If the cleaning is not in `data/clean/` with a log, it exists once, in a session nobody can reproduce. |
| "The source file is the single source of truth, so I'll read it every time." | Then every consumer repeats every guess. The curated table is the single source of truth precisely because the guessing already happened once, on the record. |

## Red Flags

Stop and return to Step 1 when you notice any of these:

- A plotting call appears in the work and `docs/data/profile.md` does not exist.
- A date column was parsed without any statement of which order was proved.
- An identifier column is stored as an integer.
- A total in the output matches a total in the source exactly, including a row labelled "Total".
- The cleaning log says what was done but not how many rows it touched.
- Two outputs from the same source disagree, which means cleaning happened twice, differently.
- The source file's modification time changed during the work.
- A chart is being built from a path under `data/raw/`.

## Verification

- [ ] `docs/data/profile.md` exists, lists every column with its inferred and intended type, and
      names a decision for each ambiguity in the Step 1 table.
- [ ] `docs/data/cleaning-log.md` records every rule with the number of rows it changed.
- [ ] `data/raw/` is byte-identical to what arrived; the source file was never written to.
- [ ] `docs/data/model.md` states in one sentence what a single row means, and the stated key is
      verified unique.
- [ ] A Parquet table exists under `data/curated/` and reading it back yields the intended types.
- [ ] Every chart names the curated table it was built from.
- [ ] Any ambiguity that could not be resolved appears in the output, not only in the log.
