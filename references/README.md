# Shared references

Checklists and tables used by **more than one** skill. A file here is linked from at least two
skills (`scripts/validate_reference_links.py` warns at one consumer and fails at none); material
a single skill needs lives next to that skill instead.

| File | Used by |
| --- | --- |
| `capacity-thresholds.md` | honest-data-limits-disclosure, spreadsheet-integrity, parquet-to-open-table-format |

Four more files were planned and deliberately not written once the skills existed, because the
material they would have held turned out not to meet the bar for this directory:

| Planned | Why it is not here |
| --- | --- |
| `chart-decision-table.md` | The decision tables in the three visualization skills are each about a different decision — which form, which palette, which area — and share no rows. A file holding all three would be three tables in one place, read by nobody. |
| `data-quality-checklist.md` | What `etl-before-dashboard` and `spreadsheet-integrity` share is two sentences about what a workbook round trip drops, and both need them inline for a per-skill install. Two sentences are not reference material. |
| `disclosure-template.md` | The artifact path `docs/data/disclosure.md` is shared; its contents differ by skill, since coverage, privacy and narrative each record different things. A shared template would have to be generic enough to be useless. |
| `pii-patterns.md` | Only one skill consumes it, which this directory's own rule excludes. It lives inline in `data-privacy-before-llm`. |

The rule that produced those four decisions is the repository's: if removing a section would not
change what an agent does, remove it. A shared file that only exists so that two skills can point
at it costs a fetch and buys nothing.

A per-skill install (`npx skills add <repo> --skill <name>`) does not carry this directory. Every
skill therefore keeps the guidance it cannot work without inline and says, next to each link,
what the reader loses when the shared file is absent.
