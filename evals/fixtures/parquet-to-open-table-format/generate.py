#!/usr/bin/env python3
"""Generate the partitioned event directory for the parquet-to-open-table-format eval.

Three monthly Parquet parts. The third one adds a `refund_reason` column that the first two do
not have, which is the ordinary way a schema changes: somebody needed a field and added it going
forward.

Reading the directory therefore drops that column entirely, with no error and no warning, because
a reader takes the schema from the first file in name order. The file names here sort so that the
narrow schema comes first, which is the common case and the one that loses data. The same three
files named the other way round would keep the column and null it for the older rows.

The directory also holds one order recorded twice, once with the wrong amount, which is what a
correction looks like when the storage layer has no way to apply one.

Needs the ``fixtures`` extra (``uv sync --extra fixtures``) for pyarrow. Deterministic: the values
come from a fixed seed.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
EVENTS = HERE / "events"
SEED = 20260904
PER_MONTH = 4_000

MONTHS = [
    ("part-2025-07.parquet", date(2025, 7, 1), 31, False),
    ("part-2025-08.parquet", date(2025, 8, 1), 31, False),
    ("part-2025-09.parquet", date(2025, 9, 1), 30, True),
]
REASONS = ["damaged", "late", "wrong item", "changed mind"]


def month_rows(
    rng: random.Random, start: date, days: int, with_reason: bool, first_id: int
) -> dict[str, list[object]]:
    """One month of orders; September carries the column that was added later."""
    columns: dict[str, list[object]] = {
        "order_id": [],
        "occurred_on": [],
        "status": [],
        "amount": [],
    }
    if with_reason:
        columns["refund_reason"] = []
    for index in range(PER_MONTH):
        status = rng.choices(["completed", "refunded"], [92, 8])[0]
        columns["order_id"].append(first_id + index)
        columns["occurred_on"].append(start + timedelta(days=rng.randrange(days)))
        columns["status"].append(status)
        columns["amount"].append(round(rng.lognormvariate(0, 0.5) * 74.0, 2))
        if with_reason:
            columns["refund_reason"].append(rng.choice(REASONS) if status == "refunded" else None)
    return columns


def main() -> None:
    """Write the three monthly parts."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    EVENTS.mkdir(exist_ok=True)
    rng = random.Random(SEED)
    first_id = 1
    written = []
    for name, start, days, with_reason in MONTHS:
        columns = month_rows(rng, start, days, with_reason, first_id)
        if name.endswith("07.parquet"):
            # The correction that the storage layer cannot apply: order 1 appears twice, once
            # with an amount everyone agrees is wrong and once with the amount that replaced it.
            # Nothing in a directory of files makes the second one win.
            for key, value in (
                ("order_id", 1),
                ("occurred_on", date(2025, 7, 4)),
                ("status", "completed"),
                ("amount", 1904.55),
            ):
                columns[key].append(value)
        table = pa.table(columns)
        pq.write_table(table, EVENTS / name)
        written.append((name, table.num_rows, table.schema.names))
        first_id += PER_MONTH

    for name, rows, names in written:
        print(f"wrote {name}: {rows} rows, columns {names}")
    read_back = pq.read_table(EVENTS)
    print(f"reading the directory returns {read_back.num_rows} rows, columns {read_back.schema.names}")


if __name__ == "__main__":
    main()
