#!/usr/bin/env python3
"""Fail the build when a reviewer persona leaves its model or its tools undeclared.

Both defaults are expensive in a way nothing announces.

An agent with no `model` inherits the caller's, so a persona whose protocol a small model would
serve runs on whatever the person happened to be using. Four subagent invocations in one audited
run cost 388,699 tokens, and none of them was a decision anybody made. Requiring the field does not
say which model is right; it says the choice has to be one somebody wrote down and can be argued
with, which is what happened to the first version of these declarations.

An agent with no `tools` gets **all** of them. Every persona here reviews work somebody else did,
and a reviewer that can edit what it reviews is not one. That is a privilege question before it is
a cost question, and these files ship to other people's machines.

So both fields are required, and `Write` and `Edit` are refused outright. What that buys is worth
stating exactly, because it is less than it sounds: these personas keep `Bash`, which they need in
order to hash a file or run a query, and a shell can write. Refusing the editing tools removes the
ordinary path, not every path, and the personas say so in their own text. `color` is required too,
because the loader's own documentation lists it as required and a field that is optional in
practice is a field that drifts.

`omitClaudeMd: true` is required for the same reason. Without it a subagent starts with every
instruction file of the project it was called into, and that project is somebody else's: its
instructions were written for doing the work, not for reviewing it, and they are paid for on every
invocation. A reviewer judges the artifacts against its own protocol, so it starts without them.
This was verified rather than read: asked for a codename that only the project's instruction file
stated, a persona without the field quoted it and the same persona with the field answered that
there was none. Only Claude Code reads the key, and the generated copies leave it out.

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
OMIT_PROJECT_INSTRUCTIONS = "omitClaudeMd"


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

        # Absent and empty are different mistakes and get different messages. Reporting an empty
        # `tools: []` as a missing field told the author to add a field that was already there,
        # and did it alongside a second finding about the same line.
        for field in REQUIRED:
            if field not in fields:
                report.error(
                    "agents/missing-field",
                    f"'{field}' is required; without it the loader picks a default nobody chose",
                    path,
                )
            elif not fields[field]:
                report.error(
                    "agents/empty-field",
                    f"'{field}' is present but empty, which the loader reads as absent; "
                    "give it a value or delete the line",
                    path,
                )

        model = str(fields.get("model", "")).strip()
        if model and model not in MODELS:
            report.error(
                "agents/model",
                f"'{model}' is not one of {', '.join(MODELS)}",
                path,
            )

        # An empty list is already reported as an empty field just above, so this only has to
        # catch the wrong shape: one finding per defect, not two.
        tools = fields.get("tools")
        if tools is not None and not isinstance(tools, list):
            report.error(
                "agents/tools-shape",
                '\'tools\' is a list of tool names, such as ["Read", "Grep"]',
                path,
            )
        elif isinstance(tools, list):
            for forbidden in FORBIDDEN_TOOLS:
                if forbidden in tools:
                    report.error(
                        "agents/tools-write",
                        f"'{forbidden}' lets a reviewer change the work it is reviewing; "
                        "these personas read and report",
                        path,
                    )

        # The frontmatter subset has no booleans, so the value arrives as text. Absent and
        # `false` are one mistake with one message: the reviewer loads the caller's instructions.
        if str(fields.get(OMIT_PROJECT_INSTRUCTIONS, "")).strip() != "true":
            report.error(
                "agents/omit-claude-md",
                f"'{OMIT_PROJECT_INSTRUCTIONS}: true' is required; without it the reviewer starts "
                "with the instructions of the project it was called into",
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
