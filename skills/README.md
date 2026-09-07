# Skills

One directory per skill, each with a `SKILL.md` as the only required file. The catalog follows
the data lifecycle:

```
PROFILE → CLEAN → MODEL → QUERY → VISUALIZE → ASSEMBLE → NARRATE → DISCLOSE   (+ REDACT, cross-cutting)
```

The catalog is complete: fifteen skills covering every stage. `using-lakehouse-skills` routes a
request to the one that owns it and fixes the boundaries between them, so start there when it is
not obvious which applies.

Every skill here satisfies [the anatomy](../docs/skill-anatomy.md), ships an eval case under
`evals/cases/` and a synthetic fixture under `evals/fixtures/`, and passes
`scripts/validate_skills.py` and `scripts/validate_skill_safety.py`. To propose a new one, read
[CONTRIBUTING.md](../CONTRIBUTING.md) first.
