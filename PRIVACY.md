# Privacy

This plugin runs entirely on the machine where the coding agent runs. It has no server, no
account, no telemetry and no network activity of its own.

## What the plugin is

Fifteen skills, nine commands, four reviewer personas and two session hooks. The skills, commands
and personas are text files the agent reads. The hooks and the shipped check
(`verify-output.sh`) are shell scripts with an embedded Python program.

## What it reads and writes

- The scripts read files inside the project directory the agent is working in, and nothing
  outside it. They write the notes the skills describe under `docs/data/` in that project, and
  temporary files in the system temporary directory that they remove on exit.
- The `Stop` hook reads the session transcript that the host tool names in the hook event, to
  check which skills were invoked. It reads it on the user's machine and sends nothing anywhere.
- None of the scripts makes a network call. `scripts/validate_skill_safety.py` fails the build on
  any skill or script that would fetch remote code, decode hidden payloads, read or transmit
  environment variables, write outside the project, or delete user data.

## What leaves the machine

Nothing, from this plugin. The coding agent that loads it may send data to the model provider it
is configured with, exactly as it does without the plugin; that traffic is the agent's and the
provider's, governed by their own policies. One skill in this pack, `data-privacy-before-llm`,
exists to make the agent decide what may leave the project before any rows are pasted into a
prompt or sent to a hosted service, and to record what was sent.

## What this repository collects

Nothing beyond what GitHub records for any repository (issues, pull requests, stars). The
evaluation fixtures in `evals/fixtures/` are synthetic; no real personal or company data is
stored here, and `CONTRIBUTING.md` forbids adding any.

## Contact

Questions about this statement: the maintainer, through the contact on the GitHub profile linked
from the plugin manifest (`.claude-plugin/plugin.json`, `author.url`).
