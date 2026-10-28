# Security policy

A `SKILL.md` in this repository is code that runs inside someone else's coding agent. We treat the
content of skills, hooks, commands and reviewer personas as code, and we treat the validators and CI
that gate them as part of the trusted computing base.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository:
[report a vulnerability](https://github.com/LuynoxRD/lakehouse-agent-skills/security/advisories/new),
or **Security → Report a vulnerability** on the repository page. Do not open a public issue,
discussion or pull request for a security problem.

Include what you found, where it is (file and line), how it could be abused, and, if you have one, a
suggested fix. You will receive an acknowledgement within 3 business days and a status update within
7 days. Fixes for high-impact findings are targeted within 14 days of confirmation; lower-impact
findings are scheduled and tracked in the advisory.

## What counts as a security issue here

- A skill, command, hook or reviewer persona that instructs an agent to fetch and execute remote
  code, decode hidden payloads, read or transmit environment variables, write outside the user's
  project, or delete user data.
- A hook that performs network calls or reads data it does not need.
- A validator or workflow that can be bypassed to merge such content, or a workflow that runs
  untrusted code with secrets, uses a floating action tag, or requests more permissions than it
  needs.
- Fixtures or examples that contain real personal data, real company data, or credentials.
- Anything that would make an installed skill behave differently from what its text says.

Questions about data-engineering advice in a skill (a threshold, a chart choice, a cleaning rule) are
not security issues; open a regular issue for those.

## Supported versions

Security fixes land on `main` and in the latest tagged release. Older tags are not patched; update to
the latest release.

Nothing an installed copy does is automatic: a fix on `main` reaches no one until they run
`npx skills update` or `claude plugin update`. A vulnerability therefore gets a GitHub security
advisory as well as a release, because the advisory is the part that reaches people who are not
watching this repository. `docs/installing.md` has the update commands and one thing that surprises
people, which is that an install made from a local checkout is never updated.

Dependabot is not part of this. It watches this repository's own toolchain, the pinned Actions and
the locked Python packages, and it opens pull requests here. It does not read skill content and it
cannot notify anyone who installed the pack. Skill content is guarded by
`scripts/validate_skill_safety.py` on every pull request.

## Safe harbor

Good-faith research that respects this policy, avoids privacy violations and service disruption, and
gives us reasonable time to respond is welcome and will not be pursued.
