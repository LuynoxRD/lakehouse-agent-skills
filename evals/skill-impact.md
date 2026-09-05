# Skill impact ledger

Changes to skill descriptions or bodies that were rejected on eval evidence, so the same idea
is not retried without new arguments. Add a row when a pull request is closed because the Tier 2
rank-1 rate, a negative trigger, a collision check or a Tier 3 behavioral eval got worse.

| Date | Skill | Change tried | Evidence | Outcome |
| --- | --- | --- | --- | --- |
| 2026-09-05 | `etl-before-dashboard` | Describing the second arrival of a source as "a new export or a corrected file", to route the arrival-comparison step | Tier 2 rank-1 fell from 100.0% to 97.7%. `export` already appeared in this description, so repeating it raised the term's weight enough to take rank 1 from `honest-data-limits-disclosure` on "I ran a batch over 200 exports and some of them threw errors that the loop swallowed" | Reworded to "a refreshed or corrected file". Same meaning, no repeated term; rank-1 back to 100.0% with 44 positives instead of 42. **A word already in a description is not free to reuse in it.** |
