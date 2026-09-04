#!/usr/bin/env bash
# Runs the whole local gate, in the same order CI runs it, before every push.
#
#   bash scripts/ci-local.sh            # everything
#   bash scripts/ci-local.sh --no-sync  # skip `uv sync` when the environment is already current
#
# Every step runs even when an earlier one fails, so one pass shows every problem. Steps whose
# tool is not installed locally (actionlint, trivy, semgrep on Windows) are reported as SKIPPED;
# CI is the hard gate for those.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

SYNC=1
for arg in "$@"; do
  case "$arg" in
    --no-sync) SYNC=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

declare -a NAMES=()
declare -a RESULTS=()
FAILED=0

record() {
  NAMES+=("$1")
  RESULTS+=("$2")
  if [ "$2" = "FAIL" ]; then FAILED=1; fi
}

step() {
  local name="$1"; shift
  printf '\n==> %s\n' "$name"
  if "$@"; then
    record "$name" "PASS"
  else
    record "$name" "FAIL"
  fi
}

# optional_step NAME PROBE COMMAND...: PROBE is a function name that succeeds when the tool is
# usable locally. No string evaluation happens; probes are plain functions defined below.
optional_step() {
  local name="$1" probe="$2"; shift 2
  if ! "$probe" >/dev/null 2>&1; then
    printf '\n==> %s\n    SKIPPED (tool not available locally; CI enforces it)\n' "$name"
    record "$name" "SKIP"
    return
  fi
  step "$name" "$@"
}

have_gitleaks()   { command -v gitleaks >/dev/null 2>&1; }
have_actionlint() { command -v actionlint >/dev/null 2>&1; }
have_trivy()      { command -v trivy >/dev/null 2>&1; }
have_claude()     { command -v claude >/dev/null 2>&1; }
have_semgrep()    { uv run --frozen semgrep --version >/dev/null 2>&1; }

pinned_gitleaks_version() {
  sed -n 's/^[[:space:]]*GITLEAKS_VERSION:[[:space:]]*"\{0,1\}\([0-9][0-9.]*\)"\{0,1\}.*/\1/p' \
    .github/workflows/gitleaks.yml | head -n 1
}

gitleaks_version_check() {
  local pinned installed
  pinned="$(pinned_gitleaks_version)"
  installed="$(gitleaks version 2>/dev/null | head -n 1 | sed 's/^v//')"
  if [ -z "$pinned" ]; then
    echo "could not read GITLEAKS_VERSION from .github/workflows/gitleaks.yml" >&2
    return 1
  fi
  if [ "$pinned" != "$installed" ]; then
    echo "gitleaks $installed is installed but CI pins $pinned; install the pinned version" >&2
    return 1
  fi
  echo "gitleaks $installed matches the CI pin"
}

vendor_neutrality_all() {
  uv run --frozen python scripts/check_vendor_neutrality.py --tree --history --root .
}

command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 2; }
# The secret scan is part of what this script promises to run, so a missing gitleaks is a
# hard stop rather than a skipped step that still prints OK.
have_gitleaks || {
  echo "gitleaks is required; install the version pinned in .github/workflows/gitleaks.yml" >&2
  exit 2
}

if [ "$SYNC" = 1 ]; then
  step "uv sync --locked --extra dev" uv sync --locked --extra dev
fi

step "ruff check"            uv run --frozen ruff check .
step "ruff format --check"   uv run --frozen ruff format --check .
step "mypy --strict"         uv run --frozen mypy
step "pytest"                uv run --frozen pytest

step "validate_skills"           uv run --frozen python scripts/validate_skills.py
step "validate_commands"         uv run --frozen python scripts/validate_commands.py
step "validate_versions"         uv run --frozen python scripts/validate_versions.py
step "validate_reference_links"  uv run --frozen python scripts/validate_reference_links.py
step "validate_artifact_paths"   uv run --frozen python scripts/validate_artifact_paths.py
step "validate_fixtures"         uv run --frozen python scripts/validate_fixtures.py
step "validate_skill_safety"     uv run --frozen python scripts/validate_skill_safety.py
step "run_evals (tier 2)"        uv run --frozen python scripts/run_evals.py

step "gitleaks version pin" gitleaks_version_check
step "gitleaks (history)"   gitleaks git --redact --exit-code 1 --no-banner .
step "gitleaks (worktree)"  gitleaks dir --redact --exit-code 1 --no-banner .

step "vendor neutrality (tree + history)" vendor_neutrality_all

step "zizmor" uv run --frozen zizmor --persona regular .github/workflows

optional_step "actionlint" have_actionlint actionlint -color
optional_step "trivy fs"   have_trivy trivy fs --scanners vuln,secret --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 .
optional_step "semgrep"    have_semgrep \
  uv run --frozen semgrep scan --config p/default --config p/security-audit --config p/python \
  --metrics=off --error --severity ERROR .
optional_step "claude plugin validate" have_claude claude plugin validate . --strict

printf '\n%-40s %s\n' "step" "result"
printf '%-40s %s\n' "----------------------------------------" "------"
for i in "${!NAMES[@]}"; do
  printf '%-40s %s\n' "${NAMES[$i]}" "${RESULTS[$i]}"
done

if [ "$FAILED" = 1 ]; then
  echo
  echo "ci-local: FAIL"
  exit 1
fi
echo
echo "ci-local: OK"
