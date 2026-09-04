---
name: parquet-to-open-table-format
description: Decides when a directory of Parquet files has stopped being enough to hold a dataset, by naming what that layer cannot do: correct a row, survive two writers, keep a column somebody added, or give a reader the same answer twice. Use when files are being rewritten to fix rows, when more than one process writes the same dataset, when a column was added and the older files do not have it, or when a reader needs the data as it stood at a point in time.
---

# Parquet to an open table format

## Overview

A directory of Parquet files is an excellent table right up to the point where it is not one. It
holds its own schema, returns the types that were written, and is read by everything. What it has
no answer for is change: correcting a row, adding a column, two processes writing at once, or
telling a reader what the dataset looked like an hour ago.

The word "lakehouse" is exactly this distinction. The data files stay as they are; a metadata
layer on top makes them behave like a table.

```
data/curated/*.parquet          data/curated/  +  a metadata layer
   files are the table            files are still the files
   change means rewriting         change means a new snapshot
```

## When to Use

Use this skill when the storage layer, not the query, has become the problem: a row needs
correcting, a delete has to be applied, a second writer appeared, a column was added, or two
readers of the same directory disagree.

Do **not** reach for it because a dataset is large. Size alone is what Parquet already handles.
Writing and reading the files themselves belongs to the `etl-before-dashboard` skill, and asking
questions of them belongs to the `duckdb-for-local-analytics` skill. A monthly extract that is
written once and read many times needs none of this, and adding a catalogue to it buys nothing
but the catalogue.

## Core Process

### Step 1: Know exactly what the file layer already gives you

Verified rather than assumed, because the guarantees are narrower than their reputation:

- **The schema and the types come back as they were written.** A 32-bit integer read back is a
  32-bit integer. This is the property that stops every consumer re-guessing.
- **Per-column statistics are optional.** They are usually written, and they can be switched off
  at write time, in which case the file has none. Treat them as an optimisation that may let a
  reader skip data, never as evidence that a scan was avoided.
- **A finished file is not extended.** The footer is written after the data and closes the file,
  so adding data means adding another file, never appending to one.

### Step 2: Understand how the directory decides its schema, because it is not by agreement

This is the failure that costs data, and it is silent.

When a reader opens a directory of Parquet files, it takes the schema from the first file it
inspects, which is the first in name order. If a later file has a column the first one does not,
**that column is dropped from the result without an error, a warning, or a null**. If the new
column happens to be in the first file instead, it is kept and the older rows come back null.

So whether a column added last month survives a read depends on the name the writer gave the
file. `part-0.parquet` and `part-1.parquet` behave differently from each other for no reason
anybody chose.

A reader can unify the schemas across every file, and then the column appears with nulls where it
was absent. That works, and it means opening every footer in the directory on every read. Doing
that once and recording the answer is precisely what a metadata layer is.

### Step 3: Name what the directory layer cannot do

Before proposing anything, say which of these the task actually needs. Each one is a reason to
move; none of them is "the data got big".

| What is needed | Why a directory cannot do it |
| --- | --- |
| Correct or delete individual rows | The files are immutable, so a correction means rewriting whichever file held the row, and any reader mid-scan sees a directory that changed underneath it. |
| Two writers at once | Nothing coordinates them. Two processes adding files can interleave, and a reader can see half of each. |
| A column added and kept | Step 2. It survives or vanishes according to file names. |
| The same answer twice | A read is over whatever files exist at that instant. A write during a long read changes the result. |
| The data as it stood earlier | Nothing records what the set of files used to be. |
| One place that knows the tables | A directory path is not a catalogue; every consumer hardcodes a path and finds out about a move by breaking. |

### Step 4: What the move actually changes, and what it costs

A table format keeps the data files exactly as they are and adds metadata that lists which files
belong to the table right now, with the schema each of them carries. A change becomes a new
snapshot of that list rather than an edit to a file, which is what makes an update, a delete, a
concurrent write and a consistent read possible at all.

The costs are real and belong in the proposal:

- **A reader needs support for the format.** In a local query engine that support arrives as an
  extension, and it is **not installed by default**: it is fetched over the network on first use.
  On an offline or audited machine that is a blocker, not a detail.
- **Small files still accumulate**, and now they accumulate in a manifest too. Compaction is a
  job somebody has to run, not a property that comes for free.
- **Partitioning is a decision, not a default.** Partition by what queries filter on, usually a
  date, and only when the data is large enough that skipping matters. Partitioning a small table
  produces many small files and a slower table.

### Step 5: Say what to do when the answer is "not yet"

Most datasets do not need this, and saying so is the useful answer. When the trigger list in Step
3 has nothing checked, keep the directory and fix the cheap things instead:

- Give files names that sort in write order, so the first file read is the oldest schema and a
  new column is at least consistently absent rather than randomly.
- Unify schemas explicitly on read, and say that the read does so.
- Write a schema note next to the data recording every column ever added and when.

State which of these was done, and what would change the answer to "yes".

> The shared reference `references/capacity-thresholds.md` collects every hard limit in this pack side by side, with the tool each one was verified against. It is useful when choosing between approaches rather than following one. A per-skill install does not carry it; without it you lose the comparison, not any limit this skill needs, because each one is stated above.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "The dataset is big, so it needs a table format." | Size is what Parquet is already good at. Change is what it is not. |
| "We only append, so we never need updates." | Until a row arrives wrong. "We only append" is a description of the past. |
| "The new column is there, I checked." | You checked a read where it survived. Whether it survives depends on which file the reader looked at first. |
| "Two writers is fine, they write different files." | Different files, one directory, no coordination and no snapshot. A reader between the two writes sees a table that never existed. |
| "A table format is just Parquet with extra steps." | It is Parquet plus a record of which files are the table. That record is the entire difference between a folder and a table. |
| "We can add the metadata layer later if we need it." | True, and that is the right default. Say it out loud so the decision is a decision. |
| "Compaction can wait." | It can, and the manifest grows while it waits. Name who runs it before proposing the move. |

## Red Flags

Stop when any of these is true:

- A Parquet file is being rewritten in place to correct a row.
- A column was added to new files and nobody has checked whether a read still returns it.
- Two processes write into the same directory and neither knows about the other.
- A long read runs while a writer is adding files to the same path.
- A table format is being proposed and no item in the Step 3 list applies.
- Partitioning is being added to a dataset small enough to read whole.
- The proposal does not say who compacts the small files.

## Verification

- [ ] The reason for the move is one of the needs in Step 3, named explicitly, not the size of
      the data.
- [ ] Whether a read still returns every column was checked against the actual files, not
      assumed from the fact that a writer added it.
- [ ] The proposal names the reader support required and whether it is already present on the
      machine, given that it is fetched over the network on first use.
- [ ] Partitioning, if proposed, names the column queries filter on and why the data is large
      enough for skipping to matter.
- [ ] If the answer is that the directory is still enough, that is stated along with what would
      change it.
