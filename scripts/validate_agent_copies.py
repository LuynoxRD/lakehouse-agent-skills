#!/usr/bin/env python3
"""Fail the build when a per-tool copy of a reviewer persona is missing, extra, or drifted.

The files under `.opencode/agent/`, `.cursor/agents/`, `.gemini/agents/` and `.codex/agents/` are
what a person
using those tools actually loads. `agents/` is the source; `scripts/sync_agents.py` writes the
copies. This checks them, and the three ways they disagree are each a real failure rather than
untidiness:

* **A persona has no copy for a tool.** It reviews work in one tool and is silently absent in the
  next, which is discovered by nobody, because an agent that does not exist raises nothing.
* **A copy belongs to no persona.** A reviewer deleted here goes on running there, with whatever
  protocol it had before it was removed.
* **A copy differs from what its source would generate.** Two versions of one reviewer exist and
  only one of them was corrected. Since the copies are also where the no-editing guarantee is
  expressed, in four different fields, a drifted copy is how a reviewer quietly gets write access
  back.

Standard library only.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lib.repo import Layout, add_root_argument, configure_output
from lib.report import Report
from sync_agents import existing, plan


def validate(layout: Layout) -> Report:
    """Compare every per-tool copy against what its source would produce."""
    report = Report("validate-agent-copies")
    wanted = plan(layout, report)
    if report.errors:
        return report

    for path, content in sorted(wanted.items()):
        report.checked += 1
        if not path.is_file():
            report.error(
                "agent-copy/missing",
                "no copy for this tool; run scripts/sync_agents.py and commit the result",
                path,
            )
            continue
        if path.read_text(encoding="utf-8") != content:
            report.error(
                "agent-copy/drifted",
                "this copy is not what its source generates, so two versions of one reviewer "
                "exist; run scripts/sync_agents.py",
                path,
            )

    for stray in sorted(existing(layout) - set(wanted)):
        report.error(
            "agent-copy/orphan",
            "no persona in agents/ owns this copy, so it runs where nothing maintains it",
            stray,
        )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = validate(layout)
    print(report.render(layout.root))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
