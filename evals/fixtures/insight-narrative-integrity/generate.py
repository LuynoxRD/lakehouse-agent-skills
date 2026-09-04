#!/usr/bin/env python3
"""Generate the pre-aggregated summaries for the insight-narrative-integrity eval.

Standard library only, fully deterministic. The numbers are chosen so that the naive reading
and the correct one differ enough to be unmistakable; FIXTURE.md states each trap.
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).parent

# Group sizes differ by an order of magnitude, so the mean of the means (60.00) is 2.14 times
# the weighted mean (28.00). The file offers avg_order_value, which invites the wrong one.
REGIONS = [
    ("North", 10, 100.00),
    ("South", 90, 20.00),
]

# A treatment-style comparison where each stratum favours A and the pooled figure favours B,
# because A was applied mostly to the harder stratum.
COHORTS = [
    ("A", "small", 81, 87),
    ("A", "large", 192, 263),
    ("B", "small", 234, 270),
    ("B", "large", 55, 80),
]

# The largest bucket has no name, and is 2.6 times the leading named channel.
CHANNELS = [
    ("Other", 3100),
    ("Direct", 1200),
    ("Search", 1100),
    ("Email", 900),
    ("Referral", 700),
    ("Unknown", 300),
]


def write(name: str, header: list[str], rows: list[list[object]]) -> None:
    """Write one CSV with LF endings."""
    path = HERE / name
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {path} ({path.stat().st_size} bytes)")


def main() -> None:
    """Write the three summaries."""
    write(
        "region_summary.csv",
        ["region", "orders", "avg_order_value"],
        [[name, orders, f"{mean:.2f}"] for name, orders, mean in REGIONS],
    )
    write(
        "cohort_outcomes.csv",
        ["variant", "segment", "successes", "trials"],
        [[variant, segment, s, n] for variant, segment, s, n in COHORTS],
    )
    write(
        "channel_sessions.csv",
        ["channel", "sessions"],
        [[channel, sessions] for channel, sessions in CHANNELS],
    )


if __name__ == "__main__":
    main()
