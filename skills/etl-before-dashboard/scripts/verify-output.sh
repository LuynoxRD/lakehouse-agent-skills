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

# Both streams carry text taken from the page: a figure's label, the population it covers, the
# sentence a rule quotes back. On Windows those default to the console's own code page, so a page
# in any language with an accent in it produced bytes the reader's terminal could not decode --
# measured here as an invalid UTF-8 sequence on stderr, and one bad label away from the same on
# the JSON that other tools parse. Named once, before anything is written.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):  # a replaced stream may not support it; not fatal
        pass

VOID_ELEMENTS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)
OPAQUE_ELEMENTS = frozenset({"script", "style"})
# Text a page presents as a specimen rather than as its own copy. A SQL snippet in <code> is
# meant to be read as code, so the language and path families below skip it. The structural
# families do not: a document nested inside <pre> is still a nested document.
VERBATIM_ELEMENTS = frozenset({"code", "pre", "samp", "kbd"})

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

# This pack's own vocabulary for the pipeline that built the page, as opposed to the page itself.
# A reader who opens the delivered file did not necessarily run PROFILE through DISCLOSE, and has
# no reason to know what any of these mean; that detail belongs in the reply that hands the page
# over, or in docs/data beside the curated table. Stage names are matched in capitals only, so an
# ordinary word in ordinary case (a product literally called "Model") never trips this.
STAGE_WORD = re.compile(
    r"(?<![\w-])(PROFILE|CLEAN|MODEL|QUERY|VISUALIZE|ASSEMBLE|NARRATE|DISCLOSE|REDACT)(?![\w-])"
)
BUCKET_WORD = re.compile(r"(?<![\w-])bucket(?![\w-])", re.IGNORECASE)
PIPELINE_ARTEFACT_NAMES = (
    "cleaning-log.md",
    "profile.md",
    "model.md",
    "disclosure.md",
    "insights.md",
    "figures.json",
    "verification.json",
    "verify-output.sh",
)
ARTEFACT_NAME = re.compile(
    "(?:" + "|".join(re.escape(name) for name in PIPELINE_ARTEFACT_NAMES) + ")", re.IGNORECASE
)

# The six languages this can tell apart, and the words that tell them apart. Every word that any
# two of them share has been removed, which is why the lists are short: what survives is only what
# discriminates. Accents are part of that -- Spanish writes "tambien" as "también" and Portuguese
# writes "também" -- so text is compared with its accents intact, which is one more reason both
# streams are UTF-8. The sets are asserted pairwise disjoint by the test suite, because a word that
# leaked into two of them would report every page carrying it as bilingual.
LANGUAGE_MARKERS: dict[str, frozenset[str]] = {
    "English": frozenset(
        {
            "the", "and", "with", "from", "this", "that", "these", "those", "which", "have",
            "has", "been", "were", "they", "their", "there", "about", "after", "before",
            "between", "during", "into", "over", "only", "other", "more", "most", "than",
            "then", "when", "where", "while", "because", "should", "would", "could", "every",
            "each", "both", "such", "through", "without", "within", "against",
        }
    ),
    "Spanish": frozenset(
        {
            "los", "las", "pero", "también", "muy", "aunque", "hacia", "ellos", "nuestro",
            "según", "siempre", "están", "estaba", "fueron", "mismo", "cualquier", "alguna",
            "ninguna", "entonces", "desde",
        }
    ),
    "Portuguese": frozenset(
        {
            "não", "são", "você", "mas", "muito", "então", "pelo", "pela", "porém", "também",
            "seus", "suas", "nós", "têm", "ainda", "apenas", "mesmo", "foram",
        }
    ),
    "French": frozenset(
        {
            "les", "des", "une", "dans", "avec", "pour", "mais", "cette", "ces", "nous",
            "vous", "sont", "aussi", "très", "chaque", "toujours", "depuis", "alors", "leur",
            "cela", "être", "plus",
        }
    ),
    "Italian": frozenset(
        {
            "gli", "degli", "delle", "della", "negli", "nella", "nelle", "sono", "anche",
            "perché", "molto", "questo", "questa", "quello", "dopo", "però", "essere",
            "hanno", "loro", "così",
        }
    ),
    "German": frozenset(
        {
            "der", "das", "und", "nicht", "mit", "für", "auch", "aber", "oder", "eine",
            "einen", "sind", "wird", "werden", "durch", "über", "zwischen", "haben", "sich",
            "noch", "schon", "wenn", "dass", "kann", "auf", "aus", "bei",
        }
    ),
}
# Two distinct markers, not one. A single foreign word on a page is a brand, a loan word or a
# proper noun; two different function words are a sentence somebody forgot to carry over.
MIN_LANGUAGE_MARKERS = 2
# What <html lang> is saying, for the six above. A page that declares its language has
# already answered which text is the leftover, and counting words to guess it can answer the
# opposite: a Spanish page carrying two English paragraphs has more English function words in
# it than Spanish ones, and would be reported as an English page with a Spanish accident.
LANGUAGE_CODES = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "it": "Italian",
    "de": "German",
}
WORD_TOKEN = re.compile(r"[^\W\d_]+")

# A path into the project, printed where a reader can see it. The reader cannot open it, has no
# reason to know how the folder is arranged, and did not ask for the plumbing -- the same argument
# the stage names above rest on, one level down. Matched two ways only, so that "and/or", "24/7"
# and an ordinary decimal stay out of it: something ending in a data extension, or something
# starting at one of the two directories this pack writes into.
DATA_SUFFIX = (
    "csv|tsv|parquet|parq|xlsx|xlsm|xlsb|xls|json|jsonl|ndjson|md|db|duckdb|sqlite|feather|pkl"
)
DELIVERY_PATH = re.compile(
    r"(?<![\w./-])(?:[\w.-]+/)*[\w.-]+\.(?:" + DATA_SUFFIX + r")(?![\w-])"
    r"|(?<![\w./-])(?:data|docs)/[\w.-]+(?:/[\w.-]+)*/?",
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

# This script reads a file. It never opens a browser, so everything below is outside what a green
# result means, and it is printed on every run rather than left for somebody to infer. A page that
# passed every check here shipped with axis labels rotated on their side and two segment labels
# overlapping each other, and the run reported zero errors and moved on.
NOT_VERIFIED = (
    "whether any text is clipped, truncated or overlapping another element",
    "whether the page is centred, or sits against one edge with dead space beside it",
    "whether a chart's own labels stay legible when its container narrows",
    "how anything looks at any viewport width; no width was rendered",
    "whether a colour actually reached the category the manifest assigned it to",
    "whether a control that exists in the markup is discoverable by a reader",
    "whether the destination was asked of a person or decided for them; only what was recorded",
    "whether the page reads as a business answer beyond the specific stage names, artefact "
    "filenames and the word 'bucket' this checks for; a sentence can still report on the pipeline "
    "without using any of them",
    "which language the page is in, or whether it is the language its reader wrote in; only "
    "whether markers of more than one of the six it knows sit in the same page text",
    "any language whose markers it does not carry, and anything inside <code>, <pre> or the "
    "<title>, none of which is read for language or for paths",
)

# The notes a reviewer treats as the evidence behind a claim. They sit beside the manifest and
# this script never parses them, but it does hash them, because the receipt is read as the index
# of the work: a receipt that named only the manifest, the pages and the table let any of these
# four be rewritten after a green run with nothing recording that it happened, while the receipt
# still read as intact. Hashing them costs one read each and closes that.
RECORDED_NOTES = ("profile.md", "cleaning-log.md", "model.md", "disclosure.md")

# A container with a maximum width and nothing centring it sits against the left edge with the
# remaining space beside it. Real, and found in a delivered page: `max-width: 1280px` in a 1600px
# viewport left roughly 300px of nothing on the right.
#
# Known limit, and the reason the manifest has an opt-out rather than this having a cleverer
# regex: centring can come from the parent. A flex or grid ancestor with `justify-content: center`
# centres this element without any declaration appearing in its own rule, and no amount of reading
# one rule at a time can see that, because resolving it needs the document tree and the cascade.
# So this catches the common shape, and `layout.left_aligned` records the other one as a decision.
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
BOUNDED_WIDTH = re.compile(r"max-width\s*:\s*[\d.]+\s*(px|rem|em|ch|pt|cm|in)\b", re.IGNORECASE)
CENTRED = re.compile(
    r"margin\s*:[^;]*\bauto\b|margin-inline\s*:[^;]*\bauto\b"
    r"|margin-left\s*:\s*auto|margin-right\s*:\s*auto"
    r"|justify-self\s*:\s*center|place-self\s*:[^;]*center|align-self\s*:\s*center"
    r"|inset-inline\s*:[^;]*\bauto\b|translate\s*:|transform\s*:[^;]*translate",
    re.IGNORECASE,
)
# Elements whose own width is bounded for legibility rather than to make a page column.
INLINE_LEVEL = re.compile(r"\b(img|svg|video|picture|canvas|pre|code|table|input|button)\b", re.I)

# An inline script this big is a bundled library rather than page code. Used to notice the same
# library shipped once per page, which is how five charts became twenty megabytes.
RUNTIME_BYTES = 50_000

# A page built from the starting template resolves its text sizes through three tokens. A page
# written from scratch grows one size per element that needed to look a bit different: a real
# delivery from a capable model carried eight, at which point nothing on the page is the figure
# and nothing is the label. Counting distinct declared sizes is the cheapest way to tell those
# apart, and it is the one structural decision a run cannot fake by naming the skill in a comment.
FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}!]+)", re.IGNORECASE)
MAX_TYPE_SIZES = 3
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
        self.verbatim_depth = 0
        self.text: list[tuple[int, str]] = []
        self.verbatim: list[bool] = []  # one flag per chunk of self.text, in the same order
        self.styles: list[str] = []
        self.title = ""
        self.lang = ""  # what <html lang> declares, if anything
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
        if tag == "html" and not self.lang:
            for name, value in attrs:
                if name.lower() == "lang" and value:
                    self.lang = value
        for name, value in attrs:
            if name.lower() == "id" and value:
                self.ids.append((value, self.line))
        if tag == "meta":
            self._meta(attrs)
        if tag in ("style", "title"):
            self.inside = tag
        if tag in OPAQUE_ELEMENTS:
            self.opaque_depth += 1
        if tag in VERBATIM_ELEMENTS:
            self.verbatim_depth += 1
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
        if tag in VERBATIM_ELEMENTS and self.verbatim_depth:
            self.verbatim_depth -= 1
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
            self.verbatim.append(self.verbatim_depth > 0)

    @property
    def prose(self) -> list[tuple[int, str]]:
        """The page's own copy, with the specimens removed.

        A path or a foreign phrase inside <code> is being quoted, not said, and a check that
        cannot tell the difference makes an honest code sample unfixable.
        """
        return [
            entry for entry, verbatim in zip(self.text, self.verbatim) if not verbatim
        ]


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


def check_pipeline_jargon(
    pages: dict[Path, PageParser], manifest: dict[str, object], report: Report
) -> None:
    """The page is read by whoever opens it, not by whoever ran the pipeline that built it.

    A stage name from this pack, one of its own artefact filenames, or the word "bucket" is true
    and unreadable to that reader: it names something from PROFILE through DISCLOSE, and that
    belongs in the reply that hands the page over, or in docs/data beside the curated table --
    never printed as page text for a reader who never ran the pipeline and has no reason to know
    what any of it means. See the SKILL's own section on this before assuming a hit is a mistake.
    """
    exceptions = manifest.get("page_copy_exceptions")
    exceptions = {str(item).lower() for item in exceptions} if isinstance(exceptions, list) else set()

    for path, parser in pages.items():
        # Once per page, like every other family. Counting each text chunk made the total scale
        # with how much prose a page happens to carry, so two runs could not be compared and the
        # number the receipt records stopped meaning anything.
        report.checked += 1
        for line, chunk in parser.text:
            stripped = chunk.strip()
            if not stripped:
                continue

            for match in STAGE_WORD.finditer(stripped):
                token = match.group(1)
                if token.lower() in exceptions:
                    continue
                report.error(
                    "page/pipeline-jargon",
                    f"{token!r} is one of this pack's own stage names, sitting as plain text on "
                    "the page. A reader who did not run the pipeline has no reason to know what "
                    "it means -- say it in the reply that hands the page over, or record it in "
                    "'page_copy_exceptions' if it is a real business term here (a product "
                    "literally named Model, say)",
                    str(path),
                    line,
                )
            for _match in BUCKET_WORD.finditer(stripped):
                if "bucket" in exceptions:
                    continue
                report.error(
                    "page/pipeline-jargon",
                    "'bucket' is this pack's own word for an uncategorized group. Say what the "
                    "group actually is instead: '1 lead did not answer', not '1 lead in the "
                    '"unspecified" bucket\'',
                    str(path),
                    line,
                )
            for match in ARTEFACT_NAME.finditer(stripped):
                token = match.group(0)
                if token.lower() in exceptions:
                    continue
                report.error(
                    "page/pipeline-jargon",
                    f"{token!r} names one of this pack's own artefact files. A reader of the "
                    "page has no way to open it and no reason to know it exists -- state the "
                    "detail in docs/data or in the reply instead of naming the file on the page",
                    str(path),
                    line,
                )


def check_page_language(
    pages: dict[Path, PageParser], manifest: dict[str, object], report: Report
) -> None:
    """One delivery, one language, and no plumbing in the copy.

    The sibling of the jargon family above, and it exists for the same reason: a page is read by
    whoever opens it. Two languages in one delivery is not a style question, it is a page half of
    whose readers cannot read half of -- and it happens by inference rather than by decision, when
    a template written in one language is filled with copy written in another. A path is the same
    failure one level down: true, and useless to somebody who cannot open the folder.

    Neither is something the run can see in its own output, which is why it is here. A page
    contaminated this way passes every other check in this script, and goes on passing it.
    """
    exceptions = manifest.get("page_copy_exceptions")
    exceptions = {str(item).lower() for item in exceptions} if isinstance(exceptions, list) else set()
    artefacts = {name.lower() for name in PIPELINE_ARTEFACT_NAMES}

    for path, parser in pages.items():
        report.checked += 1
        seen: dict[str, dict[str, int]] = {}
        opened: dict[str, int] = {}

        for line, chunk in parser.prose:
            for token in WORD_TOKEN.findall(chunk.lower()):
                if token in exceptions:
                    continue
                for language, markers in LANGUAGE_MARKERS.items():
                    if token in markers:
                        counts = seen.setdefault(language, {})
                        counts[token] = counts.get(token, 0) + 1
                        opened.setdefault(language, line)

            for match in DELIVERY_PATH.finditer(chunk):
                token = match.group(0)
                if token.lower() in exceptions:
                    continue
                # This pack's own filenames belong to the jargon family; reporting them here as
                # well would bill one fault twice and make the totals of two runs incomparable.
                if token.rstrip("/").rsplit("/", 1)[-1].lower() in artefacts:
                    continue
                report.error(
                    "page/delivery-path",
                    f"{token!r} is a path inside the project, printed as page text. Whoever "
                    "opens the page cannot open it and has no reason to know how the folder is "
                    "arranged -- put the detail in docs/data or in the reply that hands the page "
                    "over, or name it in 'page_copy_exceptions' if the page is genuinely about "
                    "this file",
                    str(path),
                    line,
                )

        present = {
            language: counts
            for language, counts in seen.items()
            if len(counts) >= MIN_LANGUAGE_MARKERS
        }
        if len(present) < 2:
            continue
        declared = LANGUAGE_CODES.get(parser.lang.split("-")[0].strip().lower())
        if declared in present:
            dominant = declared
            says = f'the page declares {dominant} in <html lang>'
        else:
            dominant = max(present, key=lambda language: sum(present[language].values()))
            says = f'the page reads as {dominant}'
        for language in sorted(present):
            if language == dominant:
                continue
            words = ", ".join(sorted(present[language])[:4])
            report.error(
                "page/mixed-language",
                f"{says} and carries {language} in the same text "
                f"({words}). Everything a reader reads takes one language, whole: carry the "
                "leftover over, or move it into the reply that hands the page across. A term "
                "that is genuinely this language belongs in 'page_copy_exceptions'",
                str(path),
                opened[language],
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


def layout_option(manifest: dict[str, object], key: str, default: object = None) -> object:
    """One field out of the manifest's layout block."""
    layout = manifest.get("layout")
    return layout.get(key, default) if isinstance(layout, dict) else default


DESTINATIONS = ("project-file", "published-page")


def check_destination(manifest: dict[str, object], report: Report) -> None:
    """Whether the run recorded where the page was going, before it built one.

    The layout skill opens by asking that, because the answer decides what can still be verified
    afterwards, and a real run skipped it with the instruction in front of it. Nothing here can
    tell whether a person was asked; it can only tell whether a decision was written down, which
    is the part a reader can then disagree with. That gap is printed with the rest.
    """
    report.checked += 1
    declared = layout_option(manifest, "destination")
    if not isinstance(declared, str) or declared not in DESTINATIONS:
        report.error(
            "layout/no-destination",
            "the manifest declares no 'layout.destination'; it is one of "
            f"{', '.join(DESTINATIONS)}, and it is a decision the reader makes because it trades "
            "opening in one click against having these figures recomputed against the table",
        )


def left_aligned(manifest: dict[str, object]) -> bool:
    """Whether sitting against one edge was recorded as a decision."""
    return bool(layout_option(manifest, "left_aligned", False))


def check_viewports(
    path: Path, parser: PageParser, manifest: dict[str, object], report: Report
) -> None:
    """A page that claims to respond to width has to have been looked at, at some widths.

    Nothing here renders anything, and no check that reads a file ever will. So the claim moves:
    the manifest names the widths the page has to work at, the run says what it saw at each, and
    this refuses a responsive page with no observations rather than passing it in silence. It
    cannot tell a real observation from an invented one, exactly as the receipt cannot; what it
    removes is the option of skipping the look without anybody noticing.
    """
    css = "\n".join(parser.styles)
    if not css.strip() or not RESPONSIVE.search(css):
        return

    declared = layout_option(manifest, "viewports")
    widths = (
        [int(w) for w in declared if isinstance(w, (int, float))]
        if isinstance(declared, list)
        else []
    )
    report.checked += 1
    if not widths:
        report.error(
            "layout/no-viewports-declared",
            "the page responds to width and 'layout.viewports' names none. Declare the widths it "
            "has to work at; 375, 768 and 1440 is the usual set, and the narrow one is where "
            "labels rotate and text starts overlapping",
            str(path),
        )
        return

    observed = layout_option(manifest, "observed")
    seen: dict[int, str] = {}
    if isinstance(observed, list):
        for item in observed:
            if isinstance(item, dict) and isinstance(item.get("width"), (int, float)):
                seen[int(item["width"])] = str(item.get("note", "")).strip()

    for width in widths:
        report.checked += 1
        if width not in seen:
            report.error(
                "layout/not-observed",
                f"{width}px is declared and nothing says what the page looked like there. Open it "
                "at that width, then record what you saw in 'layout.observed'",
                str(path),
            )
        elif not seen[width]:
            report.error(
                "layout/observation-empty",
                f"the observation for {width}px says nothing. 'Fine' is not an observation; name "
                "what you checked, such as whether any label rotated or any text overlapped",
                str(path),
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


def check_layout(
    path: Path, parser: PageParser, report: Report, *, allow_left: bool = False
) -> None:
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
    # Only the page's own styles: a vendored library ships hundreds of sizes and none of them is a
    # decision anybody here made.
    own = "\n".join(block for block in parser.styles if len(block) < RUNTIME_BYTES)
    sizes = {" ".join(found.split()).lower() for found in FONT_SIZE.findall(own)}
    if len(sizes) > MAX_TYPE_SIZES:
        report.error(
            "layout/type-scale",
            f"the page declares {len(sizes)} distinct font sizes ({', '.join(sorted(sizes)[:6])}"
            f"{', …' if len(sizes) > 6 else ''}); the starting template resolves text through "
            f"three roles — figure, body and label — and a fourth distinction is a weight, a "
            f"colour or a letter-spacing change. A page that grew one size per element has no "
            f"figure and no label, only text of assorted sizes",
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

    if allow_left:
        return
    for selector, body in CSS_RULE.findall(css):
        name = selector.strip()
        if not name or name.startswith("@") or INLINE_LEVEL.search(name):
            continue
        if BOUNDED_WIDTH.search(body) and not CENTRED.search(body):
            report.checked += 1
            report.error(
                "layout/not-centred",
                f"'{name}' has a maximum width and its own rule does nothing to centre it, so it "
                "sits against one edge with the rest of the viewport empty beside it. Add an "
                "automatic inline margin. If it is centred by a flex or grid parent, which is "
                "not readable from one rule, or if it is left-aligned on purpose, record that as "
                "layout.left_aligned in the manifest",
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


def write_receipt(path: Path, inputs: list[Path], report: Report, absent: list[str]) -> None:
    """Leave proof on disk that this ran green, or remove the proof that it did not.

    A checklist box saying "run the check and paste the output" is worth exactly the honesty of
    whoever ticks it, which is the same problem the disclosure note had before something looked
    for the file. So a green run writes a receipt naming what it read and the digest of each one,
    and a red run deletes any receipt that was there. What that buys is narrow and worth stating:
    it proves a green run happened over these exact bytes. It does not defeat a forged file, and
    nothing that runs after the fact can.

    ``absent`` is the other half, and it is the half that is easy to leave out. A reader comparing
    digests can only conclude something about a file the receipt names; a file missing from
    ``inputs`` is indistinguishable from one that was never covered, and reading an absence as a
    pass is the exact failure this whole script exists to refuse. So the notes that did not exist
    at check time are written down by name rather than left to be inferred.
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
        "absent_at_check": absent,
        "proves": "a green run over exactly these bytes; nothing about a file not listed here",
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
            check_layout(path, parsed, report, allow_left=left_aligned(manifest))
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
        check_viewports(page, parsed, manifest, report)

    check_destination(manifest, report)
    check_page_numbers(pages, accounted, report)
    check_pipeline_jargon(pages, manifest, report)
    check_page_language(pages, manifest, report)
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
    notes = [args.manifest.parent / name for name in RECORDED_NOTES]
    inputs.extend(note for note in notes if note.is_file())
    absent = [str(note) for note in notes if not note.is_file()]
    write_receipt(receipt, inputs, report, absent)

    result = {
        "ok": not report.errors,
        "checked": report.checked,
        "errors": report.errors,
        "warnings": report.warnings,
        "not_verified": list(NOT_VERIFIED),
        "receipt": str(receipt) if not report.errors else None,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    summary = f"verify-output: {report.checked} checked, {len(report.errors)} error(s)"
    print(summary, file=sys.stderr)
    # Printed on every run, including a clean one. A green result that says nothing about its own
    # blind spots is read as "the page is fine", and a page that passed every check here has
    # shipped with text overlapping itself on a narrow screen.
    print("verify-output: NOT verified by this script, because it never renders:", file=sys.stderr)
    for item in NOT_VERIFIED:
        print(f"  · {item}", file=sys.stderr)
    for entry in report.errors:
        location = f" {entry['where']}:{entry['line']}" if entry["where"] else ""
        print(f"  {entry['rule']}{location}: {entry['message']}", file=sys.stderr)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
PYTHON_PROGRAM
