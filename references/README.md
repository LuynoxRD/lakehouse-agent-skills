# Shared references

Checklists and tables used by **more than one** skill. A file here is linked from at least two
skills (`scripts/validate_reference_links.py` warns at one consumer and fails at none); material
a single skill needs lives next to that skill instead.

Planned files and their consumers:

| File | Used by |
| --- | --- |
| `capacity-thresholds.md` | honest-data-limits-disclosure, duckdb-for-local-analytics, chart-type-and-library-selection, parquet-to-open-table-format |
| `chart-decision-table.md` | chart-type-and-library-selection, dashboard-color-and-visual-hierarchy, dashboard-layout-by-widget-mix |
| `data-quality-checklist.md` | etl-before-dashboard, spreadsheet-integrity |
| `disclosure-template.md` | honest-data-limits-disclosure, insight-narrative-integrity |
| `pii-patterns.md` | data-privacy-before-llm |

A per-skill install (`npx skills add <repo> --skill <name>`) does not carry this directory. Every
skill therefore keeps the guidance it cannot work without inline and says, next to each link,
what the reader loses when the shared file is absent.
