#!/usr/bin/env python3
"""Generate the synthetic order export for the etl-before-dashboard eval.

Standard library only, fully deterministic: `python generate.py` rewrites the same bytes.
Every trap is deliberate and documented in FIXTURE.md.
"""

from __future__ import annotations

import csv
import io
import random
from pathlib import Path

SEED = 20260904
ROWS = 240
OUTPUT = Path(__file__).parent / "orders.csv"

STATUS_SPELLINGS = ["shipped", "shipped", "shipped", "pending", "", "N/A", "-", "null", "NULL"]
STORE_CODES = ["007", "013", "042", "100", "0075"]


def build_rows(rng: random.Random) -> list[list[str]]:
    """One row per order, with the ambiguities a real export carries."""
    rows: list[list[str]] = []
    revenue = 0.0
    for index in range(ROWS):
        # Days 1..12 are ambiguous between day-first and month-first. A handful of rows use a
        # day above 12, which is the only evidence in the file that the order is day-first.
        day = rng.randint(1, 12) if index % 17 else rng.randint(13, 28)
        month = rng.randint(1, 6)
        order_date = f"{day:02d}/{month:02d}/2025"

        cents = rng.randint(500, 250_000) / 100
        revenue += cents
        # Two thirds of the amounts use a decimal comma with a dot as thousands separator,
        # the rest use a plain dot, so a single parsing rule cannot be right for the column.
        if index % 3:
            amount = f"{cents:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        else:
            amount = f"{cents:.2f}"

        rows.append(
            [
                f"{index + 1:05d}",
                rng.choice(STORE_CODES),
                order_date,
                amount,
                rng.choice(STATUS_SPELLINGS),
                rng.choice(["", "", "gift wrap", "customer called", "re-issued"]),
            ]
        )
    # A grand total that looks like one more order.
    rows.append(["", "", "", f"{revenue:,.2f}".replace(",", "").replace(".", ","), "Total", ""])
    return rows


def main() -> None:
    """Write orders.csv with a byte-order mark and CRLF line endings."""
    rng = random.Random(SEED)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(["order_id", "store_code", "order_date", "amount", "status", "notes"])
    writer.writerows(build_rows(rng))
    # A byte-order mark, as exported by a spreadsheet on Windows: the first column name is not
    # readable as "order_id" unless the reader is told about it.
    OUTPUT.write_bytes(b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8"))
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
