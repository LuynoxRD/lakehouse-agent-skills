---
description: Clean a profiled dataset, recording every rule and the number of rows it touched.
---

Clean the dataset, working from `docs/data/profile.md`. If that file does not exist,
stop and run the profile step first; there is nothing to clean against without it.

Invoke the `etl-before-dashboard` skill and follow its cleaning step. Every change is a rule with
a reason in `docs/data/cleaning-log.md`, including how many rows it touched, and the output goes
to `data/clean/` while `data/raw/` stays byte-identical.

If the source is a workbook, invoke the `spreadsheet-integrity` skill as well: the source file is
never written to, and anything a round trip would drop is named before it happens rather than
discovered afterwards.

Finish by stating which ambiguities could not be resolved, because those travel with every number
that follows.
