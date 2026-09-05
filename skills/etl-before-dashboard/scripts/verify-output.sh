#!/usr/bin/env bash
# Check the artefact a run delivers against the table it claims to describe.
set -euo pipefail
#
# Every checklist in this pack verifies a document the run wrote about its own work: a profile, a
# cleaning log, a model note. None of them opens the file the reader receives. A run can therefore
# tick every box and still ship a page whose headline number counts rows it should have excluded,
# whose header contradicts its own tile, and which is fourteen HTML documents wrapped in one.
# All three of those shipped from a real run with every box ticked.
#
# So this script reads the delivered file. It answers four questions, and it answers them by
# executing rather than by asserting:
#
#   1. Is the page one document?      One doctype, one <html>, no nested <head> or <body>, no
#                                     duplicate charset, nothing left open, and it decodes as UTF-8.
#   2. Is every published number      Each figure in the manifest carries the SQL that produces it.
#      reproducible?                  The SQL runs against the curated table and must return the
#                                     value the page prints.
#   3. Does every number on the       Any number in the page's own text that no figure and no
#      page have an origin?           declared constant accounts for is a number nobody computed.
#   4. Does each figure say what      A figure's population is stated in the manifest and has to
#      it counts?                     appear on the page, because a total that hides an exclusion
#                                     is wrong in the only place the reader looks.
#   5. Did a second library of the    Two charting libraries are two visual languages; two
#      same kind arrive unexplained?  dataframe libraries type the same table twice by different
#                                     rules. Either is allowed, neither is allowed silently.
#   6. Was the page laid out for      A missing viewport meta, a stylesheet with no responsive
#      more than one screen?           mechanism, or a blank title: three absences that say the
#                                      page was built at one width and never named.
#   7. Does the reader land on the    The ranking a page was supposed to have leaves no trace in
#      panel that answers first?      the styling, so it is declared and then checked against
#                                     document order, which is also what a screen reader follows.
#   8. Is the deliverable one page,   Several files each holding one chart are several charts, and
#      with one copy of the library?  the reader does the assembling. Pages are found in the
#                                     project rather than taken from the arguments, and an inline
#                                     script repeated across them is a library shipped N times.
#
# A green run writes a receipt (verification.json beside the manifest) naming what it read and the
# digest of each one; a failing run deletes any receipt that was there. That is what lets something
# else check that this ran at all, rather than taking a checklist box at its word.
#
# Usage:
#   scripts/verify-output.sh --manifest docs/data/figures.json --html dashboard.html
#   scripts/verify-output.sh --manifest docs/data/figures.json --html a.html --html b.html \
#                            --docs docs/data
#
# JSON report on stdout, progress on stderr, non-zero exit on any error. No network. Reads the
# project only; writes nothing outside a temporary directory it removes on exit.
#
# Requires a Python interpreter and the DuckDB Python package. A missing DuckDB is an error, never
# a skipped check: a verification that quietly does not run is the state this script exists to
# refuse.

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# The engine usually lives in the project's own environment rather than on PATH, so the
# interpreter can be named outright. Without it, the first one found is used.
find_python() {
  if [ -n "${VERIFY_OUTPUT_PYTHON:-}" ]; then
    printf '%s\n' "$VERIFY_OUTPUT_PYTHON"
    return 0
  fi
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf 'verify-output: no python interpreter on PATH; set VERIFY_OUTPUT_PYTHON\n' >&2
  return 1
}

PYTHON="$(find_python)"

"$PYTHON" - --work "$WORK" "$@" <<'PYTHON_PROGRAM'
"""Verify a delivered artefact against the curated table it claims to describe."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VOID_ELEMENTS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)
OPAQUE_ELEMENTS = frozenset({"script", "style"})

# Numbers that describe the document rather than the data: dates, clock times, and the bare years
# that appear beside them in a title or a period. Stripped before the page's own numbers are
# collected. A measure that happens to equal a year is declared like any other figure, so the
# only thing this gives up is catching an invented number that lands in 1900-2100 unaccompanied.
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CLOCK_TIME = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
BARE_YEAR = re.compile(r"(?<![\d.,])(?:19|20)\d{2}(?![\d.,])")
NUMBER_TOKEN = re.compile(r"\d[\d.,]*")
SELECT_ONLY = re.compile(r"^\s*(?:WITH|SELECT)\b", re.IGNORECASE)
AGGREGATE_LABEL = re.compile(
    r"^\s*(grand\s+)?(total|subtotal|sum|average|mean|promedio|gran\s+total|totales)\b",
    re.IGNORECASE,
)

# Where a project declares what it depends on. Only the root is read: a lock file lists what was
# resolved, and a transitive dependency is not a decision anybody made.
DEPENDENCY_FILES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "environment.yml",
)

# Grouped into families, because one library and its wrapper are one decision. Naming them is
# detection, not endorsement: the point is to notice a second visual language nobody chose.
CHART_FAMILIES: dict[str, tuple[str, ...]] = {
    "plotly": ("plotly", "plotly.js", "react-plotly.js"),
    "echarts": ("echarts", "echarts-for-react", "pyecharts"),
    "chart.js": ("chart.js", "chartjs", "react-chartjs-2"),
    "matplotlib": ("matplotlib", "seaborn"),
    "vega": ("vega", "vega-lite", "altair", "react-vega"),
    "bokeh": ("bokeh",),
    "highcharts": ("highcharts", "highcharts-react-official"),
    "apexcharts": ("apexcharts", "react-apexcharts"),
    "recharts": ("recharts",),
    "d3": ("d3",),
    "nivo": ("@nivo/core",),
    "amcharts": ("@amcharts/amcharts5",),
    "uplot": ("uplot",),
}
# Any one of these means the page can reflow: a media query, a track that resolves against the
# available space, or a wrapping row. A stylesheet with none of them was written for one width.
RESPONSIVE = re.compile(
    r"@media\b|@container\b|minmax\s*\(|clamp\s*\("
    r"|auto-fit\b|auto-fill\b|flex-wrap\s*:\s*wrap",
    re.IGNORECASE,
)

# An inline script this big is a bundled library rather than page code. Used to notice the same
# library shipped once per page, which is how five charts became twenty megabytes.
RUNTIME_BYTES = 50_000
FRAME_FAMILIES: dict[str, tuple[str, ...]] = {
    "pandas": ("pandas", "geopandas", "modin"),
    "polars": ("polars",),
    "dask": ("dask",),
    "vaex": ("vaex",),
    "cudf": ("cudf",),
    "pyspark": ("pyspark",),
}


class Report:
    """Errors and warnings, rendered as JSON so a CI step can read them."""

    def __init__(self) -> None:
        self.errors: list[dict[str, object]] = []
        self.warnings: list[dict[str, object]] = []
        self.checked = 0

    def error(self, rule: str, message: str, where: str = "", line: int = 0) -> None:
        self.errors.append({"rule": rule, "message": message, "where": where, "line": line})

    def warn(self, rule: str, message: str, where: str = "", line: int = 0) -> None:
        self.warnings.append({"rule": rule, "message": message, "where": where, "line": line})


class PageParser(HTMLParser):
    """Reads a page for the structural faults a browser hides by recovering from them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doctypes: list[int] = []
        self.roots: dict[str, list[int]] = {"html": [], "head": [], "body": []}
        self.charsets: list[int] = []
        self.stack: list[tuple[str, int]] = []
        self.stray_ends: list[tuple[str, int]] = []
        self.opaque_depth = 0
        self.text: list[tuple[int, str]] = []
        self.styles: list[str] = []
        self.title = ""
        self.viewports: list[int] = []
        self.ids: list[tuple[str, int]] = []  # element ids, in document order
        self.inside = ""  # style or title, whose text is collected separately

    @property
    def line(self) -> int:
        return self.getpos()[0]

    def handle_decl(self, decl: str) -> None:
        if decl.lower().startswith("doctype"):
            self.doctypes.append(self.line)

    def _meta(self, attrs: list[tuple[str, str | None]]) -> None:
        names = {name.lower(): (value or "").lower() for name, value in attrs}
        if "charset" in names:
            self.charsets.append(self.line)
        if names.get("name") == "viewport":
            self.viewports.append(self.line)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.roots:
            self.roots[tag].append(self.line)
        for name, value in attrs:
            if name.lower() == "id" and value:
                self.ids.append((value, self.line))
        if tag == "meta":
            self._meta(attrs)
        if tag in ("style", "title"):
            self.inside = tag
        if tag in OPAQUE_ELEMENTS:
            self.opaque_depth += 1
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, self.line))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            self._meta(attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.inside:
            self.inside = ""
        if tag in OPAQUE_ELEMENTS and self.opaque_depth:
            self.opaque_depth -= 1
        if tag in VOID_ELEMENTS:
            self.stray_ends.append((tag, self.line))
            return
        names = [name for name, _ in self.stack]
        if tag not in names:
            self.stray_ends.append((tag, self.line))
            return
        del self.stack[len(names) - 1 - names[::-1].index(tag) :]

    def handle_data(self, data: str) -> None:
        if self.inside == "style":
            self.styles.append(data)
            return
        if self.inside == "title":
            self.title += data
            return
        if self.opaque_depth == 0 and data.strip():
            self.text.append((self.line, data))


def to_number(token: str) -> float | None:
    """Read a printed number, deciding the separators from how the token is grouped."""
    token = token.strip().strip(".,")
    if not token:
        return None
    if "," in token and "." in token:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        token = token.replace("," if decimal == "." else ".", "").replace(decimal, ".")
    elif "," in token:
        groups = token.split(",")
        grouped = len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:])
        token = token.replace(",", "" if grouped else ".")
    elif token.count(".") > 1:
        token = token.replace(".", "")
    try:
        return float(token)
    except ValueError:
        return None


def shown_precision(token: str) -> int:
    """How many decimals the page printed, which is the precision it may be checked to."""
    tail = re.split(r"[.,]", token.strip().strip(".,"))[-1]
    return len(tail) if len(tail) != 3 else 0


def close_enough(printed: float, token: str, declared: float) -> bool:
    """A printed figure matches a computed one when it is the computed one, rounded as shown."""
    return abs(printed - declared) <= 0.5 * 10.0 ** -shown_precision(token)


def page_numbers(parser: PageParser) -> list[tuple[int, str, float]]:
    """Every number in the page's own text, with the line it sits on."""
    found: list[tuple[int, str, float]] = []
    for line, chunk in parser.text:
        stripped = BARE_YEAR.sub(" ", CLOCK_TIME.sub(" ", ISO_DATE.sub(" ", chunk)))
        for match in NUMBER_TOKEN.finditer(stripped):
            value = to_number(match.group())
            if value is not None:
                found.append((line, match.group(), value))
    return found


def check_structure(path: Path, report: Report) -> PageParser | None:
    """One page, one document. Everything here shipped from a real run."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        report.error(
            "artefact/encoding",
            f"does not decode as UTF-8 ({error}); on Windows this is what an unqualified "
            "open(path, 'w') writes, and the accented text is already wrong in the file",
            str(path),
        )
        return None

    parser = PageParser()
    parser.feed(text)
    parser.close()
    report.checked += 1

    for tag, lines in parser.roots.items():
        if len(lines) > 1:
            report.error(
                "artefact/nested-document",
                f"<{tag}> opens {len(lines)} times, at lines {', '.join(map(str, lines))}; a "
                "figure written with a full-document writer was embedded inside the page, so "
                "its <style> rules apply to the real document",
                str(path),
                lines[1],
            )
    if len(parser.doctypes) > 1:
        report.error(
            "artefact/nested-document",
            f"{len(parser.doctypes)} doctypes; a page is one document",
            str(path),
            parser.doctypes[1],
        )
    if len(parser.charsets) > 1:
        report.error(
            "artefact/duplicate-charset",
            f"{len(parser.charsets)} charset declarations; only the first is honoured",
            str(path),
            parser.charsets[1],
        )
    for tag, line in parser.stray_ends:
        report.error("artefact/stray-end-tag", f"</{tag}> closes nothing", str(path), line)
    for tag, line in parser.stack:
        report.error("artefact/unclosed", f"<{tag}> is never closed", str(path), line)
    return parser


def connect(table: Path, work: Path, report: Report):  # noqa: ANN201 - duckdb types are optional
    """Open the curated table read-only, keeping DuckDB's scratch files out of the project."""
    try:
        import duckdb
    except ImportError:
        report.error(
            "figures/no-engine",
            "the DuckDB Python package is not importable, so no published figure could be "
            "recomputed; install it in this project's environment and run again rather than "
            "treating the figures as checked",
        )
        return None
    if not table.is_file():
        report.error("figures/no-table", f"curated table not found: {table}")
        return None
    quoted = str(work).replace("'", "''")
    connection = duckdb.connect()
    connection.execute(f"SET temp_directory = '{quoted}'")
    connection.execute(f"SET home_directory = '{quoted}'")
    reader = "read_csv_auto" if table.suffix.lower() == ".csv" else "read_parquet"
    source = str(table).replace("'", "''")
    connection.execute(f"CREATE VIEW t AS SELECT * FROM {reader}('{source}')")
    return connection


def scalar(connection, sql: str) -> tuple[float | None, str]:  # noqa: ANN001
    """Run one declared query and insist it answers with a single number."""
    rows = connection.execute(sql).fetchall()
    if len(rows) != 1 or len(rows[0]) != 1:
        columns = len(rows[0]) if rows else 0
        return None, f"returned {len(rows)} rows of {columns} columns, not a single value"
    value = rows[0][0]
    if value is None:
        return None, "returned NULL"
    try:
        return float(value), ""
    except (TypeError, ValueError):
        return None, f"returned {value!r}, which is not a number"


def check_figures(
    manifest: dict[str, object], connection, pages: dict[Path, PageParser], report: Report
) -> list[float]:  # noqa: ANN001
    """Recompute every published figure, and require each to say what it counts."""
    declared: list[float] = []
    figures = manifest.get("figures")
    if not isinstance(figures, list) or not figures:
        report.error(
            "figures/none-declared",
            "the manifest declares no figures; a page with numbers on it and nothing "
            "declaring where they came from is the state this check exists to refuse",
        )
        return declared

    page_text = " ".join(
        " ".join(" ".join(chunk.split()) for _line, chunk in parser.text)
        for parser in pages.values()
    ).lower()

    for index, figure in enumerate(figures):
        report.checked += 1
        if not isinstance(figure, dict):
            report.error("figures/shape", f"figure {index} is not an object")
            continue
        label = str(figure.get("label", f"figure {index}"))
        value = figure.get("value")
        sql = figure.get("sql")
        population = figure.get("population")

        if not isinstance(value, (int, float)):
            report.error("figures/shape", f"{label}: 'value' must be the number the page prints")
            continue
        declared.append(float(value))

        if not isinstance(population, str) or not population.strip():
            report.error(
                "figures/no-population",
                f"{label}: 'population' must say which rows this figure covers. A total that "
                "silently includes rows the reader would exclude is wrong on the page, not in "
                "the notes",
            )
        elif " ".join(population.split()).lower() not in page_text:
            report.error(
                "figures/population-not-on-page",
                f"{label}: the page never states its population, {population!r}. A disclosure "
                "that lives only in a manifest has disclosed nothing to the reader",
            )

        if not isinstance(sql, str) or not SELECT_ONLY.match(sql) or ";" in sql:
            report.error(
                "figures/sql",
                f"{label}: 'sql' must be a single SELECT (or WITH) over the view 't', with no "
                "semicolon, that returns exactly the value the page prints",
            )
            continue
        if connection is None:
            continue
        try:
            computed, problem = scalar(connection, sql)
        except Exception as error:  # noqa: BLE001 - the engine's message is the useful part
            report.error("figures/sql-failed", f"{label}: {error}")
            continue
        if computed is None:
            report.error("figures/sql", f"{label}: {problem}")
            continue
        if abs(computed - float(value)) > 0.005:
            report.error(
                "figures/mismatch",
                f"{label}: the page prints {value}, the table answers {computed}",
            )
    return declared


def check_page_numbers(
    pages: dict[Path, PageParser], accounted: list[float], report: Report
) -> None:
    """A number on the page that nothing accounts for is a number nobody computed."""
    for path, parser in pages.items():
        for line, token, value in page_numbers(parser):
            report.checked += 1
            if any(close_enough(value, token, known) for known in accounted):
                continue
            report.error(
                "page/undeclared-number",
                f"{token!r} appears in the page text and no figure or declared constant "
                "produces it; either compute it or remove it",
                str(path),
                line,
            )


def check_aggregate_rows(connection, manifest: dict[str, object], report: Report) -> None:  # noqa: ANN001
    """A spreadsheet's total row read as data doubles a measure and looks like an ordinary row."""
    if connection is None:
        return
    allowed = manifest.get("aggregate_row_exceptions")
    allowed = {str(item).lower() for item in allowed} if isinstance(allowed, list) else set()
    columns = connection.execute("SELECT * FROM t LIMIT 0").description or []
    for column, *_ in columns:
        report.checked += 1
        quoted = column.replace('"', '""')
        rows = connection.execute(
            f'SELECT DISTINCT CAST("{quoted}" AS VARCHAR) FROM t '
            f'WHERE "{quoted}" IS NOT NULL LIMIT 5000'
        ).fetchall()
        for (raw,) in rows:
            if AGGREGATE_LABEL.match(raw or "") and (raw or "").lower() not in allowed:
                report.error(
                    "table/aggregate-row",
                    f'column {column!r} holds {raw!r}, which reads as a summary row carried in '
                    "as data; remove it in the cleaning script, or record it in "
                    "'aggregate_row_exceptions' if it is a real value",
                )


def families_declared(text: str, families: dict[str, tuple[str, ...]]) -> list[str]:
    """Which library families a dependency declaration names."""
    found = []
    for family, aliases in families.items():
        pattern = "|".join(re.escape(alias) for alias in aliases)
        if re.search(rf"(?<![\w.@/-])({pattern})(?![\w.-])", text, re.IGNORECASE):
            found.append(family)
    return found


def check_libraries(project: Path, manifest: dict[str, object], report: Report) -> None:
    """A second library of the same kind is a decision, so it has to have been made.

    Two charting libraries in one project means two visual languages and two sets of defaults,
    and the usual cause is that the second one was the one that came to mind rather than the one
    the destination called for. Two dataframe libraries means the same table is typed twice, by
    different rules. Neither is forbidden here; both have to be explained where somebody reads it.
    """
    text = ""
    for name in DEPENDENCY_FILES:
        path = project / name
        if path.is_file():
            try:
                text += path.read_text(encoding="utf-8", errors="replace") + "\n"
            except OSError:  # noqa: PERF203 - one unreadable manifest must not end the check
                continue
    if not text:
        return

    declared = manifest.get("libraries")
    declared = declared if isinstance(declared, dict) else {}
    for kind, families, field in (
        ("charting", CHART_FAMILIES, "charts_reason"),
        ("dataframe", FRAME_FAMILIES, "dataframe_reason"),
    ):
        report.checked += 1
        found = families_declared(text, families)
        if len(found) < 2:
            continue
        if str(declared.get(field, "")).strip():
            continue
        report.error(
            "project/second-library",
            f"the project declares {len(found)} {kind} libraries ({', '.join(found)}) and "
            f"nothing says what distinguishes them; state it in the manifest as "
            f"libraries.{field}, or drop back to one",
        )


def check_reading_order(
    path: Path, parser: PageParser, manifest: dict[str, object], figures: int, report: Report
) -> None:
    """The ranking a page was supposed to have, checked against the order it actually has.

    Ranking the panels by how directly they answer the page's question is the one layout decision
    that leaves no trace in the styling, so it has always been a box somebody ticks. Declaring the
    order makes it checkable: the panels have to appear in the document in the order they were
    ranked, headline answer first.

    Document order rather than visual order, deliberately. It is what a screen reader announces
    and what the tab key follows, so a page whose headline is visually first and last in the
    markup reads correctly for one audience and not the other.
    """
    layout = manifest.get("layout")
    layout = layout if isinstance(layout, dict) else {}
    declared = layout.get("panels")
    declared = [str(item) for item in declared] if isinstance(declared, list) else []

    if not declared:
        if figures >= 2:
            report.checked += 1
            report.error(
                "layout/no-reading-order",
                f"{figures} figures are published and 'layout.panels' does not say which one the "
                "reader should land on. Rank them by how directly they answer the page's "
                "question, headline answer first, and name their element ids in that order",
                str(path),
            )
        return

    positions = {name: index for index, (name, _line) in enumerate(parser.ids)}
    missing = [name for name in declared if name not in positions]
    report.checked += 1
    if missing:
        report.error(
            "layout/panel-missing",
            f"'layout.panels' names {', '.join(missing)}, which no element on the page carries "
            "as an id",
            str(path),
        )
        return

    for earlier, later in zip(declared, declared[1:]):
        report.checked += 1
        if positions[earlier] > positions[later]:
            report.error(
                "layout/reading-order",
                f"'{later}' comes before '{earlier}' in the document, and the declared ranking "
                f"puts '{earlier}' first. The reader lands on whatever is first",
                str(path),
                parser.ids[positions[later]][1],
            )
            return


def check_categories(path: Path, manifest: dict[str, object], report: Report) -> None:
    """One category, one colour, on every panel that shows it.

    A category is an identity, and colour is how a reader carries that identity from one panel to
    the next. When each panel picks its own palette, the same name is two colours on one screen
    and the reader has no way to know they are the same thing. It is the colour form of the
    disagreement this whole check exists to find.

    What a file can be checked for here is narrow, and worth stating rather than overselling: the
    colours a chart draws with live inside the drawing library's own payload, so nothing outside
    it can confirm which category got which. What is checkable is that the map exists in one place
    and that no two categories were handed the same colour, which makes them indistinguishable
    wherever they appear together. The rest is the skill's rule and the reviewer's eye.
    """
    layout = manifest.get("layout")
    layout = layout if isinstance(layout, dict) else {}
    categories = layout.get("categories")
    if not isinstance(categories, dict) or not categories:
        return

    seen: dict[str, str] = {}
    for name, colour in categories.items():
        report.checked += 1
        value = str(colour).strip().lower()
        if value in seen:
            report.error(
                "categories/shared-colour",
                f"'{name}' and '{seen[value]}' are both {value}, so the two are indistinguishable "
                "wherever they appear together",
                str(path),
            )
        seen[value] = str(name)


def check_layout(path: Path, parser: PageParser, report: Report) -> None:
    """Three things a page laid out for one screen is missing, all of them binary.

    The layout skill asks for weights, flow and narrow-viewport behaviour. None of that can be
    read back out of a file, but its absence can: a page with no viewport meta is rendered by a
    phone at a fixed wide width, which turns off every responsive rule it does have; a page whose
    own stylesheet has no responsive mechanism at all was laid out at one size; and a page with no
    title is the tab, the bookmark and the shared link, all blank. A real run delivered pages
    whose title came from the drawing library's logo.
    """
    report.checked += 1
    if not parser.viewports:
        report.error(
            "layout/no-viewport",
            "no <meta name=\"viewport\">, so a narrow screen renders the page at a fixed wide "
            "width and scales it down; every responsive rule below is inert there",
            str(path),
        )

    report.checked += 1
    css = "\n".join(parser.styles)
    if css.strip() and not RESPONSIVE.search(css):
        report.error(
            "layout/not-responsive",
            "the page's own stylesheet has no media query and no flexible track or wrapping "
            "rule, so it was laid out at one width. State what happens as the viewport narrows, "
            "including any panel hidden on purpose",
            str(path),
        )

    report.checked += 1
    if not parser.title.strip():
        report.error(
            "layout/no-title",
            "no <title>, so the browser tab, the bookmark and any shared link carry nothing. "
            "Name the page after the question it answers",
            str(path),
        )


def delivered_pages(project: Path) -> list[Path]:
    """Every page sitting in the project, found rather than taken on trust.

    The list of pages to check arrives as arguments, so a run that produced five files can pass
    one and be told it is fine. This looks instead.
    """
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
    # Walked to the bottom rather than to a fixed depth: a run that writes its page to
    # output/2026/sales.html is not hiding it, and a check that stops two levels up reports a
    # clean delivery it never looked at.
    found = [
        path
        for path in project.rglob("*")
        if path.is_file()
        and path.suffix.lower() in (".html", ".htm")
        and not any(part in skip for part in path.relative_to(project).parts)
    ]
    return sorted(set(found))


def embedded_runtimes(text: str) -> dict[str, int]:
    """Digest and size of every inline script big enough to be a bundled library."""
    runtimes: dict[str, int] = {}
    for match in re.finditer(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", text, re.S | re.I):
        body = match.group(1)
        if len(body) >= RUNTIME_BYTES:
            runtimes[hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()] = len(body)
    return runtimes


def check_delivery(project: Path, manifest: dict[str, object], report: Report) -> None:
    """One deliverable, and one copy of whatever draws it.

    A dashboard is a page somebody interrogates, so it is one page unless splitting it was a
    decision. Five files each holding one chart are five charts, and a reader comparing them has
    to do the comparing. Worse, each one carried its own copy of the drawing library: a real run
    delivered five pages of four megabytes where the library is the same bytes five times.
    """
    pages = delivered_pages(project)
    if not pages:
        return

    report.checked += 1
    reason = str(manifest.get("pages_reason", "")).strip()
    if len(pages) > 1 and not reason:
        names = ", ".join(path.name for path in pages)
        report.error(
            "delivery/many-pages",
            f"{len(pages)} pages were delivered ({names}) and nothing says why the deliverable "
            "is not one page. A reader given several files does the assembling that the layout "
            "was supposed to do. State the split in the manifest as 'pages_reason', or build one "
            "page",
        )

    seen: dict[str, list[Path]] = {}
    sizes: dict[str, int] = {}
    for path in pages:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:  # noqa: PERF203 - an unreadable page is reported by the structure check
            continue
        for digest, size in embedded_runtimes(text).items():
            seen.setdefault(digest, []).append(path)
            sizes[digest] = size
    for digest, holders in seen.items():
        report.checked += 1
        if len(holders) > 1:
            names = ", ".join(path.name for path in holders)
            report.error(
                "delivery/duplicated-runtime",
                f"the same {sizes[digest] // 1024} KB of inline script is embedded in "
                f"{len(holders)} pages ({names}). Load the library once and let the pages share "
                "it, or deliver one page",
            )


def check_docs(directory: Path, report: Report) -> None:
    """The notes are delivered too, and on Windows they are where the encoding breaks."""
    for path in sorted(directory.rglob("*.md")):
        report.checked += 1
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            report.error(
                "docs/encoding",
                f"does not decode as UTF-8 ({error}); write it with an explicit encoding",
                str(path),
            )


def write_receipt(path: Path, inputs: list[Path], report: Report) -> None:
    """Leave proof on disk that this ran green, or remove the proof that it did not.

    A checklist box saying "run the check and paste the output" is worth exactly the honesty of
    whoever ticks it, which is the same problem the disclosure note had before something looked
    for the file. So a green run writes a receipt naming what it read and the digest of each one,
    and a red run deletes any receipt that was there. What that buys is narrow and worth stating:
    it proves a green run happened over these exact bytes. It does not defeat a forged file, and
    nothing that runs after the fact can.
    """
    if report.errors:
        try:
            path.unlink()
        except OSError:
            pass
        return
    digests = []
    for item in inputs:
        try:
            digests.append({"path": str(item), "sha256": hashlib.sha256(item.read_bytes()).hexdigest()})
        except OSError:  # noqa: PERF203 - an unreadable input is recorded by its absence
            continue
    payload = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": True,
        "checked": report.checked,
        "inputs": digests,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as error:
        report.warn("receipt/unwritable", f"could not write {path}: {error}")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--html", type=Path, action="append", default=[])
    parser.add_argument("--docs", type=Path)
    parser.add_argument("--table", type=Path)
    parser.add_argument(
        "--project",
        type=Path,
        help="project root whose dependency declarations are read for duplicated libraries",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        help="where to record that this ran green (default: verification.json beside the manifest)",
    )
    args = parser.parse_args()

    report = Report()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        report.error("manifest/unreadable", f"{args.manifest}: {error}")
        manifest = {}
    if not isinstance(manifest, dict):
        report.error("manifest/shape", "the manifest must be a JSON object")
        manifest = {}

    pages: dict[Path, PageParser] = {}
    for path in args.html:
        if not path.is_file():
            report.error("artefact/missing", f"no such file: {path}")
            continue
        parsed = check_structure(path, report)
        if parsed is not None:
            pages[path] = parsed
            check_layout(path, parsed, report)
            check_categories(path, manifest, report)
    if not pages and not report.errors:
        report.error("artefact/none", "no page was checked; pass --html")

    table = args.table or Path(str(manifest.get("table", "")))
    connection = connect(table, args.work, report) if str(table) else None
    if not str(table):
        report.error("figures/no-table", "the manifest must name the curated 'table'")

    accounted = check_figures(manifest, connection, pages, report)
    constants = manifest.get("constants")
    if isinstance(constants, list):
        for constant in constants:
            if isinstance(constant, dict) and isinstance(constant.get("value"), (int, float)):
                if not str(constant.get("source", "")).strip():
                    report.error(
                        "constants/no-source",
                        f"the constant {constant['value']} declares no source; a number on the "
                        "page with no origin is the shape of an invented one",
                    )
                accounted.append(float(constant["value"]))

    declared_figures = manifest.get("figures")
    declared_figures = len(declared_figures) if isinstance(declared_figures, list) else 0
    for page, parsed in pages.items():
        check_reading_order(page, parsed, manifest, declared_figures, report)

    check_page_numbers(pages, accounted, report)
    check_aggregate_rows(connection, manifest, report)
    if args.project is not None and args.project.is_dir():
        check_libraries(args.project, manifest, report)
        check_delivery(args.project, manifest, report)
    if args.docs is not None and args.docs.is_dir():
        check_docs(args.docs, report)

    receipt = args.receipt or args.manifest.parent / "verification.json"
    inputs = [args.manifest, *pages.keys()]
    if str(table):
        inputs.append(Path(str(table)))
    write_receipt(receipt, inputs, report)

    result = {
        "ok": not report.errors,
        "checked": report.checked,
        "errors": report.errors,
        "warnings": report.warnings,
        "receipt": str(receipt) if not report.errors else None,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    summary = f"verify-output: {report.checked} checked, {len(report.errors)} error(s)"
    print(summary, file=sys.stderr)
    for entry in report.errors:
        location = f" {entry['where']}:{entry['line']}" if entry["where"] else ""
        print(f"  {entry['rule']}{location}: {entry['message']}", file=sys.stderr)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
PYTHON_PROGRAM
