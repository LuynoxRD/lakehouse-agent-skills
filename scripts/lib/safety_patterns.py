"""Patterns that must never appear in content that runs inside someone else's agent.

Skills, hooks, commands and reviewer personas are instructions an agent follows.
A single line telling it to pipe a download into a shell, decode a hidden payload,
read secrets from the environment or write outside the project is a compromise
vector, whatever the surrounding prose says. These patterns fail the build.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lib.report import Severity


@dataclass(frozen=True, slots=True)
class SafetyPattern:
    """One forbidden construct."""

    rule: str
    regex: re.Pattern[str]
    severity: Severity
    message: str


@dataclass(frozen=True, slots=True)
class Match:
    """A pattern hit at a 1-based line."""

    pattern: SafetyPattern
    line: int


PATTERNS: tuple[SafetyPattern, ...] = (
    SafetyPattern(
        "safety/pipe-to-shell",
        re.compile(
            # Anything may sit between the download and the shell, including another pipe:
            # `curl … | tee /tmp/i | bash` executes the download just the same.
            r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b[^\n]*\|\s*"
            r"(sudo\s+)?(ba|z|da|k)?sh\b|\|\s*(iex|Invoke-Expression)\b",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "piping a download into a shell executes unreviewed remote code",
    ),
    SafetyPattern(
        "safety/substituted-download",
        re.compile(
            r"[<$]\(\s*(sudo\s+)?(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "running a download through process or command substitution executes unreviewed "
        "remote code, exactly as a pipe into a shell does",
    ),
    SafetyPattern(
        "safety/eval",
        re.compile(
            # The call form takes no space before the parenthesis, so prose such as
            # "the eval (tier 2) results" is not mistaken for code.
            r"\b(eval|exec)\("
            # Quoted or interpolated arguments: eval "$(cat cmd)", exec $payload.
            r"|\b(eval|exec)[ \t]*[\"'$`]"
            # A bare `eval ssh-agent -s` has no delimiter. Anchor it to a command position and
            # require the argument to look like a command rather than an English word, so
            # "Eval cases live in evals/cases/" stays clean.
            r"|(?:^|[;&|]\s*|`)[ \t]*(eval|exec)[ \t]+\S*[$\"'`/\\-]"
            r"|\b(Invoke-Expression|iex)\s",
            re.IGNORECASE | re.MULTILINE,
        ),
        Severity.ERROR,
        "eval and exec run text as code; write the command out instead",
    ),
    SafetyPattern(
        "safety/base64-decode",
        re.compile(
            # -d, -D, --decode and combined short flags such as -di all decode.
            r"\bbase64\s+(-[a-zA-Z]*[dD][a-zA-Z]*|--decode)"
            r"|\bb64decode\s*\(|FromBase64String|\batob\s*\(",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "decoding a payload hides what will run; ship plain text",
    ),
    SafetyPattern(
        "safety/recursive-delete",
        re.compile(
            r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\s+"
            r"(?!\"?\$\{?(TMP|TMPDIR|tmp|tmpdir|scratch|WORK)|/tmp/|\$\(mktemp)"
            r"|Remove-Item\b[^\n]*-Recurse"
            r"|\bgit\s+clean\b[^\n]*-[a-zA-Z]*[fdx]"
            r"|\bfind\b[^\n]*\s-delete\b"
            r"|\bshutil\.rmtree\s*\(",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "recursive deletes are only allowed on temporary directories the skill created",
    ),
    SafetyPattern(
        "safety/write-outside-project",
        re.compile(
            r"(>>?|\btee\b|\bcp\b|\bmv\b|\bmkdir\b|\btouch\b|Set-Content|Out-File|Add-Content)"
            r"[^\n]*?(~/|\$HOME/|\$\{HOME\}|\"\$HOME|/etc/|/usr/|/var/|/home/|/root/|/opt/"
            r"|%APPDATA%|%USERPROFILE%|\$env:APPDATA|\$env:USERPROFILE|\$env:HOME"
            r"|C:[\\/]Users[\\/])",
            # Windows spellings arrive in any case: `set-content`, `$env:appdata`, `c:\users\`.
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "skills write inside the user's project only",
    ),
    SafetyPattern(
        "safety/home-directory",
        re.compile(
            r"\bPath\.home\s*\(|\bos\.path\.expanduser\s*\(|\bexpanduser\s*\(\s*[\"']~"
            r"|\bos\.environ\s*\[\s*[\"'](HOME|USERPROFILE|APPDATA)[\"']",
        ),
        Severity.ERROR,
        "skills stay inside the user's project and never reach into the home directory",
    ),
    SafetyPattern(
        "safety/env-exfiltration",
        re.compile(
            r"(printenv|os\.environ|os\.getenv|\$\{?[A-Z_]*"
            r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z_]*\}?"
            r"|\$env:[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD))[^\n]*"
            r"(curl|wget|http|requests\.|fetch\(|Invoke-WebRequest|Invoke-RestMethod|nc\s|ncat)",
        ),
        Severity.ERROR,
        "environment variables must never be read and sent anywhere",
    ),
    SafetyPattern(
        "safety/env-secret-read",
        re.compile(
            r"\bprintenv\b|\benv\s*\|\s*grep\b"
            # Subscript and accessor forms both read the variable:
            # os.environ["X"], os.environ.get("X"), os.getenv("X").
            r"|os\.(environ\[|environ\.get\s*\(|getenv\s*\()\s*[\"'][A-Z_]*"
            r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)"
            r"|\$\{?[A-Z_]*(API_KEY|TOKEN|SECRET|PASSWORD)[A-Z_]*\}?",
        ),
        Severity.ERROR,
        "skills do not read secrets from the environment",
    ),
    SafetyPattern(
        "safety/global-install",
        re.compile(
            r"\b(npm|pnpm|yarn)\s+(install|add|i)\b[^\n]*(\s-g\b|--global\b)"
            r"|\bpip3?\s+install\b[^\n]*(--user|--break-system-packages)"
            r"|\bsudo\s+(pip3?|npm|apt|apt-get|brew|dnf|yum|snap)\b"
            r"|\b(brew|choco|winget|scoop|apt|apt-get|dnf|yum|snap)\s+install\b"
            r"|\b(pipx|gem|cargo)\s+install\b|\buv\s+tool\s+install\b|\bgo\s+install\b",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "skills point at the project's own package manager, never at global installers",
    ),
    SafetyPattern(
        "safety/remote-installer",
        re.compile(r"https?://\S+\.(sh|bash|ps1|exe|msi|dmg|pkg|run|bat|cmd)\b", re.IGNORECASE),
        Severity.ERROR,
        "skills never link to installers or scripts to download",
    ),
    SafetyPattern(
        "safety/instruction-override",
        re.compile(
            # The object must belong to the agent, not to the data. "Override the type
            # inference rules" is ordinary cleaning guidance; "override the safety rules" is
            # not, and the qualifier is what separates them.
            r"\b(ignore|disregard|forget|override|bypass)\b(?:\W+\w+){0,3}\W+"
            r"(system|safety|security|previous|prior|above|earlier|your)\b(?:\W+\w+){0,2}\W*"
            r"(instructions?|prompts?|rules?|guidelines?|guardrails?|restrictions?|policies)\b"
            # "disregard everything the user told you earlier": no keyword, but the object is
            # the conversation itself.
            r"|\b(ignore|disregard|forget)\b(?:\W+\w+){0,4}\W+(told|said|asked|instructed)"
            r"\s+(you|us|the\s+agent)\b",
            re.IGNORECASE,
        ),
        Severity.ERROR,
        "a skill that tells the agent to set aside its instructions is an injection, not guidance",
    ),
    SafetyPattern(
        "safety/invisible-characters",
        re.compile(r"[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\ufeff\u00ad]"),
        Severity.ERROR,
        "zero-width or invisible characters can hide text from reviewers",
    ),
)

# Documentation hosts a skill may cite. A network *command* is flagged regardless;
# a plain link to one of these hosts is fine.
ALLOWED_HOSTS = frozenset(
    {
        "github.com",
        "docs.github.com",
        "duckdb.org",
        "openpyxl.readthedocs.io",
        "pandas.pydata.org",
        "arrow.apache.org",
        "parquet.apache.org",
        "iceberg.apache.org",
        "delta.io",
        "hudi.apache.org",
        "www.w3.org",
        "www.iso.org",
        "en.wikipedia.org",
        "datatracker.ietf.org",
        "docs.python.org",
        "pypi.org",
        "www.npmjs.com",
        "code.claude.com",
        "agentskills.io",
        "echarts.apache.org",
        "www.chartjs.org",
        "d3js.org",
        "plotly.com",
        "matplotlib.org",
        "vega.github.io",
        "observablehq.com",
        "www.itu.int",
        "unicode.org",
        "www.unicode.org",
        "support.microsoft.com",
        "learn.microsoft.com",
        "sqlite.org",
        "www.postgresql.org",
        "www.rfc-editor.org",
        "example.com",
        "localhost",
    }
)

# Userinfo before the host is skipped deliberately: "https://github.com@evil.example.net/x"
# is served by evil.example.net, and reading the part before the "@" as the host would let an
# allowlisted name launder any destination.
_URL_RE = re.compile(r"https?://(?:[^/\s@]*@)?([A-Za-z0-9.-]+)")
_NETWORK_COMMAND_RE = re.compile(
    r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm|requests\.(get|post|put)"
    r"|urllib\.request|urlopen|httpx\.|aiohttp|fetch\s*\()",
    re.IGNORECASE,
)

NETWORK_COMMAND_RULE = "safety/network-command"
UNKNOWN_HOST_RULE = "safety/unknown-host"


def scan_text(text: str) -> list[Match]:
    """Every forbidden construct in *text*, with 1-based line numbers."""
    matches: list[Match] = []
    for number, line in enumerate(text.split("\n"), start=1):
        matches.extend(Match(pattern, number) for pattern in PATTERNS if pattern.regex.search(line))
    return matches


def network_commands(text: str) -> list[int]:
    """Lines that invoke a network client."""
    return [
        number
        for number, line in enumerate(text.split("\n"), start=1)
        if _NETWORK_COMMAND_RE.search(line)
    ]


def unknown_hosts(text: str) -> list[tuple[str, int]]:
    """Hosts linked from *text* that are not on the documentation allowlist."""
    found: list[tuple[str, int]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        for match in _URL_RE.finditer(line):
            host = match.group(1).lower().rstrip(".")
            if host not in ALLOWED_HOSTS:
                found.append((host, number))
    return found
