# Skills

One directory per skill, each with a `SKILL.md` as the only required file. The catalog follows
the data lifecycle:

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE   (+ REDACT, cross-cutting)
```

The catalog is being built in phases. The router `using-lakehouse-skills` lands first and fixes
the boundaries between skills; the flagship trio (`honest-data-limits-disclosure`,
`etl-before-dashboard`, `insight-narrative-integrity`) follows; the remaining skills complete the
lifecycle.

Every skill here satisfies [the anatomy](../docs/skill-anatomy.md), ships an eval case under
`evals/cases/` and a synthetic fixture under `evals/fixtures/`, and passes
`scripts/validate_skills.py` and `scripts/validate_skill_safety.py`. To propose a new one, read
[CONTRIBUTING.md](../CONTRIBUTING.md) first.
