#!/usr/bin/env python3
"""Generate the mixed-shape export for the structured-vs-unstructured-routing eval.

One newline-delimited JSON file holding all three shapes at once, because the skill's whole job is
telling them apart:

* fields every record has, with scalar values, which is a table stored as JSON;
* a nested object, an array whose length varies, and a field only a minority of records carry,
  which is genuinely semi-structured;
* two string fields that look alike and are not: `plan` is categorical with a vocabulary that
  stops at four words, and `comment` is free text whose vocabulary keeps growing.

The trap is that eyeballing the first few records shows neither the rare field nor the difference
between the two string columns. Only the measurements in Step 1 of the skill separate them.

Standard library only, fully deterministic: the values come from a fixed seed.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
EXPORT = HERE / "feedback.jsonl"
SEED = 20260904
RECORDS = 220
START = date(2025, 10, 1)

PLANS = ["starter", "team", "business", "enterprise"]
REGIONS = ["emea", "amer", "apac"]
TAGS = ["billing", "onboarding", "performance", "mobile", "reporting", "integrations", "search"]

# Free text assembled from parts, so the vocabulary keeps growing with the row count instead of
# repeating a fixed set of sentences.
OPENERS = [
    "The export finished but",
    "After the last update",
    "Every morning",
    "When I switch workspaces",
    "Since we moved to the new plan",
    "On a slow connection",
    "If two people edit at once",
    "The first time I logged in",
]
SUBJECTS = [
    "the dashboard",
    "the invoice screen",
    "the scheduled report",
    "the mobile app",
    "the search box",
    "the integration with our warehouse",
    "the permissions page",
    "the weekly digest",
]
PROBLEMS = [
    "takes almost a minute to load",
    "shows figures from the previous month",
    "loses the filters I set",
    "logs me out without warning",
    "returns nothing for a term I know exists",
    "duplicates the last row",
    "sends twice to the same address",
    "silently drops the currency symbol",
]
CLOSERS = [
    "which makes the number impossible to trust.",
    "and I have to start again.",
    "so we stopped using it.",
    "and support told me it was expected.",
    "which nobody else on the team can reproduce.",
    "and it only happens on the larger accounts.",
]

ESCALATION_NOTES = [
    "raised to the account team",
    "second report from this customer",
    "linked to the incident on the third",
]


def build(rng: random.Random) -> list[dict[str, object]]:
    """One record per piece of feedback."""
    records: list[dict[str, object]] = []
    for index in range(RECORDS):
        record: dict[str, object] = {
            "feedback_id": f"FB-{index + 1:04d}",
            "received_on": (START + timedelta(days=rng.randrange(90))).isoformat(),
            "plan": rng.choice(PLANS),
            "rating": rng.randint(1, 5),
            # A nested object, present in every record but with an inner field that is not.
            "account": {
                "account_id": rng.randrange(1000, 9999),
                "region": rng.choice(REGIONS),
            },
            # Arrays of different lengths, including empty ones.
            "tags": rng.sample(TAGS, rng.choice([0, 1, 1, 2, 2, 3])),
            "comment": " ".join(
                [
                    rng.choice(OPENERS),
                    rng.choice(SUBJECTS),
                    rng.choice(PROBLEMS),
                    rng.choice(CLOSERS),
                ]
            ),
        }
        # A minority field: only escalated items carry it, and only some of those carry the
        # inner seat count. Roughly one record in twelve.
        if rng.random() < 1 / 12:
            record["escalation"] = {
                "note": rng.choice(ESCALATION_NOTES),
                "owner": rng.choice(["support", "success", "engineering"]),
            }
        if rng.random() < 1 / 6:
            account = record["account"]
            assert isinstance(account, dict)
            account["seats"] = rng.randrange(3, 400)
        records.append(record)
    return records


def main() -> None:
    """Write the export and report the numbers the skill asks a run to measure."""
    records = build(random.Random(SEED))
    with EXPORT.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    escalated = sum(1 for r in records if "escalation" in r)
    seats = sum(1 for r in records if "seats" in r["account"])  # type: ignore[operator]
    comment_vocab = len({w for r in records for w in str(r["comment"]).split()})
    plan_vocab = len({str(r["plan"]) for r in records})
    mean_comment = sum(len(str(r["comment"])) for r in records) / len(records)
    print(
        f"wrote {EXPORT} ({len(records)} records)\n"
        f"  escalation present in {escalated}, account.seats present in {seats}\n"
        f"  comment: mean {mean_comment:.0f} chars, vocabulary {comment_vocab}\n"
        f"  plan: vocabulary {plan_vocab}"
    )


if __name__ == "__main__":
    main()
