---
description: Decide what one row means and persist the modelled table to columnar storage.
context: fork
background: false
---

Model the cleaned dataset and persist it.

Invoke the `etl-before-dashboard` skill and follow its modelling and persistence steps. Write
`docs/data/model.md` stating in one sentence what a single row means, name the key that makes a
row unique and verify it, then write the table to `data/curated/` as Parquet with the types you
proved.

If two sources have to be related, settle that here rather than in the query. Name the key on
each side, prove it is the same thing on both (whitespace, case, type, leading zeros) and record
any normalisation as a cleaning rule, state the cardinality, and count the rows on each side
that match nothing before choosing a join type. One sentence per relation in `docs/data/model.md`.

Then invoke the `parquet-to-open-table-format` skill to check whether a directory of files is
still enough for this dataset. The trigger is change, never size: row-level corrections,
concurrent writers, a column that has to survive being added, or a reader that needs the same
answer twice. Say which of those apply, and say plainly when none of them do.

Finish by naming the curated table and its grain, because everything downstream will quote
them.
