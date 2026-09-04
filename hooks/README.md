# Hooks

Two hooks. One earns its place by staying quiet; the other by being the only thing here that can
say no.

| File | Event | What it does |
| --- | --- | --- |
| `session-start.sh` | `SessionStart`, matcher `startup` | Counts the data files in the project. If there are any and `docs/data/profile.md` does not exist, it says so once. Otherwise it prints nothing. |
| `stop-evidence.sh` | `Stop`, matcher `*` | Sends the turn back once when a fact on disk is missing: a profile with no `docs/data/disclosure.md`, or declared figures with no fresh `docs/data/verification.json`. Otherwise it prints nothing. |

`hooks.json` is the configuration a plugin installs; the manifest field points at that file, not
at this directory.

## Why these two

The pack's whole claim is that profiling comes before charting and that a run states what it did
not cover. Everything else in this repository asks for that. These are the two moments when
something can do more than ask.

`session-start.sh` is the cheapest possible reminder, placed at the only moment when saying it
changes what happens next: a session opening in a project full of exports where nothing on screen
says the step exists.

`stop-evidence.sh` exists because of a ceiling worth stating plainly. Skills are discovered by
description: the model reads what is installed and decides for itself what applies. Nothing in the
mechanism intercepts a turn, so a router can go unread and a checklist can be ticked without being
executed, and that is true of every skill pack, not only this one. A `Stop` hook runs after the
turn is written and can return it, which makes it the single point in this repository where a step
is enforced rather than requested. It is Claude Code only. In the other tools this pack installs
into, the same discipline stays best-effort, and saying so is more useful than implying otherwise.

It checks two facts on disk, never the model's account of them:

- `docs/data/profile.md` exists and `docs/data/disclosure.md` does not.
- `docs/data/figures.json` exists and `docs/data/verification.json` is missing, or is older than
  the pages and the manifest it was supposed to have checked. That receipt is written by
  `verify-output.sh` only on a run with zero errors, and deleted by it on a run with any.

What the receipt proves is narrow and worth being honest about: that a green run happened over the
current bytes. A forged receipt would pass, and nothing checking after the fact can close that. It
closes the two cases that actually occur, which are never running the check, and running it and
then changing the file.

Everything else a hook could do here was left out on purpose. A hook that fires on every tool call
spends tokens on every tool call, and a reminder nobody asked for twice is noise the third time.

## Contract

Read from the documented hook interface rather than written from memory:

- `SessionStart`: **stdout** carries JSON where `hookSpecificOutput.hookEventName` is
  `SessionStart` and `hookSpecificOutput.systemMessage` is the text added as context.
- `Stop`: **stdout** carries `{"decision": "block", "reason": ...}` to send the turn back, and the
  reason is what the model is told. Printing nothing lets the turn end.
- **stderr** carries status, and on a clean exit the tool sends it to the debug log only.
- **exit code is always 0.** Exit 2 is a blocking error whose stderr is fed back, and any other
  non-zero is a non-blocking error notice. Neither is a thing to end up in by accident, so both
  scripts approve rather than fail when something is unreadable.
- **no network, ever.** They read the filesystem and write one line.

`stop-evidence.sh` blocks at most once per session. It reads `session_id` from the event payload
with a plain pattern rather than depending on a JSON tool being installed, and records that the
session was told in a marker under the system temporary directory, so it leaves nothing in the
user's repository. Without a session id it approves: an interruption it cannot bound is worse than
one it never makes. It also approves when the project directory is missing, when no profile exists,
and when the marker cannot be written.

## Installing them outside a plugin

In `.claude/settings.json`, with the path to wherever this repository sits:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/lakehouse-agent-skills/hooks/session-start.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/lakehouse-agent-skills/hooks/stop-evidence.sh"
          }
        ]
      }
    ]
  }
}
```

Both scripts read `CLAUDE_PROJECT_DIR` and fall back to the working directory, so they report on
the project the session is in rather than on the repository the scripts live in.

## Testing them

`tests/test_session_hook.py` and `tests/test_stop_hook.py` start each script as a real process for
every case: data without a profile, a profile that exists, no data at all, dependency directories
that should not count, more files than the list shows, a project directory that is not there, a
file name containing a quote, a second turn in the same session, a payload with no session id, a
receipt older than the page it vouches for, declared figures with no receipt at all, and a marker
directory that cannot be written. Testing shell any other way tests a description of it.
