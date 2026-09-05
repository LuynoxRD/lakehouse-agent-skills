---
description: Profile a dataset before anything is cleaned, charted or claimed about it.
---

Profile the dataset the user named, and change nothing while doing it.

If it is not obvious whether the source is a table, uneven records or free text, invoke the
`structured-vs-unstructured-routing` skill first and settle the shape with measurements before
going further.

If `docs/data/profile.md` already exists for this source, this is a second arrival and the job
is a comparison, not a repetition. Follow the arrival step of the `etl-before-dashboard` skill
first: columns that appeared or are gone, types that changed, the null spellings, the overlap on
the declared key as counts, and whether each recorded cleaning rule still matches anything. Say
whether this file appends rows or restates them, with the numbers.

Then invoke the `etl-before-dashboard` skill and follow its profiling step in full. Write
`docs/data/profile.md`, covering every column and every trap that skill lists, and state each
ambiguity as a decision with the evidence that settled it.

If the source is a batch, a workbook, or larger than what can be read whole, also invoke the
`honest-data-limits-disclosure` skill for its pre-flight, so the profile says what it could not
reach before anyone builds on it.

Do not clean, chart or summarise anything in this step. Finish by naming what the profile found
that will change the cleaning.
