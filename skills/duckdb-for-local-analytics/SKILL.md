---
name: duckdb-for-local-analytics
description: Answers an analytical question with SQL over the Parquet or delimited tables that were already persisted, instead of another pass of row-by-row code over the source. Use when a question asks for revenue, counts or averages per group, a ranking of segments or channels, or one period compared with the period before it, when an analysis is being written as iteration over rows, when a file is larger than the memory available to load it, or when the same source is re-read and re-cleaned for every new question.
---

# DuckDB for local analytics

## Overview

Most analytical questions are the same four operations: filter some rows, join them to something
else, group them, and rank the result. A query engine is built to do exactly that, over data it
does not have to hold in memory all at once, and it will say what it plans to do before it does
it.

Writing the same thing as iteration over rows produces code that is longer, slower, harder to
check, and silently wrong in the ordinary cases: a row that was skipped, a group that had no
rows, a division whose denominator was zero for one department only.

```
data/curated/*.parquet ──► SQL ──► the answer
        ▲                    │
        │                    └── the plan says what it will read, before it reads it
   already profiled and cleaned
```

## When to Use

Use this skill when a question is asked of a table: totals per group, a comparison between
periods, a ranking, a join between two sources, a filtered count.

Use it when a file will not fit in memory, when the same source is being loaded again for each
new question, or when an analysis is taking shape as nested loops accumulating into a dictionary.

Do **not** use it to decide what the values mean or how they were cleaned; profiling, cleaning
and persisting belong to the `etl-before-dashboard` skill and happen before a query is worth
writing. Querying a database other people depend on belongs to the `safe-live-database-access`
skill. Whether a directory of files still suffices as the storage layer belongs to the
`parquet-to-open-table-format` skill.

## Core Process

### Step 1: Query the persisted table, not the source

The query reads from `data/curated/`. If there is nothing there, the answer is not to query the
raw file faster; it is that the profile, the cleaning and the persist step have not happened yet.

Re-reading a source per question means re-inferring its types per question, and two answers in
one report can then disagree without either being a bug in the query.

### Step 2: State the grain before writing the SQL

Say what one row of the result means before writing the query that produces it: "one row per
channel per month". A query whose grain nobody stated is a query whose duplicates nobody will
notice, because a join that fans out looks exactly like a business that grew.

Then translate the question directly: the filter is the `WHERE`, the "per" is the `GROUP BY`, the
"top" is an `ORDER BY` with a `LIMIT`, and "compared to" is a join or a window, not a second
query whose result is pasted next to the first.

When the request arrives with a deadline, or with "it is only a few rows, do not overthink it",
keep the checks and say what they cost. Counting the rows on both sides of a join is one more
query and it runs in the time it takes to read this sentence; it is also the whole difference
between a ranking and a wrong ranking. Speed is a reason to drop work that is slow, and these
checks are not. Say that in one line rather than either arguing about the deadline or quietly
dropping the check to meet it.

### Step 3: Read the plan before claiming anything about speed

The engine will describe what it intends to do. Read it and say what it showed, rather than
asserting that a query is efficient because it is written in SQL.

- Ask for the plan before running anything that might be expensive, and for the plan with
  measurements after, when the cost actually matters.
- What matters in the plan is what it reads: the number of files touched, whether a filter was
  pushed down into the scan, and whether a join is the shape you expected.
- "It ran quickly on this machine" is a measurement of this machine, not of the query.

### Step 4: Know what the engine reads on its own, and what it fetches first

Reading delimited text, Parquet and JSON needs nothing extra. Other sources are extensions, and
the engine will **install them over the network on first use, without asking**, leaving them
under the user's home directory. Spreadsheets, object storage over HTTP and the open table
formats all fall on that side.

That is a change to the machine, made by a query. On a machine that is offline, audited, or
subject to a policy about what it downloads, name the extensions the work needs before the first
statement runs rather than discovering them in a stack trace.

The engine itself may not be installed either. That is a fact to state, not to route around:
quietly switching to a different tool and presenting the result as though the plan had been
followed hides the substitution from the only person who could object to it. Bring the engine in
through the project's own package manager, or run it in a throwaway environment that leaves the
shared interpreter untouched. Installing into a system-wide interpreter to answer one question
is a change to somebody's machine that outlives the question.

### Step 5: The data does not have to be in a file

An in-memory table is queryable directly: a data frame in the running process can be named in the
`FROM` clause by its variable name and joined against a real table in the same statement. Nothing
has to be written out first.

This is what makes the rest of the pack independent of where data came from. Rows handed over by
a connector, an API response already parsed, a frame built in the session: all of them reach SQL
without a detour through a file, and the discipline that applies afterwards is unchanged.

### Step 6: Persist an answer that will be asked again

A result that another step depends on is written back to `data/curated/` as a table of its own,
with the grain stated. Recomputing it per consumer is how two charts of the same thing end up
disagreeing.

A result nobody will reuse does not need to be stored. Say which of the two it is rather than
storing everything or nothing.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "The data frame library can do this too." | It can. It also holds the whole table in memory, re-infers the types, and gives no plan to read. The question is not which can, but which one you can check. |
| "It is only a hundred thousand rows." | Then the query costs nothing and the loop costs nothing, and the query is still the one whose grain and filters are legible six months later. |
| "SQL is harder to read than the loop." | The loop is easier to read and harder to verify. A `GROUP BY` cannot silently skip a row the way a `continue` inside a loop can. |
| "I will load the file and work in memory." | Then the file size, not the question, decides whether the analysis is possible at all. |
| "Looking at the plan is premature optimisation." | It is not optimisation, it is reading. The plan is how you find out that the filter was not pushed down and the query read every file. |
| "I re-read the source each time so I know it is fresh." | You know it is re-guessed. Freshness is a property of the pipeline that wrote the curated table, not of reading a CSV again. |
| "The extension installed itself, so it must be fine." | It installed itself over the network onto this machine. Fine or not, it happened and it was not stated. |

## Red Flags

Stop when any of these is true:

- A loop is accumulating an aggregate that a `GROUP BY` would produce.
- The query reads from `data/raw/` or from the original download path.
- A claim about performance is being made and no plan was read.
- The same source file is loaded in more than one place in the work.
- A join was added and the row count of the result was never compared to the row count before it.
- An extension was installed during the work and the answer does not mention it.
- The result is being pasted between queries by hand instead of joined.

## Verification

- [ ] Every query reads from a persisted table under `data/curated/`, not from a source file.
- [ ] The grain of each result is stated, and a join that could fan out was checked against the
      row count before it.
- [ ] Any claim about cost or speed quotes the engine's own plan, not an impression.
- [ ] Any extension the engine installed to run the work is named in the answer.
- [ ] A result other steps depend on is persisted with its grain recorded; one that is not
      reused is explicitly left unstored.
