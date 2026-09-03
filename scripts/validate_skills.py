#!/usr/bin/env python3
"""Validate every skill under skills/ against the anatomy rules (Tier 1).

Rules are implemented in lib/skill_lint.py and documented in docs/skill-anatomy.md.
Exit code 1 when any error is found.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lib.repo import Layout, add_root_argument
from lib.skill_lint import lint_catalog


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = lint_catalog(layout)
    print(report.render(layout.root))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
