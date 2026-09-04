"""Findings, reports and exit codes shared by every validator."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    """How a finding affects the build: errors fail it, warnings and infos do not."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


_ANNOTATION_KIND = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "notice",
}


@dataclass(frozen=True, slots=True)
class Finding:
    """One observation about one place in the repository."""

    severity: Severity
    rule: str
    message: str
    path: Path | None = None
    line: int | None = None

    def relative_path(self, root: Path | None = None) -> str | None:
        """POSIX path relative to *root* when possible, the absolute path otherwise."""
        if self.path is None:
            return None
        if root is not None:
            try:
                return self.path.relative_to(root).as_posix()
            except ValueError:
                pass
        return self.path.as_posix()

    def location(self, root: Path | None = None) -> str:
        """Return ``path:line`` relative to *root* when possible, or an empty string."""
        text = self.relative_path(root)
        if text is None:
            return ""
        if self.line is not None:
            text = f"{text}:{self.line}"
        return text

    def render(self, root: Path | None = None) -> str:
        """Render a human-readable line."""
        location = self.location(root)
        prefix = f"{location}: " if location else ""
        return f"{prefix}{self.severity.value}[{self.rule}] {self.message}"

    def render_annotation(self, root: Path | None = None) -> str:
        """Render a GitHub Actions workflow command so the finding shows up inline."""
        properties: list[str] = []
        shown = self.relative_path(root)
        if shown is not None:
            properties.append(f"file={shown}")
        if self.line is not None:
            properties.append(f"line={self.line}")
        kind = _ANNOTATION_KIND[self.severity]
        header = f"::{kind} {','.join(properties)}" if properties else f"::{kind}"
        message = self.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        return f"{header}::[{self.rule}] {message}"


def _sort_key(finding: Finding) -> tuple[str, int, int, str]:
    path = finding.path.as_posix() if finding.path is not None else ""
    line = finding.line if finding.line is not None else 0
    severity_rank = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}[finding.severity]
    return (path, line, severity_rank, finding.rule)


@dataclass(slots=True)
class Report:
    """Findings collected by one tool, plus the count of units it examined."""

    tool: str
    findings: list[Finding] = field(default_factory=list)
    checked: int = 0

    def add(
        self,
        severity: Severity,
        rule: str,
        message: str,
        path: Path | None = None,
        line: int | None = None,
    ) -> None:
        """Record a finding."""
        self.findings.append(Finding(severity, rule, message, path, line))

    def error(
        self, rule: str, message: str, path: Path | None = None, line: int | None = None
    ) -> None:
        """Record a finding that fails the build."""
        self.add(Severity.ERROR, rule, message, path, line)

    def warning(
        self, rule: str, message: str, path: Path | None = None, line: int | None = None
    ) -> None:
        """Record a finding that needs attention but does not fail the build."""
        self.add(Severity.WARNING, rule, message, path, line)

    def info(
        self, rule: str, message: str, path: Path | None = None, line: int | None = None
    ) -> None:
        """Record an informational note."""
        self.add(Severity.INFO, rule, message, path, line)

    def extend(self, findings: list[Finding]) -> None:
        """Append findings produced elsewhere."""
        self.findings.extend(findings)

    @property
    def errors(self) -> list[Finding]:
        """Findings with error severity."""
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        """Findings with warning severity."""
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        """True when nothing fails the build."""
        return not self.errors

    @property
    def exit_code(self) -> int:
        """Process exit code: 1 when any error exists, otherwise 0."""
        return 0 if self.ok else 1

    def summary(self) -> str:
        """One-line summary used as the last line of every report."""
        verdict = "OK" if self.ok else "FAIL"
        return (
            f"{self.tool}: {self.checked} checked, {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s): {verdict}"
        )

    def render(self, root: Path | None = None, *, github: bool | None = None) -> str:
        """Render every finding, GitHub annotations when running in Actions, then the summary."""
        if github is None:
            github = os.environ.get("GITHUB_ACTIONS") == "true"
        ordered = sorted(self.findings, key=_sort_key)
        lines = [f.render(root) for f in ordered]
        if github:
            lines.extend(
                f.render_annotation(root) for f in ordered if f.severity is not Severity.INFO
            )
        lines.append(self.summary())
        return "\n".join(lines)

    def to_dict(self, root: Path | None = None) -> dict[str, object]:
        """Serialize for JSON result files."""
        findings: list[dict[str, object]] = []
        for finding in sorted(self.findings, key=_sort_key):
            item = asdict(finding)
            item["severity"] = finding.severity.value
            item["path"] = finding.relative_path(root)
            findings.append(item)
        return {
            "tool": self.tool,
            "checked": self.checked,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "ok": self.ok,
            "findings": findings,
        }
