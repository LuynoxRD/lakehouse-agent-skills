#!/usr/bin/env python3
"""Generate the three results for the chart-type-and-library-selection eval.

Each file is a result that a habit would render one way and its shape rules that way out:

* ``category_share.csv`` has 43 categories with a long tail, so a pie is unreadable and equal
  visual weight for every category hides where the total actually is.
* ``signups_daily.csv`` is a time series with a 17-day gap and its rows deliberately out of date
  order, so a line drawn as the file arrives both connects across missing days and joins points
  in the order they happen to be written.
* ``price_vs_units.csv`` is two continuous variables with a dense region, so it is a relationship
  rather than a set of categories, and the dense region is the finding.

Standard library only, fully deterministic: the values come from a fixed seed.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results"
SEED = 20260904

CATEGORIES = 43
START = date(2025, 9, 1)
DAYS = 120
GAP_START = 61
GAP_LENGTH = 17
SCATTER_POINTS = 900


def write_category_share(rng: random.Random) -> None:
    """A long tail: three categories hold most of the total, forty share the rest."""
    names = [f"segment_{index + 1:02d}" for index in range(CATEGORIES)]
    head = [41800.0, 26350.0, 18900.0]
    tail = [round(rng.uniform(90.0, 1400.0), 2) for _ in range(CATEGORIES - len(head))]
    values = head + tail
    with (RESULTS / "category_share.csv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["segment", "revenue"])
        writer.writerows(zip(names, values, strict=True))
    total = sum(values)
    print(
        f"  category_share.csv: {CATEGORIES} categories, "
        f"top 3 hold {sum(head) / total:.1%} of {total:,.0f}"
    )


def write_signups(rng: random.Random) -> None:
    """A daily series with a hole in it, written out of order."""
    rows = []
    level = 180.0
    for offset in range(DAYS):
        if GAP_START <= offset < GAP_START + GAP_LENGTH:
            continue  # the days the collector was down; they are absent, not zero
        level = max(40.0, level + rng.gauss(0.4, 14.0))
        rows.append(((START + timedelta(days=offset)).isoformat(), round(level)))
    rng.shuffle(rows)
    with (RESULTS / "signups_daily.csv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["day", "signups"])
        writer.writerows(rows)
    print(
        f"  signups_daily.csv: {len(rows)} rows of {DAYS} days, "
        f"{GAP_LENGTH}-day gap from {(START + timedelta(days=GAP_START)).isoformat()}, "
        "rows not in date order"
    )


def write_price_units(rng: random.Random) -> None:
    """Two continuous variables, most of the mass in one corner."""
    rows = []
    for _ in range(SCATTER_POINTS):
        if rng.random() < 0.78:
            price = rng.uniform(8.0, 26.0)
            units = max(1.0, rng.gauss(240.0 - price * 6.0, 22.0))
        else:
            price = rng.uniform(26.0, 190.0)
            units = max(1.0, rng.gauss(120.0 - price * 0.4, 30.0))
        rows.append((round(price, 2), round(units)))
    with (RESULTS / "price_vs_units.csv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["unit_price", "units_sold"])
        writer.writerows(rows)
    dense = sum(1 for price, _ in rows if price < 26.0)
    print(f"  price_vs_units.csv: {SCATTER_POINTS} points, {dense} of them under 26.00")


def main() -> None:
    """Write all three results."""
    RESULTS.mkdir(exist_ok=True)
    print(f"wrote {RESULTS}")
    write_category_share(random.Random(SEED))
    write_signups(random.Random(SEED))
    write_price_units(random.Random(SEED))


if __name__ == "__main__":
    main()
