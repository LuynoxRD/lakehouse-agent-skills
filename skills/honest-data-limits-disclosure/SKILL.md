---
name: honest-data-limits-disclosure
description: Declares what a data run did not cover before and after the work: memory ceilings, sampled rows, unread sheets, skipped files and hard format limits. Use when a file may be too large to read whole, when only part of a batch or a workbook was processed, when a row cap or a sample was applied, or when reporting results that came from less data than the request implied.
---

# Honest data limits disclosure

## Overview

The dangerous answer is not the one that fails. It is the one that succeeds on part of the data
and reports as though it covered all of it. "I processed the sales file" after reading one sheet
of twelve, "the average order is 47" after reading the first thousand rows, "all 200 files are
in the report" when 14 threw an error that was swallowed: each of these is a true sentence about
work that was done and a false impression about what it covers.

This skill has two halves. Before the work, decide what will fit and say so. After the work,
state what was left out. Neither half is optional, and the second cannot be skipped because the
first went well.

## When to Use

Use this skill before reading any file whose size is unknown or larger than a few megabytes,
before processing a batch of files, and before reading a spreadsheet with more than one sheet.

Use it after any run where a limit was hit: a row cap, a sample, a timeout, a file that failed,
a sheet that was skipped, a column that was dropped for size.

Use it whenever a result is about to be reported and the coverage is not obviously total.

Do **not** use it as a substitute for doing the work. Disclosure explains a real limit; it does
not license reading less because reading less is easier. Do not use it to hedge a complete run:
padding a full result with caveats is its own dishonesty. It does not own how values were
cleaned, which belongs to the `etl-before-dashboard` skill, nor the arithmetic of a claim, which
belongs to the `insight-narrative-integrity` skill.

## Core Process

### Step 1: Pre-flight, before opening the file

Answer these before reading, not after something fails.

**How big is it, against what is available?** Compare the file size to available memory, not to
total memory. A columnar or compressed file expands when loaded, often several times over;
a delimited text file loaded into a dataframe typically occupies more memory than its bytes on
disk, because every value becomes a typed object. If the file is a large fraction of what is
free, decide now between streaming it, reading selected columns, or processing it in chunks.

**What are the format's hard ceilings?** They are absolute, and content beyond them does not
exist in the file:

| Limit | Value | Consequence |
| --- | --- | --- |
| Rows in one spreadsheet worksheet | 1,048,576 | Rows past it were never saved |
| Columns in one spreadsheet worksheet | 16,384 | Columns past it were never saved |

If a source was ever converted through a spreadsheet, treat a row count at exactly the ceiling
as evidence of truncation upstream, not as a coincidence, and say so.

**How many sheets, and what is on them?** Enumerate every sheet by name before reading any.
A workbook is not a table. Two more traps live here:

- **Several tables on one sheet.** A blank row and a new header row partway down means two
  tables. Reading the sheet as one rectangle silently concatenates them.
- **The sheet you were given is not the sheet with the data.** A summary tab is often first.

**How many files, and which ones?** For a batch, count them first, then track the outcome of
each one. A loop that catches exceptions and continues will finish quietly having done less
than it claims.

**What is your own reading budget?** An agent's context is a real limit, no different from
memory. Reading a large file into the conversation truncates it, and the truncation is silent
from the reader's point of view. Decide up front to compute over the file rather than to read
it, and state that decision. Never let a limit degrade the answer without naming it.

### Step 2: Choose a strategy and name it

There are four honest strategies. Pick one deliberately and record which:

1. **Whole**: the data fits, everything is read. The only strategy that supports an unqualified
   population claim.
2. **Streamed or chunked**: everything is read, never all at once. Also supports a full claim,
   as long as every chunk was actually processed.
3. **Column subset**: all rows, some columns. Claims about the read columns are full; the
   dropped columns do not exist for this run.
4. **Sample**: some rows. Every claim from it is an estimate about the sample, and turning it
   into a population claim requires the sample to be random, which a head of a file is not.

The fifth option, reading the first N rows and reporting as though it were all, is not on the
list. That is the behaviour this skill exists to prevent.

### Step 3: Do not loop over rows

A per-row loop over a large table is the pattern that turns a two-second job into one that gets
abandoned halfway and reported as partial. Express the work as a set operation over the whole
table: an aggregation, a join, a vectorized transformation, or a SQL query against the file.
This matters here rather than being a performance aside, because the abandoned loop is the most
common cause of an undisclosed partial result.

### Step 4: Write the disclosure

Write `docs/data/disclosure.md` and put the load-bearing parts of it into the answer itself.
A disclosure that lives only in a file nobody opens has not disclosed anything.

State, in numbers:

- **Rows read, of how many.** If the total is unknown, say that it is unknown rather than
  omitting it.
- **Sheets read, of how many**, by name.
- **Files processed, of how many**, and the name and reason for each one that failed.
- **Columns used**, when a subset was read.
- **The strategy** from Step 2, in one word, and why it was chosen.
- **Every filter that removed data**, including the ones that felt like cleaning.
- **What could not be determined**, such as an ambiguity that stayed unresolved.

Numbers, not adjectives. "Some rows were skipped" is not a disclosure; "1,412 of 48,900 rows had
an unparseable date and were excluded" is.

### Step 5: Match the claim to the coverage

Before the answer goes out, check every sentence in it against the coverage:

- A statistic from a sample is described as an estimate from that sample, with its size.
- A superlative ("the highest", "the best month") is only made when every candidate was
  examined. If only part of the data was read, the honest form is "the highest among the rows
  read".
- No statement of confidence is made without the evidence for it. "The data is clean" requires
  the checks that established it, not the absence of an error.
- A total is described as a total only when nothing was dropped between the source and it.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "The first 1,000 rows are representative." | The first rows are ordered by whatever the export was sorted by, usually time or id. That is a systematic slice, not a sample. |
| "It's obvious I couldn't read the whole thing." | It is obvious to you. The reader sees a number with no qualifier and treats it as the answer. |
| "The other sheets are just notes." | Then say that, having looked. Sheets named "Sheet3" have held the actual data often enough that assuming is not free. |
| "Mentioning the limit undermines the result." | An unstated limit does not disappear; it waits to be discovered by someone who then distrusts everything else you produced. |
| "The errors were only a few files." | Name the number and the files. "A few" is the word that hides fourteen. |
| "I'll note it if they ask." | They will not ask, because nothing in the answer suggests there is something to ask about. |
| "The truncation warning was harmless." | A truncation warning is the file telling you the data you are about to report on is not all there. |
| "Adding caveats to everything is noise." | Disclose what was actually limited. A complete run gets a one-line statement that it was complete; that is not noise, it is the difference between the two. |

## Red Flags

Any of these means the disclosure is missing or wrong:

- A row cap appears in the code and no number appears in the answer: `nrows=`, `head(`,
  `LIMIT`, `.take(`, `sample(`, a break inside a read loop.
- The phrase "the file" or "the data" in an answer, when a workbook with several sheets was
  opened.
- A batch job that reports success without a processed count.
- An exception handler around a read that continues without recording what failed.
- A row count that is exactly 1,048,576, or exactly the value of a limit set earlier.
- A superlative in the answer and a sample in the method.
- The word "all" anywhere in the answer, without a count next to it.
- A result that arrived suspiciously fast for the stated data size.

## Verification

- [ ] File size was compared against available memory before reading, and the strategy from
      Step 2 is named in `docs/data/disclosure.md`.
- [ ] Every sheet in every workbook is listed by name, marked read or not read.
- [ ] For a batch, processed and failed counts sum to the total number of input files, and each
      failure is named with its reason.
- [ ] Rows read and total rows both appear as numbers, or the total is explicitly stated as
      unknown.
- [ ] No claim in the answer is broader than the coverage: no unqualified superlative or total
      from partial data.
- [ ] The limits that shaped the result appear in the answer itself, not only in the file.
- [ ] If the run was complete, the answer says so in one line, with the counts that prove it.
