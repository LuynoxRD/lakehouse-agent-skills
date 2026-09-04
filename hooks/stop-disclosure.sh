#!/usr/bin/env bash
set -euo pipefail
#
# Refuse to end a turn that profiled a dataset and never said what the run did not cover.
#
# Every other nudge in this pack is a suggestion the model may decline: a description it may not
# read, a checklist it may tick without executing, a router it may never load. That is a ceiling
# of the mechanism rather than a gap in this pack, and it is the same everywhere skills are
# discovered by description. One event escapes it. A Stop hook runs after the turn is written and
# can send it back, which makes it the only place in this repository where "do not skip DISCLOSE"
# is enforced instead of requested.
#
# It fires narrowly on purpose. Blocking a turn that should have ended is worse than missing one
# that should not have, so all of these must hold:
#
#   * docs/data/profile.md exists, which means this pack's pipeline actually ran here. A session
#     that never touched data has no profile and is never interrupted.
#   * docs/data/disclosure.md does not exist.
#   * this session has not been sent back once already.
#
# Anything unexpected ends in approval. A hook that blocks because it could not read something is
# a hook that strands a session.
#
# Contract, read from the documented hook interface rather than recalled: a Stop hook decides with
# {"decision": "block", "reason": ...} on stdout, the reason is what the model is told, and exit 0
# leaves the turn alone. Claude Code only; no other tool runs this file.

readonly PROFILE_NOTE="docs/data/profile.md"
readonly DISCLOSURE_NOTE="docs/data/disclosure.md"

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

approve() {
  echo "stop-disclosure: $1" >&2
  exit 0
}

[ -d "$project_dir" ] || approve "no project directory at $project_dir"
[ -f "$project_dir/$PROFILE_NOTE" ] || approve "no $PROFILE_NOTE; this session did not profile a dataset"
if [ -f "$project_dir/$DISCLOSURE_NOTE" ]; then
  approve "$DISCLOSURE_NOTE exists"
fi

# The event payload arrives on stdin, and is held in a variable rather than a temporary file: a
# hook that cannot create a scratch directory must still be able to decide, and the payload is one
# short line. Only the session identifier is needed, read with a plain pattern so the hook does not
# depend on a JSON tool being installed. No identifier means no way to stop at one interruption,
# and an unbounded interruption is worse than a missed one.
payload="$(cat 2>/dev/null || true)"
session_id=$(printf '%s' "$payload" |
  sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
[ -n "$session_id" ] || approve "no session id in the payload; declining to interrupt"

# Marked outside the project, so the reminder leaves nothing behind in the user's repository.
marker_dir="${TMPDIR:-/tmp}/lakehouse-agent-skills"
marker="$marker_dir/disclosure-$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_-' '_')"
if [ -f "$marker" ]; then
  approve "already reported once this session"
fi
mkdir -p "$marker_dir" 2>/dev/null || approve "cannot record that this session was told; declining to interrupt"
: >"$marker" 2>/dev/null || approve "cannot record that this session was told; declining to interrupt"

reason="This project has $PROFILE_NOTE but no $DISCLOSURE_NOTE, so a dataset was profiled and \
nothing states what the run did not cover. Before finishing: write $DISCLOSURE_NOTE with the rows \
read of how many, the sheets and files read of how many, every filter that removed data, and what \
could not be determined, then put the load-bearing parts of it in the answer itself. Numbers, not \
adjectives. The honest-data-limits-disclosure skill has the full form. If disclosure genuinely \
does not apply here, say so in one line and finish."

printf '{"decision":"block","reason":"%s"}\n' "$(printf '%s' "$reason" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
echo "stop-disclosure: asked for $DISCLOSURE_NOTE (once this session)" >&2
exit 0
