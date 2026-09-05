#!/usr/bin/env python3
"""Fail the build when a reviewer persona leaves its model or its tools undeclared.

Both defaults are expensive in a way nothing announces.

An agent with no `model` inherits the caller's, so a bounded classifier written to run a small
script over a column list runs on whatever the person happened to be using. Four subagent
invocations in one audited run cost 388,699 tokens, and none of them was a decision anybody made.

An agent with no `tools` gets **all** of them. Every persona here reviews work somebody else did,
and a reviewer that can edit what it reviews is not one. That is a privilege question before it is
a cost question, and these files ship to other people's machines.

So both fields are required, and `Write` and `Edit` are refused outright. `color` is required too,
because the loader's own documentation lists it as required and a field that is optional in
practice is a field that drifts.

Standard library only.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lib.frontmatter import FrontmatterError, parse
from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report

REQUIRED = ("name", "description", "model", "color", "tools")
MODELS = ("inherit", "opus", "sonnet", "haiku")
# A reviewer that can rewrite the artifacts it is reviewing can make its own report come true.
FORBIDDEN_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def validate(layout: Layout) -> Report:
    """Check every persona's frontmatter."""
    report = Report("validate-agents")
    if not layout.agents.is_dir():
        return report

    for path in sorted(layout.agents.glob("*.md")):
        report.checked += 1
        try:
            fields = parse(read_text(path)).data
        except FrontmatterError as error:
            report.error("agents/frontmatter", str(error), path)
            continue

        for field in REQUIRED:
            if not fields.get(field):
                report.error(
                    "agents/missing-field",
                    f"'{field}' is required; without it the loader picks a default nobody chose",
                    path,
                )

        model = str(fields.get("model", "")).strip()
        if model and model not in MODELS:
            report.error(
                "agents/model",
                f"'{model}' is not one of {', '.join(MODELS)}",
                path,
            )

        tools = fields.get("tools")
        if tools is not None:
            if not isinstance(tools, list) or not tools:
                report.error(
                    "agents/tools-shape",
                    '\'tools\' is a non-empty list of tool names, such as ["Read", "Grep"]',
                    path,
                )
            else:
                for forbidden in FORBIDDEN_TOOLS:
                    if forbidden in tools:
                        report.error(
                            "agents/tools-write",
                            f"'{forbidden}' lets a reviewer change the work it is reviewing; "
                            "these personas read and report",
                            path,
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
