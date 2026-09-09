#!/usr/bin/env bash
set -euo pipefail
#
# Refuse to end a turn whose evidence is missing: a dataset profiled and never disclosed, or an
# artefact check that a checklist says was run and that nothing on disk agrees was.
#
# Every other nudge in this pack is a suggestion the model may decline: a description it may not
# read, a checklist it may tick without executing, a router it may never load. That is a ceiling
# of the mechanism rather than a gap in this pack, and it is the same everywhere skills are
# discovered by description. One event escapes it. A Stop hook runs after the turn is written and
# can send it back, which makes it the only place in this repository where a step is enforced
# instead of requested.
#
# It checks three facts, all of them cheap and none of them the model's word — two on disk and
# one in the transcript the event names:
#
#   * docs/data/profile.md exists and docs/data/disclosure.md does not. A dataset was profiled and
#     nothing states what the run did not cover.
#   * docs/data/figures.json exists and docs/data/verification.json is missing or older than the
#     inputs. Figures were declared and the artefact check either never ran or ran before the
#     files it was supposed to check. verify-output.sh writes that receipt only on a green run and
#     deletes it on a red one.
#   * docs/data/figures.json exists and the session's transcript, which the event names as
#     transcript_path, carries no invocation of the skills that own how a page reads. A page was
#     declared and nobody applied to it the rules for where its panels sit, what its colours
#     encode, or how its type, spacing, alignment and ink rank the information. The persona that
#     reviews the page cannot see this — a subagent starts with no view of the conversation, by
#     the documented design — so the transcript is the only record of which skills ran.
#
# What the receipt proves is narrow and worth being honest about: that a green run happened over
# the current bytes. A forged receipt would still pass, and nothing checking after the fact can
# close that. It closes the two cases that actually occur, which are never running the check and
# running it and then changing the file.
#
# It fires narrowly on purpose. Blocking a turn that should have ended is worse than missing one
# that should not have, so anything unexpected ends in approval, and a session is sent back at
# most once.
#
# Contract, read from the documented hook interface rather than recalled: a Stop hook decides with
# {"decision": "block", "reason": ...} on stdout, the reason is what the model is told, and exit 0
# leaves the turn alone. Claude Code only; no other tool runs this file.

readonly PROFILE_NOTE="docs/data/profile.md"
readonly DISCLOSURE_NOTE="docs/data/disclosure.md"
readonly FIGURES_NOTE="docs/data/figures.json"
readonly RECEIPT_NOTE="docs/data/verification.json"
readonly PAGE_SKILLS="dashboard-layout-by-widget-mix dashboard-color-and-visual-hierarchy dashboard-visual-craft"
readonly MAX_DEPTH=3

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

approve() {
  echo "stop-evidence: $1" >&2
  exit 0
}

[ -d "$project_dir" ] || approve "no project directory at $project_dir"

# The event payload arrives on stdin, and is held in a variable rather than a temporary file: a
# hook that cannot create a scratch directory must still be able to decide, and the payload is one
# short line. Two fields are read from it with a plain pattern, so the hook does not depend on a
# JSON tool being installed: the session identifier, and the path of the session's transcript.
payload="$(cat 2>/dev/null || true)"

missing=""
add() {
  if [ -n "$missing" ]; then
    missing="$missing "
  fi
  missing="$missing$1"
}

if [ -f "$project_dir/$PROFILE_NOTE" ] && [ ! -f "$project_dir/$DISCLOSURE_NOTE" ]; then
  add "A dataset was profiled and there is no $DISCLOSURE_NOTE, so nothing states what the run did \
not cover. Write it with the rows read of how many, the sheets and files read of how many, every \
filter that removed data, and what could not be determined, then put the load-bearing parts in the \
answer itself. Numbers, not adjectives; the honest-data-limits-disclosure skill has the full form."
fi

if [ -f "$project_dir/$FIGURES_NOTE" ]; then
  receipt="$project_dir/$RECEIPT_NOTE"
  if [ ! -f "$receipt" ]; then
    add "Figures are declared in $FIGURES_NOTE and there is no $RECEIPT_NOTE, which is the receipt \
verify-output.sh writes only when it finishes with zero errors. Run it and read what it says."
  else
    # Anything the check was meant to read that is newer than the receipt means the receipt
    # describes a file that no longer exists in that form. Compared by modification time, which
    # needs no parsing and no hashing tool, and searched from inside the project so the paths come
    # back relative by construction. The notes are in the list because the receipt now records
    # their digests: an audit found that editing one after a green run left the receipt reading as
    # intact, which is an absence being taken for a pass.
    newer=$(
      cd "$project_dir" 2>/dev/null || exit 0
      find . -maxdepth "$MAX_DEPTH" -type f \
        \( -iname '*.html' -o -iname '*.htm' -o -path "./$FIGURES_NOTE" \
           -o -path './docs/data/*.md' \) \
        -newer "$RECEIPT_NOTE" \
        -not -path './.git/*' -not -path './node_modules/*' -not -path './.venv/*' \
        -not -path './venv/*' -not -path '*/__pycache__/*' 2>/dev/null | head -n 3
    )
    if [ -n "$newer" ]; then
      add "$RECEIPT_NOTE is older than $(printf '%s' "$newer" | tr '\n' ' '), so the artefact check \
last passed against files that have changed since. Run verify-output.sh again."
    fi
  fi
fi

# Third: a page was declared and the skills that own how a page reads never ran. The persona that
# reviews the page cannot see this — a subagent starts with no view of the conversation, by the
# documented design — so the transcript the event names is the only record of which skills were
# invoked. What is matched is the tool call as the transcript serialises it, never the bare name,
# so this hook's own reason, which reaches the transcript as a message, can never count as an
# invocation. The transcript is written asynchronously and can lag the current turn, which is one
# more reason to interrupt once and to let the model answer in a line.
if [ -f "$project_dir/$FIGURES_NOTE" ]; then
  transcript=$(printf '%s' "$payload" |
    sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1 |
    sed -e 's/\\\\/\//g' -e 's/\\/\//g')
  if [ -n "$transcript" ] && [ -r "$transcript" ]; then
    unseen=""
    for skill in $PAGE_SKILLS; do
      if ! grep -q -E "\"name\":[[:space:]]*\"Skill\".*\"skill\":[[:space:]]*\"[^\"]*$skill\"" \
        "$transcript" 2>/dev/null; then
        unseen="$unseen $skill"
      fi
    done
    if [ -n "$unseen" ]; then
      add "Figures are declared in $FIGURES_NOTE, so a page was written, and this session's transcript \
shows no invocation of:$unseen. Those skills own how a page reads once it is placed — where the \
panels sit, what the colours encode, the type scale, the spacing, the alignment and the ink that is \
not data — and a page they never saw has been reviewed for none of it. Invoke each one on the file \
that was written, not on the plan. If one did run and the transcript has not caught up, say so in \
one line and finish."
    fi
  else
    echo "stop-evidence: no readable transcript named in the payload; the skill check is skipped" >&2
  fi
fi

[ -n "$missing" ] || approve "the evidence this looks for is present"

session_id=$(printf '%s' "$payload" |
  sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
[ -n "$session_id" ] || approve "no session id in the payload; declining to interrupt"

# Marked outside the project, so the reminder leaves nothing behind in the user's repository.
marker_dir="${TMPDIR:-/tmp}/lakehouse-agent-skills"
marker="$marker_dir/evidence-$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_-' '_')"
if [ -f "$marker" ]; then
  approve "already reported once this session"
fi
mkdir -p "$marker_dir" 2>/dev/null || approve "cannot record that this session was told; declining to interrupt"
: >"$marker" 2>/dev/null || approve "cannot record that this session was told; declining to interrupt"

reason="Before finishing: $missing If a step genuinely does not apply here, say so in one line and \
finish."

printf '{"decision":"block","reason":"%s"}\n' "$(printf '%s' "$reason" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
echo "stop-evidence: sent the turn back once this session" >&2
exit 0
