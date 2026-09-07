---
name: using-lakehouse-skills
description: Routes a data request to the skill that owns it and states the order the stages have to run in. Use when starting work on a dataset and it is not obvious which skill applies, when a request jumps straight to a chart or a conclusion, when work spans more than one stage of the data lifecycle, or when a request names an action rather than a stage and what the work will write has to decide which stages are in play.
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

## How much runs is decided by what is at stake, not by how big the data is

The stages below are cheap. What is not cheap is the machinery built around them: a reviewer
persona opening a dozen artefacts, a full disclosure with its counts, a second pass over the
arithmetic. That machinery earns its cost on a result somebody acts on, and it is pure waste on a
look taken to decide whether the work is worth continuing at all.

Two questions about the request settle it, answered before the work starts:

1. **Does the result leave the project?** A file sent, a page shared, a figure pasted into a
   message or a document somebody else reads.
2. **Will somebody act on it?** A decision, a price, a message to a customer, a change to a
   system that is running.

**Either one is yes:** the reviewer personas run, the disclosure is complete with its counts, and
every published figure is recomputed against the table it came from.

**Both are no:** the personas do not run and the disclosure is a paragraph rather than a document.
A paragraph still carries its counts — what shrinks is the writing, never the numbers, and a
short disclosure made of adjectives is the one thing the `honest-data-limits-disclosure` skill
refuses outright. The answer then says which of the two was skipped, because a first look is one
forwarded message away from being the thing that ships, and whoever forwards it has to be able to
see that nobody reviewed it.

**"No" is a claim, and it is the one to doubt.** It is the answer that removes the most work,
which is exactly why it cannot be asserted. Quote the words in the request that support it —
"just checking whether this is worth digging into", "before I take it to the team" — and put them
next to the decision, in the answer. A "no" with nothing quoted is a budget decision wearing the
clothes of a scope decision, and the run that produced this rule was a run under exactly that
pressure.

**When the request says neither, the answer is yes.** The two errors are not the same size.
Reviewing something that turned out not to matter costs a few minutes of reading. Not reviewing
something that did is the failure this whole pack exists to prevent, and it is discovered by the
person who acted on it. So the gate is deliberately not symmetric: silence resolves upward, and
only stated words resolve it down.

None of this skips a stage or applies a skill halfway. **The one rule above has no exceptions.**
What this gate decides is whether the reviewer personas run and how long the disclosure is —
never whether the file gets profiled, whether the cleaning gets logged, or whether the published
figures get recomputed. Those cost one pass each and they are not what made an audited run
expensive.

The gate is the stakes, never the size. A ten-row table that sets a price is the expensive case; a
million rows nobody will act on is the cheap one. Reading the request answers this in a sentence.
Measuring the file does not, and a threshold in rows would wave the expensive case straight
through.

What never scales down is the order. Profiling a file before charting it costs one pass over it,
and skipping it is what produces the confident wrong answer this pack exists to prevent.

## The language of what you hand back

**Everything a person reads takes that person's language, whole, and never mixed.** If they
wrote to you in Spanish, the profile note, the cleaning log, the model note, the disclosure, the
labels on the page and the answer itself are in Spanish. If they wrote in English, all of it is
in English. Chinese is Chinese. One delivery, one language.

**Identifiers are the exception, and they are never translated.** Column names, file paths,
table names, manifest keys, SQL and code stay exactly as they are, because they are literals
something else has to find. A column called `total_amount` is called `total_amount` in a Spanish
note; describing it in Spanish is the job, renaming it is a bug.

**How a number is written is part of the language.** The decimal separator, the thousands
separator and the date order follow the reader as well. This is the discipline the profile
applies on the way in, pointed the other way: handing `1,046.65` to somebody who reads
`1.046,65` moves the figure by three orders of magnitude in their head, which is the exact
failure `etl-before-dashboard` spends a whole table catching on arrival. The stored value never
changes — the curated table, the manifest and any exported file keep one canonical form, and
the formatting happens where the number is displayed. Where a figure could still be read two
ways, its unit goes next to it.

The reason to state this so plainly is that the opposite happens by inference. A repository whose
own files are in English is stating a rule about *its* files, not about what an agent writes to a
person, and reading it as the second produces exactly what one real run produced: `model.md` in
English and the dashboard in Spanish, in the same delivery, decided by nobody. If a skill's own
text is in one language and the reader writes in another, the reader wins.

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
| "Get the numbers out of this PDF", "here are photos of the receipts", "the columns came out mixed together" | `document-extraction-integrity` skill |
| "Is this even a table?", "the records don't all have the same fields", "find the themes in this text" | `structured-vs-unstructured-routing` skill |
| "Edit this workbook", "write the results back into the spreadsheet" | `spreadsheet-integrity` skill |
| "Connect to the database", "delete the test rows", "run this against production" | `safe-live-database-access` skill |
| "Paste these rows into the model", "send this to the API", "is there anything identifying in here?" | `data-privacy-before-llm` skill |
| "Revenue per channel", "the loop is too slow", "group and rank this" | `duckdb-for-local-analytics` skill |
| "Here is this month's file", "the export came again", "they sent a corrected version" | `etl-before-dashboard` skill, starting from its arrival comparison |
| "Re-run the pipeline", "regenerate the dashboard", "rebuild it with the script we already have" | `etl-before-dashboard` skill, starting from its existing-code step, then every skill that owns the form of what it wrote |
| "Join these two files", "match the orders to the customers", "add the region from this other table" | `etl-before-dashboard` skill for whether they relate, then `duckdb-for-local-analytics` skill to run it |
| "The new column isn't showing up", "two jobs write to the same folder", "we need to correct rows" | `parquet-to-open-table-format` skill |
| "Pie or bar?", "plot this over time", "what kind of chart?" | `chart-type-and-library-selection` skill |
| "Which colours?", "is red and green enough?", "does it work in dark mode?" | `dashboard-color-and-visual-hierarchy` skill |
| "This page is cluttered", "where does the big table go?", "what belongs on the first screen?" | `dashboard-layout-by-widget-mix` skill |
| "What are the key takeaways?", "which segment is winning?", "did it improve?" | `insight-narrative-integrity` skill |
| "Why did it go up?", "what caused this?" | `insight-narrative-integrity` skill |

When two apply, they compose in lifecycle order. A request to chart a very large export is
`honest-data-limits-disclosure` for the pre-flight, then `etl-before-dashboard` for the work,
then `honest-data-limits-disclosure` again for what the run left out.

## Artifact to skill

The table above keys on how a request sounds, and a request does not always sound like its stage.
"Re-run it", "just verify this", "small fix to the page", "refresh the numbers" each describe an
action taken on code or on time. None of them names a stage, and a router that only reads phrasing
finds nothing and concludes there is nothing to find. **What decides the stage is the artefact the
work will write or change; the verb the request used decides nothing.**

So there is a second lookup, and it is the one to use whenever the first comes back empty. It is
the lifecycle table read backwards, which is the direction routing actually needs, and it also
carries the skills that sit outside the stages.

| If the work will write or change | The stage is | Which means these apply |
| --- | --- | --- |
| A file landing in `data/raw/` | PROFILE | `etl-before-dashboard` skill, from its arrival step |
| Anything under `data/clean/` or `data/curated/` | CLEAN, MODEL | `etl-before-dashboard` skill |
| The storage layout itself: a new column, a second writer, rows to correct | — | `parquet-to-open-table-format` skill |
| A query, a group-by, a join that runs | QUERY | `duckdb-for-local-analytics` skill |
| A chart, a plot, a figure specification | VISUALIZE | `chart-type-and-library-selection` skill, then `dashboard-color-and-visual-hierarchy` skill |
| A page, a dashboard, a document somebody opens | ASSEMBLE | `dashboard-layout-by-widget-mix` skill, plus the two above for what it holds |
| A sentence stating a finding, a headline, a takeaway | NARRATE | `insight-narrative-integrity` skill |
| `docs/data/disclosure.md`, or an answer that says what was covered | DISCLOSE | `honest-data-limits-disclosure` skill |
| Rows leaving the project: a prompt, a request body, an attachment | REDACT | `data-privacy-before-llm` skill |
| A workbook written back to disk | crosses CLEAN | `spreadsheet-integrity` skill |
| A connection or a write to a system other people use | before PROFILE | `safe-live-database-access` skill |
| **A script that produces any of the above** | **the stage of its output** | **the skills of that stage, and the existing-code step of `etl-before-dashboard` skill** |

Read the rows against what the work will produce, never against what happens to exist already. An
artefact that is only read, and is neither changed nor handed to anybody, is not a stage; that is
the case the last section covers.

**Two things this table does not do.** It does not decide how much runs: that is the stakes gate
above, which sets whether the reviewer personas run and how long the disclosure is, and never
whether a stage happens. And it does not let a stage be satisfied by a check. A green artefact
check is evidence about the numbers it recomputed, and the skills in the third column above own
things the check states, in its own output, that it never read.

## How they divide the ground

These boundaries are what keep the skills from overlapping. Read them before deciding.

- **`etl-before-dashboard` skill** owns the *order of operations* and what happens to values on
  the way: types, locale, encoding, persistence. It does not own coverage claims.
- **`honest-data-limits-disclosure` skill** owns *coverage*: what was read, what was skipped,
  what could not fit, and how that gets stated. It does not own how a value was cleaned.
- **`insight-narrative-integrity` skill** owns *the arithmetic of a claim* and the words built
  on it. It assumes the data is already clean and its coverage already disclosed; it checks
  that the sentence follows from the numbers.
- **`document-extraction-integrity` skill** owns *getting data off a page*, which happens before
  the shape question can even be asked. A PDF, a scan or a photograph of a receipt is not text
  until something extracts it, and that extraction is lossy in ways only it counts.
- **`structured-vs-unstructured-routing` skill** owns the question of *what shape the source is*,
  and it runs before profiling. Once the answer is "a table", it hands over and stops.
- **`spreadsheet-integrity` skill** owns *what happens to a document* when a workbook is written.
  It does not own the values inside it.
- **`safe-live-database-access` skill** owns *the connection and the writes* to a system other
  people use. Once rows are in hand, it is finished.
- **`data-privacy-before-llm` skill** owns *what may leave the project*. It applies at any stage,
  because any stage can be the one that sends something.
- **`duckdb-for-local-analytics` skill** owns *asking a persisted table a question*, joins
  included. Whether two sources can be related at all — one key, the same thing on both sides,
  the cardinality, the rows that match nothing — is modelling and belongs to
  `etl-before-dashboard`. Running the join over a key nobody established is how a query
  returns a number instead of an error.
- **`parquet-to-open-table-format` skill** owns *whether the storage layer still holds*, which is
  a question about change, never about size.
- **`chart-type-and-library-selection` skill** owns *the form a chart takes*;
  **`dashboard-color-and-visual-hierarchy` skill** owns *what its colours encode and whether they
  can be read*; **`dashboard-layout-by-widget-mix` skill** owns *where the panels sit on a page*.
  Three separate decisions that are usually made as one, badly.

The seam is easy to state: extraction comes before shape, shape comes before values, cleaning is about values, disclosure is
about coverage, narrative is about claims, and privacy cuts across all of them.

## When none of them applies

Not every task touching a file is a data task. Reading a configuration file, editing a fixture,
or changing code that happens to mention a CSV is ordinary work. These skills apply when a
dataset is being turned into an answer.

## Verification

- [ ] The stage this request belongs to is named before any work starts.
- [ ] The artefacts this work will write or change are listed before it starts, and each one names
      the stage it belongs to.
- [ ] Where the request's verb — re-run, verify, fix, refresh — differs from what the work will
      actually write, the artefact decided the stage and the verb did not.
- [ ] If this source has arrived before, the new profile was compared against the recorded one
      and the differences are written down, including the overlap on the key.
- [ ] Everything the reader reads is in the reader's language, with nothing left in another,
      and every column name, path and manifest key is unchanged.
- [ ] Displayed numbers and dates use the reader's separators and order, while the stored
      values keep one canonical form.
- [ ] Whether the result leaves the project, and whether somebody will act on it, were both
      answered from the request before the work started, not from the size of the file.
- [ ] If both answers were no, the words in the request that support that are quoted next to the
      decision. An unsupported no is the cheap answer asserted, which is the thing Step 4 of the
      `chart-type-and-library-selection` skill refuses for the same reason.
- [ ] If the reviewers and the full disclosure were skipped because both answers were no, the
      answer says so in the words a reader would need to know it was not reviewed.
- [ ] Nothing was skipped beyond the reviewers and the length of the disclosure. Every stage ran
      and every skill that applied was invoked in full, because the gate is about the machinery
      around the stages and never about the stages.
- [ ] Every applicable skill was invoked in full, not summarized.
- [ ] No stage was skipped, or the skip is stated in the answer with its reason.
- [ ] Every skill named in the answer exists in this catalog. If a request needs something the
      catalog does not cover, say so plainly rather than naming a skill that is not here.
