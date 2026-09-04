#!/usr/bin/env bash
set -euo pipefail
#
# Say, once per session, whether this project has data that nobody has profiled yet.
#
# The pack's whole claim is that profiling comes before charting, and a session that starts in a
# project holding a dozen CSVs and no docs/data/profile.md is exactly where that gets skipped,
# because nothing on screen says the step exists. This is the cheapest possible reminder: it
# counts files, says nothing when there is nothing to say, and never touches the network.
#
# Contract, verified against the documented hook interface rather than recalled: JSON on stdout,
# status on stderr, and exit 0 always, so a reminder can never block somebody's session.

readonly PROFILE_NOTE="docs/data/profile.md"
readonly MAX_DEPTH=3
readonly LIST_LIMIT=5

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
# A stale TMPDIR makes mktemp fail, and an unguarded failure here would end a reminder hook with a
# non-zero status, which the tool reports as an error at the start of every session.
work_dir="$(mktemp -d 2>/dev/null)" || {
  echo "session-start: no writable temporary directory; nothing to say" >&2
  exit 0
}
trap 'rm -rf "$work_dir"' EXIT

emit() {
  # One field, one value, escaped for JSON: a backslash or a quote in a file name would otherwise
  # produce a payload the reader cannot parse.
  local message="$1"
  local escaped
  escaped=$(printf '%s' "$message" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","systemMessage":"%s"}}\n' "$escaped"
}

if [ ! -d "$project_dir" ]; then
  echo "session-start: no project directory at $project_dir" >&2
  exit 0
fi

if [ -f "$project_dir/$PROFILE_NOTE" ]; then
  echo "session-start: $PROFILE_NOTE exists; nothing to say" >&2
  exit 0
fi

# Searched from inside the project so the paths come back relative. Stripping an absolute prefix
# afterwards looks equivalent and is not: the project directory arrives with whatever separator
# the host uses, and on Windows that is a backslash the pattern would never match.
data_files="$work_dir/data_files"
(
  cd "$project_dir" || exit 0
  find . -maxdepth "$MAX_DEPTH" -type f \
    \( -iname '*.csv' -o -iname '*.tsv' -o -iname '*.xlsx' -o -iname '*.xls' \
       -o -iname '*.parquet' -o -iname '*.jsonl' -o -iname '*.ndjson' \) \
    -not -path './.git/*' -not -path './node_modules/*' -not -path './.venv/*' \
    -not -path './venv/*' -not -path '*/__pycache__/*' -not -path './.tox/*' \
    -not -path './.mypy_cache/*' -not -path './.pytest_cache/*'
) >"$data_files" 2>/dev/null || true

count=$(wc -l <"$data_files" | tr -d ' ')
if [ "$count" -eq 0 ]; then
  echo "session-start: no data files found; nothing to say" >&2
  exit 0
fi

names=$(sed -e 's|^\./||' "$data_files" | sort | head -n "$LIST_LIMIT" |
  awk 'NR > 1 { printf ", " } { printf "%s", $0 }')
if [ "$count" -gt "$LIST_LIMIT" ]; then
  names="$names and $((count - LIST_LIMIT)) more"
fi

emit "This project has $count data file(s) and no $PROFILE_NOTE: $names. Before charting, summarising or drawing a conclusion from any of them, invoke the using-lakehouse-skills skill to pick the right stage; it starts with profiling, which is what that missing file records."
echo "session-start: reported $count unprofiled data file(s)" >&2
exit 0
