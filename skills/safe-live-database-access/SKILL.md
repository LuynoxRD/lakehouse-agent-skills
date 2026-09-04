---
name: safe-live-database-access
description: Treats a live database as a system other people depend on rather than a file that was handed over, so it stays read-only unless a write was asked for, the cost of a query is known before it runs, credentials are never copied into code or output, and every write is confirmed as its own decision. Use when connecting to a shared or production database, when a query will run against a system that is serving other users, when a task needs credentials to reach data, or when a request asks to insert, update or delete rows.
---

# Safe live database access

## Overview

A file that was handed over is a copy. Nothing an agent does to it reaches anyone else, and the
worst outcome is a wrong answer. A live database is the opposite on every count: the rows are
being read and written by other people right now, a query competes with their queries for the
same machine, and a statement that changes data changes it for everybody at once.

Nothing about the SQL looks different. The same `DELETE` runs the same way against a copy and
against the system a business is running on. What has to change is everything around it.

```
CONNECT read-only ──► COST the query ──► AGGREGATE at the source ──► move the answer
                                                     │
                                  a write leaves this path and becomes its own decision
```

## When to Use

Use this skill the moment a task involves a database that is not a local copy made for this work:
a production system, a shared warehouse, a replica other people query, a service reached with
credentials.

Use it when a request asks to change rows, whatever the wording. "Clean up the test records",
"fix the duplicate", "just drop that column" are all writes to a live system.

Do **not** use it for a database file created by this work as an intermediate step; that is
ordinary local storage and belongs to the `etl-before-dashboard` skill. Once rows have arrived,
what happens to their values is that skill's, and what the answer may claim about coverage
belongs to the `honest-data-limits-disclosure` skill. This skill owns the connection, the cost
and the writes.

## Core Process

### Step 1: Open the connection read-only, and prove that it is

Read-only is a property of the connection, not an intention. Most engines take it as an explicit
option when the connection is opened, and the option is either accepted or the connection is not
read-only; there is no middle state.

Two details decide whether it took effect, and both are checkable rather than assumable:

- **Syntax is not forgiving.** In DuckDB the attach options go in parentheses:
  `ATTACH '<connection>' AS live (TYPE postgres, READ_ONLY)`. Written without them the statement
  does not parse at all, which is the safe failure. The dangerous shape is an option that parses
  and does nothing.
- **A misspelled option is not silently ignored.** Passing an option the engine does not know
  raises an error naming it. That is how to tell a real option from one that was remembered
  wrongly: give it a deliberately wrong name once and confirm the engine complains. An option
  that produces no error and no effect is the one that lets a write through.

Then confirm the connection behaves as declared, by attempting the smallest possible write and
seeing it refused. A connection assumed read-only is a connection that has not been tested.

### Step 2: Credentials come from outside the work and stay there

The connection string arrives from a secret manager or the environment the process already runs
in. It is never typed into a file this work creates, never printed, never included in an error
message, a log line, a commit, or an answer to the user.

- If a credential is visible in something handed over, treat it as exposed: say so, and say it
  should be rotated. Reading it does not make it safe.
- Refer to a credential by the name of the place it lives, never by its value.
- Before writing any file that contains a connection detail, ask whether the value or only the
  location is needed. It is almost always the location.

### Step 3: Know what a query costs before a live system pays for it

A query against a shared system spends someone else's resources. Estimate first:

- Read the plan the engine produces for the statement, and say what it will scan. A plan showing
  a full scan of the largest table is a result in itself.
- Probe with a bounded statement before an unbounded one: a count over a narrow filter, or the
  same query restricted to a small range, tells you the shape of the answer without the cost of
  it.
- Never issue an unbounded select against a table whose size is unknown. "It is probably small"
  is not a size.
- State the estimate before running: which tables, roughly how many rows, and whether it is
  expected to be seconds or minutes. If the answer is minutes on a production system, that is a
  decision for the person who owns the system, not a detail to discover afterwards.

### Step 4: Aggregate where the data already is

Move the answer, not the table. A grouped aggregate computed in the database transfers a handful
of rows; the same aggregate computed after dragging the table out transfers all of them, costs
the live system the full scan anyway, and lands data on a machine that was not supposed to hold
it.

Pull raw rows only when the task genuinely needs them, and then say how many and why. If they
contain personal data, they do not leave the system before the `data-privacy-before-llm` skill
has been applied.

### Step 5: A write is a separate decision, taken in steps

Nothing in a read task turns into a write on its own. When a write is genuinely the request:

1. **Show the target set first.** Run the select that matches exactly the rows the write would
   touch, and report the count. A write whose row count nobody stated is a write nobody agreed
   to.
2. **Ask for confirmation that names the count and the table.** "Yes, go ahead" against an
   unstated number is not confirmation. The person confirming has to be able to see what they are
   agreeing to.
3. **Wrap it so there is a way back.** Run inside a transaction, verify the affected count
   matches the number that was confirmed, and only then commit. A count that does not match is a
   reason to roll back, not to investigate afterwards.
4. **Schema changes and deletes without a filter never happen as part of something else.** They
   are their own request, confirmed on their own.

There is no version of this that is faster because the change is small. The steps exist because
the cost of the mistake is not proportional to the size of the statement.

### Step 6: Say what connecting changes on the machine

Reaching a database is not always a pure read of a remote system. Engines load their connectors
as extensions, and they may fetch them over the network on first use: attaching a database in
DuckDB downloads and installs the connector, persisting it under the user's home directory,
without prompting. Once it is on disk, turning the automatic install off no longer prevents the
attach, so the check has to happen before the first connection, not after.

That matters wherever a machine is audited, offline, or subject to a policy about what it may
download. Name the connectors the work will need and whether they are already present, before
the first statement runs.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "It is a read-only query, so it is safe." | Safe from changing data, not from cost. An unbounded scan on a busy table is an outage that happens to be spelled `SELECT`. |
| "I set the connection to read-only." | Setting is not proving. Attempt a write once and watch it be refused; that takes a second and removes the whole class of doubt. |
| "It is only the test rows." | The filter that selects "only the test rows" is the entire risk. Show the rows first, count them, then delete the counted set. |
| "There is a backup, so a bad write is recoverable." | Restoring a production database is an incident with a duration. A backup changes the size of the disaster, not whether it happened. |
| "The credential was in the file they sent me, so it is fine to use it there." | It was exposed when it was sent. Using it further does not make it less exposed, and copying it anywhere else spreads it. |
| "I will pull the table and aggregate locally, it is simpler." | Simpler for the code, more expensive for the shared system, and it moves data that was not asked to move. |
| "The query worked in staging." | Staging has a different data volume and a different plan. The plan is the thing that has to be read against the system it will run on. |
| "They asked me to fix it, so the write is already approved." | Approved in intent, not in extent. Confirmation is about which rows, and how many, not about whether something should be fixed. |

## Red Flags

Stop when any of these is true:

- A statement that changes data is about to run and no row count has been stated.
- A `DELETE` or `UPDATE` has no `WHERE`, or its `WHERE` was never run as a `SELECT` first.
- The connection was opened without a read-only option on a task that only reads.
- A credential value appears in a file this work wrote, in a log, or in the answer.
- A query is about to run against a live system with no estimate of what it will scan.
- The whole table is being transferred so that it can be aggregated afterwards.
- A schema change is riding along with a data task.
- The engine reported installing something in order to connect, and nobody said it would.

## Verification

- [ ] The connection was opened with an explicit read-only option, and a write was attempted once
      and refused, proving it took effect.
- [ ] No credential value appears in any file this work created, in the output, or in the answer;
      credentials are referred to by where they live.
- [ ] Every statement run against the live system had its expected cost stated first, backed by
      the engine's own plan or a bounded probe.
- [ ] Aggregates were computed at the source, and any raw rows pulled are counted and justified
      in the answer.
- [ ] For any write: the matching rows were selected and counted first, the confirmation named
      that count and that table, the statement ran in a transaction, and the affected count was
      checked against the confirmed number before committing.
- [ ] Any connector the engine installed to make the connection is named in the answer.
