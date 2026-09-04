#!/usr/bin/env python3
"""Generate the routing fixture for the using-lakehouse-skills eval.

Standard library only, fully deterministic. The file is small on purpose: the eval is about
naming the right stage and skill, not about processing volume. FIXTURE.md states each trap.
"""

from __future__ import annotations

import csv
from pathlib import Path

OUTPUT = Path(__file__).parent / "signups.csv"

# Small enough to read at a glance, and carrying one trap from each flagship skill:
# an ambiguous date and a text-typed number (cleaning), a plan bucket named Other that
# outweighs every named plan (narrative), and a note that the export is partial (coverage).
ROWS = [
    ["1001", "04/03/2025", "Other", "1.250,00", "partial export: 3 of 8 source files"],
    ["1002", "11/03/2025", "pro", "89,00", ""],
    ["1003", "23/03/2025", "team", "240,00", ""],
    ["1004", "02/04/2025", "Other", "1.100,50", ""],
    ["1005", "07/04/2025", "pro", "89,00", ""],
    ["1006", "09/04/2025", "Other", "980,00", ""],
    ["1007", "12/04/2025", "starter", "19,00", ""],
    ["1008", "18/04/2025", "Other", "1.310,25", ""],
]


def main() -> None:
    """Write signups.csv with LF endings."""
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["signup_id", "signup_date", "plan", "mrr", "export_note"])
        writer.writerows(ROWS)
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
