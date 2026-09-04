# Hooks

One hook, and it earns its place by staying quiet.

| File | Event | What it does |
| --- | --- | --- |
| `session-start.sh` | `SessionStart`, matcher `startup` | Counts the data files in the project. If there are any and `docs/data/profile.md` does not exist, it says so once. Otherwise it prints nothing. |

`hooks.json` is the configuration a plugin installs; the manifest field points at that file, not
at this directory.

## Why this one

The pack's whole claim is that profiling comes before charting. The place that gets skipped is a
session that opens in a project full of exports where nothing on screen says the step exists. One
line at the start costs almost nothing and is the only moment when saying it changes what happens
next.

Everything else a hook could do here was left out on purpose. A hook that fires on every tool call
spends tokens on every tool call, and a reminder nobody asked for twice is noise the third time.

## Contract

Verified against the documented hook interface rather than written from memory:

- **stdout** carries JSON: `hookSpecificOutput.hookEventName` is `SessionStart` and
  `hookSpecificOutput.systemMessage` is the text added as context.
- **stderr** carries status, and on a clean exit the tool sends it to the debug log only.
- **exit code is always 0.** A non-zero exit turns a reminder into an error notice, and exit 2
  would block the session outright. Nothing here is worth blocking a session for.
- **no network, ever.** The script reads the filesystem and writes one line.

It also removes its own temporary directory on exit, skips `.git`, `node_modules`, virtualenv and
cache directories, searches three levels deep, and lists at most five names before summarising the
rest.

## Installing it outside a plugin

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
    ]
  }
}
```

The script reads `CLAUDE_PROJECT_DIR` and falls back to the working directory, so it reports on
the project the session is in rather than on the repository the script lives in.

## Testing it

`tests/test_session_hook.py` starts the script as a real process for every case: data without a
profile, a profile that exists, no data at all, dependency directories that should not count,
more files than the list shows, a project directory that is not there, and a file name containing
a quote. Testing shell any other way tests a description of it.
