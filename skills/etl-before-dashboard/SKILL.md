---
name: etl-before-dashboard
description: Enforces the profile, clean, model and persist order before anything is charted, so a visualization never renders raw ingest. Use when a request asks to chart, plot, dashboard or summarize a CSV, spreadsheet, export or extract, when a bar chart or a monthly total is being built straight from a source file, or when values arrive as text, with mixed date formats, comma decimals or lost leading zeros.
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
| Serial dates | A date column arriving as integers around 40000–50000 | Dates become meaningless integers; the common epoch also counts a day that never existed, so two serials can land on one date |
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

- **Pick the thing that holds the table before writing a line of cleaning.** This whole skill
  exists because types get guessed and the guess is not recorded, so the tool that holds the
  table has to be one that declares a schema rather than inferring a fresh one per column and
  sometimes per chunk. Anything expressible as a query belongs in SQL against the persisted
  table, which is the `duckdb-for-local-analytics` skill. For the row work that is not a query,
  the default is Polars, because its schema is explicit and stable rather than re-derived from
  the data it happens to have seen.

  The exception is the one that matters in practice: **if the project already uses a dataframe
  library, use that one.** A second one is a second set of type rules over the same table, and
  two libraries disagreeing about a column is the failure this step exists to prevent. Where the
  existing library infers types, pin them at read time and record the pinned schema in the log,
  which buys back the property the default would have given for free.
- **Fix types explicitly.** Read identifier-like columns as text from the start rather than
  repairing them afterwards; a leading zero removed on read cannot be recovered, because
  nothing records how many digits were there.
- **Parse dates with the format you proved**, not with an inference that may switch per row.
- **Normalize the null spellings** you found, and say which ones you treated as missing.
- **Remove aggregate rows** and record how many, because their absence changes every total.
- **Deduplicate on a stated key**, and report how many rows collapsed. If the key was not
  obvious, that uncertainty belongs in the log.
- **Never edit the source file.** Write to `data/clean/`, leaving `data/raw/` untouched.
  Round-tripping a workbook through a library is not lossless: the cached results of formulas
  are dropped every time, and drawings, embedded images, macros and rich text may be too,
  depending on the library and which of its optional dependencies are installed. If a workbook
  really must be changed in place, list what the round trip drops and prove it by reading the
  result back.

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

This is not a performance preference. A delimited text file defines no types, so every consumer
infers them again and the inferences can differ. Parquet stores its schema, including the type
of every column, in the file footer, which is what stops Step 1 from having to happen twice.
What comes back is the type recorded in the file, so record the types you proved rather than
assuming a particular engine's native type survives untouched.

- Partition by the column that queries filter on, usually a date, only when the data is large
  enough that skipping matters. Partitioning a small table just creates many small files.
- Treat the written file as the input to everything after it. Re-cleaning per question is how
  two charts in one report end up disagreeing.
- A file can also carry per-column statistics that let a reader skip data which cannot match a
  filter. They are optional, so treat them as an optimization that may be present, never as a
  guarantee that a scan was avoided.
- Adding data means writing another file into the directory. The footer is written after the
  data and closes the file, and the format defines no append operation, so a finished file is
  not extended. Row-level updates and deletes are therefore not an operation this layer has:
  they come from a table format layered on top, which keeps data files immutable and changes
  metadata instead. If the task needs them, or needs concurrent writers, say so rather than
  simulating it with a directory of files.

### Step 5: Only now, visualize

The chart reads from `data/curated/`. If a chart specification needs a value that is not in the
curated table, the answer is to go back to Step 3, not to patch the value into the chart.

State, next to the chart, which curated table it came from and the date it was built. A chart
whose provenance is unstated becomes a screenshot with no way back to the data.

> The shared reference `references/format-strategy.md` puts every format this pack meets side by side, with what reads it and what bites. It is the view to take when a source arrives in a format you have not handled before. A per-skill install does not carry it; without it you lose the comparison, not the formats this skill needs, which are above.

### Step 6: Check the delivered file, not the notes about it

Every step above leaves a document behind, and a document is easy to write correctly about work
that went wrong. This step is the only one that reads what the reader actually receives, and it
is not optional: a run that stops at Step 5 has verified its own paperwork.

First declare the numbers. Write `docs/data/figures.json` naming every figure the output
publishes, with the value printed, the population it covers, and the query over the curated
table that produces it:

```json
{
  "table": "data/curated/orders.parquet",
  "figures": [
    {
      "label": "Revenue",
      "value": 7316.65,
      "population": "delivered orders only; 37 cancelled orders excluded",
      "sql": "SELECT SUM(total) FROM t WHERE status = 'delivered'"
    }
  ],
  "constants": [
    {"value": 5, "label": "product categories", "source": "docs/data/profile.md"}
  ]
}
```

`population` is the load-bearing field. A total that silently includes rows the reader would
have excluded is not a rounding difference, it is a different number, and the place it has to be
corrected is the page rather than the log.

Then run the check and read what it says:

```
bash scripts/verify-output.sh --manifest docs/data/figures.json \
  --html <the file that ships> --docs docs/data --project .
```

It runs the declared queries with DuckDB, which usually lives in the project's environment rather
than on `PATH`; name that interpreter with `VERIFY_OUTPUT_PYTHON` when it does. A missing engine is
reported as an error rather than passed over, because a check that quietly did not run is the
thing this step exists to replace.

It fails when a declared figure is not what the table answers, when a number appears in the
page's own text that no figure and no declared constant produces, when a figure's population is
missing or never appears on the page, when the delivered page is more than one HTML document,
when a summary row is still being carried as data, when the project declares a second charting or
dataframe library and nothing says what distinguishes it from the first, or when a delivered note
does not decode as UTF-8.

None of those are hypothetical. Every one was found in a delivered artefact whose run had
recorded a complete profile, a cleaning log and a model note, and had ticked every box in this
skill before this step existed.

A failure here is never fixed by editing the delivered file. The number came from somewhere;
go back to the step that produced it. Patching the page leaves the pipeline still producing the
wrong value, and the next run publishes it again.

A run with zero errors writes `docs/data/verification.json`, naming what it read and the digest of
each one; a run with any errors deletes it. That receipt is the evidence, not the claim: pasting
the output into an answer says the check passed, and the receipt is what something else can look
at. Never write it by hand, and never edit a checked file afterwards without running the check
again — the receipt then describes bytes that no longer exist, which is the state it is designed
to expose.

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
| "I opened the output and it looked fine." | Looking fine is what a page does when its headline counts rows it should have excluded. The check compares the printed number to what the table answers; an eye compares it to nothing. |
| "The numbers are in the chart library's own output, so they must be right." | They are right about the array they were handed. Whether that array came from the curated table, or from a value typed into the template, is the thing that goes unchecked. |
| "It is the dataframe library I always reach for." | Then it was chosen by habit before the data was seen, which is the same move as picking a chart library by familiarity. Use the one the project already has, or the one whose schema is declared. Reaching is not deciding. |
| "That figure came from the profile, so it is already verified." | A profile is a document this run wrote. Numbers in it have been copied from the wrong summary before; the query is what makes one verified. |
| "Fixing it by hand is faster than re-running the pipeline." | It is, once. Then the pipeline still produces the wrong value, the hand fix is not in the log, and the next run publishes the original number with nothing to show it was ever wrong. |

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
- A row was removed, a type corrected or a value patched anywhere other than inside the cleaning
  script. A fix applied by hand is a fix the next run does not have.
- A distinct count in the profile equals the row count exactly. That is what a non-null count
  looks like when it has been filed under the wrong heading.
- A number appears in the output that no query produced.
- A dataframe library is imported that the project did not already depend on, and no line says
  why the table needed a second set of type rules.

## Verification

- [ ] `docs/data/profile.md` exists, lists every column with its inferred and intended type, and
      names a decision for each ambiguity in the Step 1 table.
- [ ] Every count in the profile was measured, not inferred from the row count, and distinct
      counts were computed as distinct counts.
- [ ] `docs/data/cleaning-log.md` records every rule with the number of rows it changed.
- [ ] `data/raw/` is byte-identical to what arrived; the source file was never written to.
- [ ] `docs/data/model.md` states in one sentence what a single row means, and the stated key is
      verified unique. The sentence and the key agree: a key that is unique per order contradicts
      a sentence that says the row is a line item, and one of the two is wrong.
- [ ] Everything under `data/clean/` and `data/curated/` was produced by re-running the recorded
      script end to end, with no step applied by hand afterwards.
- [ ] A Parquet table exists under `data/curated/` and reading it back yields the intended types.
- [ ] Every chart names the curated table it was built from.
- [ ] `docs/data/figures.json` accounts for every number the output publishes, each with the
      population it covers and the query that produces it.
- [ ] No library was added that does a job something already in the project does. Where two of a
      kind exist, what distinguishes them is written down, not implied by the import list.
- [ ] `scripts/verify-output.sh` was run against the file that ships, and its output is quoted in
      the answer showing zero errors. Not run, or run and not read, is the same as not checked.
- [ ] `docs/data/verification.json` exists, was written by that run rather than by hand, and is
      newer than every file it names.
- [ ] Any ambiguity that could not be resolved appears in the output, not only in the log.
