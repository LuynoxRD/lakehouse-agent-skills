#!/usr/bin/env python3
"""Generate the curated tables for the duckdb-for-local-analytics eval.

Two Parquet tables that look ready to query and are not quite. The dimension table carries one
channel twice, so an unguarded join doubles that channel's revenue and moves it to the top of the
ranking; and the fact table carries cancelled and refunded orders whose amounts are still
positive, so a total that does not filter on status is high in a way nothing flags.

Both traps produce a plausible number. That is the point: the failure is not an error message, it
is a ranking that reads perfectly well and is wrong.

Needs the ``fixtures`` extra (``uv sync --extra fixtures``) for pyarrow. Deterministic: the values
come from a fixed seed.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
WAREHOUSE = HERE / "warehouse"
SEED = 20260904
ORDERS = 48_000
START = date(2025, 7, 1)
DAYS = 184  # two full quarters: Q3 and Q4 of 2025

CHANNELS = ["direct", "affiliate", "marketplace", "retail", "wholesale"]
# The share each channel takes of the orders, and the mean order value it tends to carry.
WEIGHTS = [0.34, 0.11, 0.28, 0.19, 0.08]
MEAN_AMOUNT = {
    "direct": 82.0,
    "affiliate": 45.0,
    "marketplace": 61.0,
    "retail": 118.0,
    "wholesale": 940.0,
}
STATUSES = ["completed"] * 88 + ["cancelled"] * 7 + ["refunded"] * 5


def build_orders(rng: random.Random) -> dict[str, list[object]]:
    """One row per order, across two quarters."""
    columns: dict[str, list[object]] = {
        "order_id": [],
        "placed_on": [],
        "channel_code": [],
        "status": [],
        "amount": [],
    }
    for index in range(ORDERS):
        channel = rng.choices(CHANNELS, WEIGHTS)[0]
        columns["order_id"].append(index + 1)
        columns["placed_on"].append(START + timedelta(days=rng.randrange(DAYS)))
        columns["channel_code"].append(channel)
        columns["status"].append(rng.choice(STATUSES))
        columns["amount"].append(round(rng.lognormvariate(0, 0.45) * MEAN_AMOUNT[channel], 2))
    return columns


def build_channels() -> dict[str, list[object]]:
    """The dimension table, with one code appearing twice.

    ``marketplace`` was renamed once and both rows were kept. Joining on the code multiplies every
    marketplace order by two, which reads as a channel that had a very good quarter.
    """
    return {
        "channel_code": ["direct", "affiliate", "marketplace", "marketplace", "retail", "wholesale"],
        "channel_name": [
            "Direct",
            "Affiliate",
            "Marketplace",
            "Marketplace (legacy)",
            "Retail partners",
            "Wholesale",
        ],
        "is_paid": [False, True, True, True, False, False],
    }


def main() -> None:
    """Write both tables under warehouse/."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    WAREHOUSE.mkdir(exist_ok=True)
    rng = random.Random(SEED)

    orders = pa.table(build_orders(rng))
    pq.write_table(orders, WAREHOUSE / "orders.parquet")
    channels = pa.table(build_channels())
    pq.write_table(channels, WAREHOUSE / "channels.parquet")

    completed = sum(1 for s in orders.column("status").to_pylist() if s == "completed")
    print(
        f"wrote {WAREHOUSE} "
        f"(orders {orders.num_rows} rows, {completed} completed, "
        f"channels {channels.num_rows} rows for {len(CHANNELS)} codes)"
    )


if __name__ == "__main__":
    main()
