---
description: Answer a question with SQL over the table that was already persisted.
context: fork
background: false
---

Answer the user's question with SQL.

Invoke the `duckdb-for-local-analytics` skill. Query the persisted table under `data/curated/`
rather than the source, state the grain of the result before writing the query, and check the row
count across any join instead of assuming it. Read the engine's plan before claiming anything
about what a query costs.

If the question has to be answered against a database other people are using, invoke the
`safe-live-database-access` skill first and follow it completely: read-only unless a write was
actually asked for, the cost stated before the statement runs, credentials never reproduced, and
any write confirmed as its own decision with its row count named.

Finish with the query itself, its result, and the definition behind any number you report.
