<!-- Title: what the change does and why, in one sentence. Body: what was found, what was
     decided, what the evidence was. The body becomes the squash commit on main. -->

## What this changes

## What it was found by

<!-- A test run, an audit, a failing eval, a reader's report. Name it; a change with no origin is
     a preference. -->

## Evidence

- [ ] `bash scripts/ci-local.sh` ran on the final commit and finished `OK`
- [ ] Every file is in English; nothing names a commercial product as origin, sponsor or recommendation
- [ ] Any new fixture is synthetic and carries a `FIXTURE.md` saying how it was generated
- [ ] A skill's description changed → Tier 2 rank-1 rate is unchanged or higher, and the numbers are in this body
- [ ] A skill's rules changed → Tier 3 for that skill was run once and read, and the verdicts are in this body
- [ ] A shipped script changed → `scripts/sync_skill_scripts.py` ran and the copies do not drift
- [ ] A persona changed → `scripts/sync_agents.py` ran and the four generated copies do not drift

## What is deliberately not done

<!-- Zero debt at merge: a real gap is a blocker, a fix here, or an issue linked from this line. -->
