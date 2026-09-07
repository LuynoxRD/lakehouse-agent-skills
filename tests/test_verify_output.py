"""Tests for the artefact check that ships inside the skills, run as a real process.

The script exists because every other checklist in this pack verifies a document the run wrote
about its own work, and none of them opens the file the reader receives. So the cases here are
the faults that were actually found in a delivered artefact whose run had ticked every box:

* a page built by embedding figures from a writer whose default is a whole document, leaving
  fourteen documents nested inside one, each carrying its own stylesheet;
* a number printed in a header that no query produced and that disagreed with the computed tile
  a few centimetres below it;
* a note written with an unqualified open() on Windows, so the delivered file is not UTF-8.

Shell is tested by starting it.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill-scripts" / "verify-output.sh"
BASH = shutil.which("bash")
HAS_DUCKDB = importlib.util.find_spec("duckdb") is not None

pytestmark = pytest.mark.skipif(BASH is None, reason="the check is shell and needs bash to run")

ROWS = "status,total\ndelivered,10.00\ndelivered,15.50\ncancelled,4.50\n"

# A page that satisfies the layout checks, so tests about figures and receipts are not also
# testing the layout. What it carries is the minimum those checks look for: a viewport, one rule
# that responds to width, and a title.
CLEAN_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sales</title>
<style>.board { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }</style>
</head>
<body>
  <h1>Sales</h1>
  <p>Revenue 25.50 across delivered orders only</p>
</body>
</html>
"""

# What a plotting library returns when it is asked for a figure's HTML and nobody passed the
# option that turns the whole document off.
EMBEDDED_DOCUMENT = """<!doctype html>
<html>
<head><meta charset="utf-8"><style>html, body {height: 100%;}</style></head>
<body><div id="figure"></div></body>
</html>"""

NESTED_PAGE = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sales</title>
<style>.board {{ display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}</style>
</head>
<body>
  <div class="tile">{EMBEDDED_DOCUMENT}</div>
  <p>Revenue 25.50 across delivered orders only</p>
</body>
</html>
"""


def manifest(table: Path, *, value: float = 25.50) -> dict[str, object]:
    """A manifest that declares one figure, the query behind it, and the widths that were looked at.

    The layout block is here rather than in the tests that need it because a responsive page
    without it is now an error, and every fixture page is responsive: leaving it out would make
    every unrelated test also a test of the viewport rule. The destination is here for the same
    reason: it is required on every run, so its own test declares it missing rather than the
    other way round.
    """
    return {
        "table": str(table),
        "layout": {
            "destination": "project-file",
            "viewports": [375, 1440],
            "observed": [
                {"width": 375, "note": "labels upright, nothing overlapping"},
                {"width": 1440, "note": "centred, no dead space beside the board"},
            ],
        },
        "figures": [
            {
                "label": "Revenue",
                "value": value,
                "population": "delivered orders only",
                "sql": "SELECT SUM(total) FROM t WHERE status = 'delivered'",
            }
        ],
    }


def project(
    tmp_path: Path, page: str, document: dict[str, object] | None = None
) -> tuple[Path, Path]:
    """A miniature delivery: one table, one manifest, one page."""
    table = tmp_path / "orders.csv"
    table.write_text(ROWS, encoding="utf-8", newline="\n")
    payload = manifest(table) if document is None else document
    note = tmp_path / "figures.json"
    note.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    html = tmp_path / "page.html"
    html.write_text(page, encoding="utf-8", newline="\n")
    return note, html


def run(note: Path, html: Path, docs: Path | None = None) -> tuple[int, dict[str, object]]:
    """Start the check the way a skill tells the reader to, and read its report."""
    assert BASH is not None
    command = [BASH, str(SCRIPT), "--manifest", str(note), "--html", str(html)]
    if docs is not None:
        command += ["--docs", str(docs)]
    # The script resolves an interpreter from PATH unless one is named. It is named here, so the
    # tests report on the environment they run in rather than on whichever Python came first.
    result = subprocess.run(
        command,
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            # Kept deliberately: on Windows the bare name `python3` can be the install manager's
            # shim, and with no LOCALAPPDATA it resolves its install root to the working directory
            # and installs a Python there. Naming the interpreter avoids the probe; this makes the
            # fallback safe as well.
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "VERIFY_OUTPUT_PYTHON": sys.executable,
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def findings(report: dict[str, object]) -> list[dict[str, object]]:
    """The report's errors, narrowed from the JSON it was decoded as."""
    errors = report["errors"]
    assert isinstance(errors, list)
    return errors


def rules(report: dict[str, object]) -> set[str]:
    """Every rule the report fired, as a set."""
    return {str(entry["rule"]) for entry in findings(report)}


def messages(report: dict[str, object]) -> str:
    """Every message the report carried, joined, for asserting on the detail."""
    return " ".join(str(entry["message"]) for entry in findings(report))


def test_a_page_with_documents_nested_inside_it_is_refused(tmp_path: Path) -> None:
    """The exact fault a full-document figure writer produces, fourteen times in a real run."""
    note, html = project(tmp_path, NESTED_PAGE)

    code, report = run(note, html)

    assert code == 1
    assert "artefact/nested-document" in rules(report)
    assert "artefact/duplicate-charset" in rules(report)
    assert "<html> opens 2 times" in messages(report)


def test_a_single_document_page_raises_nothing_structural(tmp_path: Path) -> None:
    note, html = project(tmp_path, CLEAN_PAGE)

    _code, report = run(note, html)

    assert not [rule for rule in rules(report) if rule.startswith("artefact/")]


def test_a_number_no_query_produced_is_refused(tmp_path: Path) -> None:
    """The header said 182 customers; the tile below computed 162. Neither knew about the other."""
    page = CLEAN_PAGE.replace("<h1>Sales</h1>", "<h1>Sales</h1>\n  <p>182 customers</p>")
    note, html = project(tmp_path, page)

    code, report = run(note, html)

    assert code == 1
    assert "page/undeclared-number" in rules(report)
    assert "'182'" in messages(report)


def test_a_date_in_the_page_is_not_mistaken_for_a_figure(tmp_path: Path) -> None:
    """Periods and generation dates are printed on every dashboard and computed by nothing."""
    page = CLEAN_PAGE.replace("<h1>Sales</h1>", "<h1>Sales</h1>\n  <p>2026-01-01 to 2026-06-30</p>")
    note, html = project(tmp_path, page)

    _code, report = run(note, html)

    assert "page/undeclared-number" not in rules(report)


def test_a_figure_that_declares_no_population_is_refused(tmp_path: Path) -> None:
    """A total that hides an exclusion is wrong on the page, not in the notes."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    del figures[0]["population"]
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "figures/no-population" in rules(report)


def test_a_population_the_page_never_states_is_refused(tmp_path: Path) -> None:
    table = tmp_path / "orders.csv"
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    figures[0]["population"] = "orders placed on a Tuesday"
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "figures/population-not-on-page" in rules(report)


def test_a_manifest_with_no_figures_is_refused(tmp_path: Path) -> None:
    """A page with numbers and nothing declaring them is the state this exists to refuse."""
    note, html = project(tmp_path, CLEAN_PAGE, {"table": str(tmp_path / "orders.csv")})

    code, report = run(note, html)

    assert code == 1
    assert "figures/none-declared" in rules(report)


def test_a_delivered_note_that_is_not_utf8_is_refused(tmp_path: Path) -> None:
    """What an unqualified open(path, 'w') writes on Windows, in a file the reader receives."""
    docs = tmp_path / "docs"
    docs.mkdir()
    # Accented text is the whole point: an unqualified write only corrupts what is not ASCII,
    # which is why the corruption is invisible until somebody reads the delivered note.
    (docs / "cleaning-log.md").write_bytes("# Limpieza: categoría, región\n".encode("cp1252"))
    note, html = project(tmp_path, CLEAN_PAGE)

    code, report = run(note, html, docs)

    assert code == 1
    assert "docs/encoding" in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_figure_that_matches_the_table_passes(tmp_path: Path) -> None:
    note, html = project(tmp_path, CLEAN_PAGE)

    code, report = run(note, html)

    assert code == 0, report
    assert report["errors"] == []


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_figure_the_table_disagrees_with_is_refused(tmp_path: Path) -> None:
    """The published number and the table's answer, compared rather than assumed equal."""
    table = tmp_path / "orders.csv"
    document = manifest(table, value=30.0)
    note, html = project(tmp_path, CLEAN_PAGE.replace("25.50", "30.00"), document)

    code, report = run(note, html)

    assert code == 1
    assert "figures/mismatch" in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_summary_row_carried_in_as_data_is_refused(tmp_path: Path) -> None:
    """A spreadsheet's total row read as an ordinary row doubles the measure it summarises."""
    table = tmp_path / "orders.csv"
    table.write_text(ROWS + "TOTAL GENERAL,30.00\n", encoding="utf-8", newline="\n")
    note, html = project(tmp_path, CLEAN_PAGE)
    table.write_text(ROWS + "TOTAL GENERAL,30.00\n", encoding="utf-8", newline="\n")

    code, report = run(note, html)

    assert code == 1
    assert "table/aggregate-row" in rules(report)


JARGON_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sales</title>
<style>.board { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }</style>
</head>
<body>
  <h1>Sales</h1>
  <p>Revenue 25.50 across delivered orders only. Rows were excluded in CLEAN.</p>
</body>
</html>
"""


def test_a_pipeline_stage_name_on_the_page_is_refused(tmp_path: Path) -> None:
    """CLEAN is this pack's own stage name, not a word a business reader was ever meant to see."""
    note, html = project(tmp_path, JARGON_PAGE)

    code, report = run(note, html)

    assert code == 1
    assert "page/pipeline-jargon" in rules(report)
    assert "CLEAN" in messages(report)


BUCKET_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sales</title>
<style>.board { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }</style>
</head>
<body>
  <h1>Sales</h1>
  <p>Revenue 25.50 across delivered orders only. Some orders sit in the "unspecified" bucket.</p>
</body>
</html>
"""


def test_the_word_bucket_on_the_page_is_refused(tmp_path: Path) -> None:
    """'Bucket' is pipeline vocabulary for an uncategorised group, not a word for the reader."""
    note, html = project(tmp_path, BUCKET_PAGE)

    code, report = run(note, html)

    assert code == 1
    assert "page/pipeline-jargon" in rules(report)


ARTEFACT_NAME_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sales</title>
<style>.board { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }</style>
</head>
<body>
  <h1>Sales</h1>
  <p>Revenue 25.50 across delivered orders only — see cleaning-log.md for what was excluded.</p>
</body>
</html>
"""


def test_a_pipeline_artefact_filename_on_the_page_is_refused(tmp_path: Path) -> None:
    """A reader of the page cannot open cleaning-log.md and has no reason to know it exists."""
    note, html = project(tmp_path, ARTEFACT_NAME_PAGE)

    code, report = run(note, html)

    assert code == 1
    assert "page/pipeline-jargon" in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_declared_page_copy_exception_is_not_refused(tmp_path: Path) -> None:
    """A real business term that happens to collide with a stage name is named, not guessed."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    document["page_copy_exceptions"] = ["model"]
    page = JARGON_PAGE.replace("CLEAN", "MODEL")
    note, html = project(tmp_path, page, document)

    code, report = run(note, html)

    assert code == 0
    assert "page/pipeline-jargon" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_an_ordinary_lowercase_word_is_not_mistaken_for_a_stage_name(tmp_path: Path) -> None:
    """Stage names are matched in capitals only, so ordinary prose about clean energy passes."""
    page = CLEAN_PAGE.replace(
        "Revenue 25.50 across delivered orders only",
        "Revenue 25.50 across delivered orders only, mostly from clean energy customers",
    )
    note, html = project(tmp_path, page)

    code, report = run(note, html)

    assert code == 0
    assert "page/pipeline-jargon" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_sql_that_is_not_a_select_is_refused(tmp_path: Path) -> None:
    """The manifest is read, not trusted: the check never becomes a way to write to the table."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    figures[0]["sql"] = "DROP VIEW t"
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "figures/sql" in rules(report)


def with_dependencies(tmp_path: Path, package_json: str) -> None:
    """Give the miniature project a dependency declaration to read."""
    (tmp_path / "package.json").write_text(package_json, encoding="utf-8", newline="\n")


def run_with_project(note: Path, html: Path, project: Path) -> tuple[int, dict[str, object]]:
    assert BASH is not None
    result = subprocess.run(
        [
            BASH,
            str(SCRIPT),
            "--manifest",
            str(note),
            "--html",
            str(html),
            "--project",
            str(project),
        ],
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "VERIFY_OUTPUT_PYTHON": sys.executable,
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def test_two_charting_libraries_with_no_stated_difference_are_refused(tmp_path: Path) -> None:
    """Two visual languages in one project, arrived at rather than chosen."""
    note, html = project(tmp_path, CLEAN_PAGE)
    with_dependencies(tmp_path, '{"dependencies": {"plotly.js": "2", "echarts": "5"}}')

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "project/second-library" in rules(report)
    assert "plotly" in messages(report)
    assert "echarts" in messages(report)


def test_two_charting_libraries_with_a_stated_difference_pass(tmp_path: Path) -> None:
    """Having two is allowed. Arriving at two without deciding is not."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    document["libraries"] = {
        "charts_reason": "echarts for the linked dashboard, plotly in notebooks"
    }
    note, html = project(tmp_path, CLEAN_PAGE, document)
    with_dependencies(tmp_path, '{"dependencies": {"plotly.js": "2", "echarts": "5"}}')

    _code, report = run_with_project(note, html, tmp_path)

    assert "project/second-library" not in rules(report)


def test_a_library_and_its_wrapper_are_one_decision(tmp_path: Path) -> None:
    """seaborn on matplotlib is one visual language; counting names would call it two."""
    note, html = project(tmp_path, CLEAN_PAGE)
    with_dependencies(tmp_path, '{"dependencies": {"matplotlib": "3", "seaborn": "0.13"}}')

    _code, report = run_with_project(note, html, tmp_path)

    assert "project/second-library" not in rules(report)


def test_two_dataframe_libraries_are_refused(tmp_path: Path) -> None:
    """The same table typed twice, by different rules, is the failure the pack exists to stop."""
    note, html = project(tmp_path, CLEAN_PAGE)
    with_dependencies(tmp_path, '{"dependencies": {"pandas": "2", "polars": "1"}}')

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "project/second-library" in rules(report)
    assert "dataframe" in messages(report)


def test_one_library_of_each_kind_passes(tmp_path: Path) -> None:
    note, html = project(tmp_path, CLEAN_PAGE)
    with_dependencies(tmp_path, '{"dependencies": {"echarts": "5", "polars": "1"}}')

    _code, report = run_with_project(note, html, tmp_path)

    assert "project/second-library" not in rules(report)


def test_a_project_with_no_dependency_file_is_not_second_guessed(tmp_path: Path) -> None:
    note, html = project(tmp_path, CLEAN_PAGE)

    _code, report = run_with_project(note, html, tmp_path)

    assert "project/second-library" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_green_run_leaves_a_receipt(tmp_path: Path) -> None:
    """Something has to be able to check that this ran, without taking a checklist at its word."""
    note, html = project(tmp_path, CLEAN_PAGE)

    code, report = run(note, html)

    assert code == 0, report
    receipt = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    assert receipt["ok"] is True
    recorded = {entry["path"] for entry in receipt["inputs"]}
    assert str(html) in recorded
    assert str(note) in recorded
    assert all(len(entry["sha256"]) == 64 for entry in receipt["inputs"])


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_the_receipt_covers_the_notes_a_reviewer_treats_as_evidence(tmp_path: Path) -> None:
    """Found by audit, not by any check here.

    The reviewer persona is told to read the receipt first and let it bound the rest, and its
    table of artifacts lists five files. The receipt named two of them. Anyone editing the
    disclosure after a green run left the receipt intact, so an absence read as a pass, which is
    the same failure as a green check being read as a page that renders.
    """
    note, html = project(tmp_path, CLEAN_PAGE)
    disclosure = tmp_path / "disclosure.md"
    disclosure.write_text("Processed 1 of 1 inputs, 4 rows.\n", encoding="utf-8", newline="\n")

    code, report = run(note, html)

    assert code == 0, report
    receipt = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    assert str(disclosure) in {entry["path"] for entry in receipt["inputs"]}
    # The three that do not exist are named, because an absence has to be read, not inferred.
    assert receipt["absent_at_check"] == [
        str(tmp_path / name) for name in ("profile.md", "cleaning-log.md", "model.md")
    ]


def test_a_run_that_never_recorded_where_the_page_was_going_is_refused(tmp_path: Path) -> None:
    """The layout skill opens with that question and a real run skipped it, instruction in hand.

    A rule with no mechanism is a rule a run under pressure drops, which is the whole lesson of
    this file. What the check can see is whether a decision was recorded; that it cannot see
    whether anybody was asked is printed with the other blind spots on every run.
    """
    table = tmp_path / "orders.csv"
    table.write_text(ROWS, encoding="utf-8", newline="\n")
    document = manifest(table)
    layout = document["layout"]
    assert isinstance(layout, dict)
    del layout["destination"]
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/no-destination" in rules(report)
    unverified = report["not_verified"]
    assert isinstance(unverified, list)
    assert any("recorded" in str(item) for item in unverified)


def test_a_destination_outside_the_two_is_refused(tmp_path: Path) -> None:
    """A free-text value would let any string count as a decision."""
    table = tmp_path / "orders.csv"
    table.write_text(ROWS, encoding="utf-8", newline="\n")
    document = manifest(table)
    layout = document["layout"]
    assert isinstance(layout, dict)
    layout["destination"] = "somewhere"
    note, html = project(tmp_path, CLEAN_PAGE, document)

    _code, report = run(note, html)

    assert "layout/no-destination" in rules(report)


def test_a_page_with_a_size_per_element_is_refused(tmp_path: Path) -> None:
    """Found by measuring two real deliveries, one of them from a capable model.

    That one carried eight distinct sizes, at which point nothing on the page is the figure and
    nothing is the label. Three roles is what the starting template resolves text through, and the
    count is the one structural decision a run cannot fake by naming the skill in a comment.
    """
    scale = "".join(f".s{n} {{ font-size: {n}rem; }}" for n in range(1, 9))
    note, html = project(tmp_path, CLEAN_PAGE.replace("<style>", "<style>" + scale))

    code, report = run(note, html)

    assert code == 1
    assert "layout/type-scale" in rules(report)
    assert "8 distinct font sizes" in messages(report)


def test_three_roles_resolved_through_tokens_pass(tmp_path: Path) -> None:
    """What the starting template itself does, so the rule has to accept it."""
    scale = ".a{font-size:var(--t-figure)}.b{font-size:var(--t-body)}.c{font-size:var(--t-label)}"
    note, html = project(tmp_path, CLEAN_PAGE.replace("<style>", "<style>" + scale))

    _code, report = run(note, html)

    assert "layout/type-scale" not in rules(report)


def test_both_streams_decode_as_utf8_whatever_the_console_is(tmp_path: Path) -> None:
    """Found by running the check over a page in Spanish on a Windows console.

    Both streams carry text lifted from the page -- a label, a population, a quoted sentence -- and
    they defaulted to the console code page, so stderr came back as bytes no reader could decode
    and the JSON was one accented label away from the same. A verification whose own output is
    unreadable to the person who ran it is the failure this script exists to refuse, pointed at
    itself.
    """
    table = tmp_path / "pedidos.csv"
    table.write_text("estado,total\nentregado,25.50\n", encoding="utf-8", newline="\n")
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    figures[0]["label"] = "Facturación"
    figures[0]["population"] = "sólo pedidos entregados, año 2025"
    figures[0]["sql"] = "SELECT SUM(total) FROM t"
    page = CLEAN_PAGE.replace(
        "Revenue 25.50 across delivered orders only",
        "Facturación 25.50 sólo pedidos entregados, año 2025",
    )
    note, html = project(tmp_path, page, document)

    assert BASH is not None
    result = subprocess.run(
        [BASH, str(SCRIPT), "--manifest", str(note), "--html", str(html)],
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "VERIFY_OUTPUT_PYTHON": sys.executable,
        },
        capture_output=True,
        timeout=180,
        check=False,
    )

    # Bytes, not text: decoding here with a forgiving codec would hide exactly the defect.
    result.stdout.decode("utf-8")
    # The bullet the blind-spot list prints on every run was the byte that gave this away, arriving
    # as a lone 0xB7 from the console code page instead of the two bytes UTF-8 spells it with.
    assert "·".encode() in result.stderr
    result.stderr.decode("utf-8")


# A delivery that is Spanish end to end -- manifest and page -- so that anything a test adds is
# the only foreign text on the page and the rule has one thing to find.
SPANISH_PAGE = """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ventas</title>
<style>.board {{ display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}</style>
</head>
<body>
  <h1>Ventas</h1>
  <p>Facturación 25.50, solo los pedidos entregados, pero sin los cancelados</p>
{extra}
</body>
</html>
"""


def spanish(tmp_path: Path, extra: str = "") -> tuple[Path, Path]:
    """The Spanish delivery, with whatever a test wants to add to the body."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    figures[0]["label"] = "Facturación"
    figures[0]["population"] = "solo los pedidos entregados"
    return project(tmp_path, SPANISH_PAGE.format(extra=extra), document)


def embedded_program() -> str:
    """The Python the shell script hands its interpreter, lifted back out of the heredoc."""
    source = SCRIPT.read_text(encoding="utf-8")
    opening = "<<'PYTHON_PROGRAM'\n"
    start = source.index(opening) + len(opening)
    return source[start : source.index("\nPYTHON_PROGRAM", start)]


def language_markers() -> dict[str, frozenset[str]]:
    """The marker tables, read out of the script rather than run out of it."""
    for node in ast.parse(embedded_program()).body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "LANGUAGE_MARKERS":
            continue
        assert isinstance(node.value, ast.Dict)
        found: dict[str, frozenset[str]] = {}
        for key, value in zip(node.value.keys, node.value.values, strict=True):
            assert key is not None
            assert isinstance(value, ast.Call)
            found[str(ast.literal_eval(key))] = frozenset(ast.literal_eval(value.args[0]))
        return found
    raise AssertionError("the embedded program declares no LANGUAGE_MARKERS")


def test_no_word_belongs_to_two_languages() -> None:
    """The invariant the whole family rests on, asserted rather than trusted.

    Every word in these tables is supposed to appear in exactly one of the six languages. One that
    leaked into two would report any page carrying it as bilingual, and the page would have no way
    to be fixed: the word is in the language it is already in.
    """
    markers = language_markers()
    assert len(markers) == 6
    for left in markers:
        for right in markers:
            if left < right:
                assert not markers[left] & markers[right], (left, right)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_page_written_in_two_languages_is_refused(tmp_path: Path) -> None:
    """Found in a delivered page: a template in one language filled with copy from another.

    Nobody decided it. It is what happens when the skills' own files are read as a rule about the
    delivery instead of a rule about the repository, and no other check in this script sees it: the
    numbers are right, the structure is right, and half the readers can read half the page.
    """
    note, html = spanish(tmp_path, "  <p>Revenue grew and the margin improved</p>")

    code, report = run(note, html)

    assert code == 1
    assert "page/mixed-language" in rules(report)
    assert "declares Spanish" in messages(report)
    assert "carries English" in messages(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_one_foreign_word_is_not_a_second_language(tmp_path: Path) -> None:
    """A brand, a loan word or a proper noun is one word, and one word is not a sentence."""
    note, html = spanish(tmp_path, "  <p>Ventas de la tienda The Corner</p>")

    code, report = run(note, html)

    assert code == 0
    assert "page/mixed-language" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_code_specimen_is_not_the_page_speaking(tmp_path: Path) -> None:
    """A query shown as a specimen is quoted, not said, and its path is part of the quotation."""
    specimen = (
        "  <pre><code>-- and the other columns are dropped here\n"
        "SELECT SUM(total) FROM 'data/curated/orders.parquet'</code></pre>"
    )
    note, html = spanish(tmp_path, specimen)

    code, report = run(note, html)

    assert code == 0
    assert "page/mixed-language" not in rules(report)
    assert "page/delivery-path" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_path_into_the_project_is_refused(tmp_path: Path) -> None:
    """The reader cannot open it and has no reason to know the folder is arranged that way."""
    note, html = spanish(tmp_path, "  <p>Fuente: data/curated/orders.parquet</p>")

    code, report = run(note, html)

    assert code == 1
    assert "page/delivery-path" in rules(report)
    assert "data/curated/orders.parquet" in messages(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_declared_path_exception_is_not_refused(tmp_path: Path) -> None:
    """A page that is genuinely about a file names it once, in the manifest, and is believed."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    figures = document["figures"]
    assert isinstance(figures, list)
    figures[0]["label"] = "Facturación"
    figures[0]["population"] = "solo los pedidos entregados"
    document["page_copy_exceptions"] = ["data/curated/orders.parquet"]
    page = SPANISH_PAGE.format(extra="  <p>Fuente: data/curated/orders.parquet</p>")
    note, html = project(tmp_path, page, document)

    code, report = run(note, html)

    assert code == 0
    assert "page/delivery-path" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_this_pack_s_own_filenames_are_billed_once(tmp_path: Path) -> None:
    """Two families can match one string. Reporting it twice makes two runs incomparable."""
    note, html = project(tmp_path, ARTEFACT_NAME_PAGE)

    code, report = run(note, html)

    assert code == 1
    assert "page/pipeline-jargon" in rules(report)
    assert "page/delivery-path" not in rules(report)


OLD_STATE = "0" * 64


def delivered(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A clean delivery with a docs directory, which is where a review would be recorded."""
    note, html = project(tmp_path, CLEAN_PAGE)
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "disclosure.md").write_text(
        "# Coverage\n\nAll 3 rows read, none skipped.\n", encoding="utf-8", newline="\n"
    )
    return note, html, docs


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_run_reports_the_state_it_read(tmp_path: Path) -> None:
    """The fingerprint a review names. Without it there is nothing to be stale against."""
    note, html, docs = delivered(tmp_path)

    code, report = run(note, html, docs)

    assert code == 0
    state = report["state"]
    assert isinstance(state, str)
    assert len(state) == 64


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_notes_that_record_no_review_are_never_asked_for_one(tmp_path: Path) -> None:
    """Recording a review stays optional. What is refused is a recorded one that is not true."""
    note, html, docs = delivered(tmp_path)

    code, report = run(note, html, docs)

    assert code == 0
    assert "review/superseded" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_review_recorded_against_older_bytes_is_refused(tmp_path: Path) -> None:
    """The failure that looks like diligence.

    A note carrying "reviewed" and a date reads as a standing property of the work. It is not: it
    was true about the bytes in front of the reviewer that day, and every artefact here can be
    regenerated without the review regenerating with it.
    """
    note, html, docs = delivered(tmp_path)
    (docs / "disclosure.md").write_text(
        f"# Coverage\n\nReviewed by the data reviewer, state: {OLD_STATE}\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 1
    assert "review/superseded" in rules(report)
    assert OLD_STATE[:12] in messages(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_review_that_names_the_current_state_passes(tmp_path: Path) -> None:
    note, html, docs = delivered(tmp_path)
    _code, first = run(note, html, docs)
    state = first["state"]
    (docs / "disclosure.md").write_text(
        f"# Coverage\n\nReviewed by the data reviewer, state: {state}\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 0, messages(report)
    assert "review/superseded" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_the_history_may_stay_when_a_current_review_is_there_too(tmp_path: Path) -> None:
    """Keeping the older entries is often the point. A history with no current entry is not."""
    note, html, docs = delivered(tmp_path)
    _code, first = run(note, html, docs)
    (docs / "disclosure.md").write_text(
        f"# Coverage\n\n- 2026-09-01, state: {OLD_STATE}\n- today, state: {first['state']}\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 0, messages(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_bare_digest_in_a_note_is_not_read_as_a_review(tmp_path: Path) -> None:
    """Only a labelled fingerprint counts, so a note quoting a file's own hash is left alone."""
    note, html, docs = delivered(tmp_path)
    (docs / "disclosure.md").write_text(
        f"# Coverage\n\nThe source arrived with sha256 {OLD_STATE} per the sender.\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 0, messages(report)
    assert "review/superseded" not in rules(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_the_state_does_not_move_when_nothing_did(tmp_path: Path) -> None:
    """A fingerprint that changed on its own would make every recorded review stale by noon."""
    note, html, docs = delivered(tmp_path)

    _code, first = run(note, html, docs)
    _code, second = run(note, html, docs)

    assert first["state"] == second["state"]


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_the_state_moves_when_a_delivered_byte_does(tmp_path: Path) -> None:
    """The whole point. A review names a state, and the state is what changing the work breaks."""
    note, html, docs = delivered(tmp_path)
    _code, before = run(note, html, docs)
    html.write_text(
        CLEAN_PAGE.replace("<h1>Sales</h1>", "<h1>Sales by month</h1>"),
        encoding="utf-8",
        newline="\n",
    )

    _code, after = run(note, html, docs)

    assert before["state"] != after["state"]


def documented(tmp_path: Path) -> tuple[Path, Path, Path]:
    """The layout the skill actually tells people to build.

    The manifest sits in `docs/data` beside the four notes, which is what makes the placement of a
    recorded review a real question: those notes are hashed into the state, and this fixture is the
    only one that reproduces that.
    """
    docs = tmp_path / "docs" / "data"
    docs.mkdir(parents=True, exist_ok=True)
    table = tmp_path / "orders.csv"
    table.write_text(ROWS, encoding="utf-8", newline="\n")
    note = docs / "figures.json"
    note.write_text(json.dumps(manifest(table)), encoding="utf-8", newline="\n")
    for name in ("profile.md", "cleaning-log.md", "model.md", "disclosure.md"):
        (docs / name).write_text(f"# {name}\n\nnotes\n", encoding="utf-8", newline="\n")
    html = tmp_path / "page.html"
    html.write_text(CLEAN_PAGE, encoding="utf-8", newline="\n")
    return note, html, docs


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_review_recorded_in_a_hashed_note_is_refused(tmp_path: Path) -> None:
    """Found by laying the project out the way the skill documents it, and trying to use this.

    The four notes are hashed into the state, so a review written inside one of them changes the
    state it just named: stale the moment it is saved, and correcting it moves the target again.
    Two rounds of that were measured before this rule existed.
    """
    note, html, docs = documented(tmp_path)
    _code, first = run(note, html, docs)
    disclosure = docs / "disclosure.md"
    disclosure.write_text(
        disclosure.read_text(encoding="utf-8") + f"\nReviewed today, state: {first['state']}\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 1
    assert "review/self-defeating" in rules(report)
    assert "reviews.md" in messages(report)


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_review_recorded_where_the_state_is_not_computed_settles(tmp_path: Path) -> None:
    """The round trip that makes the mechanism usable rather than merely correct.

    Record the review in the note the state is deliberately not computed over, and the next run
    agrees with it. Without this the whole family could be right in every detail and never settle.
    """
    note, html, docs = documented(tmp_path)
    _code, first = run(note, html, docs)
    (docs / "reviews.md").write_text(
        f"# Reviews\n\n- data-work-reviewer, no contradictions, state: {first['state']}\n",
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 0, messages(report)
    assert report["state"] == first["state"]


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_a_review_in_the_right_note_still_goes_stale_when_the_work_changes(tmp_path: Path) -> None:
    """Settling is not the same as never expiring, which is the point of the whole family."""
    note, html, docs = documented(tmp_path)
    _code, first = run(note, html, docs)
    (docs / "reviews.md").write_text(
        f"# Reviews\n\n- data-work-reviewer, state: {first['state']}\n",
        encoding="utf-8",
        newline="\n",
    )
    html.write_text(
        CLEAN_PAGE.replace("<h1>Sales</h1>", "<h1>Sales by month</h1>"),
        encoding="utf-8",
        newline="\n",
    )

    code, report = run(note, html, docs)

    assert code == 1
    assert "review/superseded" in rules(report)


def test_a_failing_run_removes_a_receipt_that_was_there(tmp_path: Path) -> None:
    """A receipt from an earlier green run must not vouch for a page that now fails."""
    note, html = project(tmp_path, NESTED_PAGE)
    stale = tmp_path / "verification.json"
    stale.write_text('{"ok": true}\n', encoding="utf-8")

    code, _report = run(note, html)

    assert code == 1
    assert not stale.exists()


@pytest.mark.skipif(not HAS_DUCKDB, reason="the figure check needs the DuckDB package")
def test_the_receipt_records_the_bytes_that_were_checked(tmp_path: Path) -> None:
    """Editing the page after the check leaves a receipt whose digest no longer matches."""
    note, html = project(tmp_path, CLEAN_PAGE)
    run(note, html)
    before = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    digest = next(e["sha256"] for e in before["inputs"] if e["path"] == str(html))

    html.write_text(CLEAN_PAGE.replace("25.50", "99.99"), encoding="utf-8", newline="\n")

    assert hashlib.sha256(html.read_bytes()).hexdigest() != digest


RUNTIME = "<script>" + ("// a bundled library\n" * 4000) + "</script>"


def test_several_delivered_pages_with_no_stated_reason_are_refused(tmp_path: Path) -> None:
    """Five files of one chart each are five charts; the reader does the assembling."""
    note, html = project(tmp_path, CLEAN_PAGE)
    for index in range(2, 5):
        (tmp_path / f"chart_{index}.html").write_text(CLEAN_PAGE, encoding="utf-8", newline="\n")

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "delivery/many-pages" in rules(report)
    assert "chart_2.html" in messages(report)


def test_several_pages_with_a_stated_reason_pass(tmp_path: Path) -> None:
    """Splitting is allowed. Splitting without deciding is not."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    document["pages_reason"] = "one page per region, agreed with the team"
    note, html = project(tmp_path, CLEAN_PAGE, document)
    (tmp_path / "second.html").write_text(CLEAN_PAGE, encoding="utf-8", newline="\n")

    _code, report = run_with_project(note, html, tmp_path)

    assert "delivery/many-pages" not in rules(report)


def test_one_page_is_never_questioned(tmp_path: Path) -> None:
    note, html = project(tmp_path, CLEAN_PAGE)

    _code, report = run_with_project(note, html, tmp_path)

    assert "delivery/many-pages" not in rules(report)


def test_the_same_library_embedded_in_every_page_is_refused(tmp_path: Path) -> None:
    """A real run shipped five files of four megabytes that were the same library five times."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    document["pages_reason"] = "one page per chart, deliberately"
    note, html = project(tmp_path, CLEAN_PAGE.replace("</body>", RUNTIME + "</body>"), document)
    (tmp_path / "second.html").write_text(
        CLEAN_PAGE.replace("</body>", RUNTIME + "</body>"), encoding="utf-8", newline="\n"
    )

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "delivery/duplicated-runtime" in rules(report)
    assert "2 pages" in messages(report)


def test_a_library_loaded_by_reference_is_not_a_duplicate(tmp_path: Path) -> None:
    """One load shared by every panel is the shape the skills ask for."""
    table = tmp_path / "orders.csv"
    document = manifest(table)
    document["pages_reason"] = "one page per chart, deliberately"
    linked = CLEAN_PAGE.replace("</head>", '<script src="./lib.js"></script></head>')
    note, html = project(tmp_path, linked, document)
    (tmp_path / "second.html").write_text(linked, encoding="utf-8", newline="\n")

    _code, report = run_with_project(note, html, tmp_path)

    assert "delivery/duplicated-runtime" not in rules(report)


def test_pages_are_found_rather_than_taken_from_the_arguments(tmp_path: Path) -> None:
    """A run that produced five files can pass one, so the check looks instead of trusting."""
    note, html = project(tmp_path, CLEAN_PAGE)
    (tmp_path / "not_passed.html").write_text(CLEAN_PAGE, encoding="utf-8", newline="\n")

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "not_passed.html" in messages(report)


LAID_OUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revenue by channel</title>
<style>
.board { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; }
@media (max-width: 800px) { .board { grid-template-columns: repeat(4, 1fr); } }
</style>
</head>
<body><p>Revenue 25.50 across delivered orders only</p></body>
</html>
"""


def test_a_page_laid_out_for_one_screen_is_refused(tmp_path: Path) -> None:
    """Three absences that say the page was built at one width and never named."""
    bare = LAID_OUT.replace(
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n', ""
    )
    bare = bare.replace("<title>Revenue by channel</title>\n", "")
    bare = bare.replace(
        "@media (max-width: 800px) { .board { grid-template-columns: repeat(4, 1fr); } }\n", ""
    )
    note, html = project(tmp_path, bare)

    code, report = run(note, html)

    assert code == 1
    assert {"layout/no-viewport", "layout/not-responsive", "layout/no-title"} <= rules(report)


def test_a_page_that_was_laid_out_raises_nothing(tmp_path: Path) -> None:
    note, html = project(tmp_path, LAID_OUT)

    _code, report = run(note, html)

    assert not [rule for rule in rules(report) if rule.startswith("layout/")]


def test_a_flexible_track_counts_as_responsive_without_a_media_query(tmp_path: Path) -> None:
    """A grid whose tracks resolve against the space is responsive; it needs no breakpoint."""
    fluid = LAID_OUT.replace(
        "@media (max-width: 800px) { .board { grid-template-columns: repeat(4, 1fr); } }",
        ".board { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }",
    )
    note, html = project(tmp_path, fluid)

    _code, report = run(note, html)

    assert "layout/not-responsive" not in rules(report)


def test_a_page_with_no_stylesheet_of_its_own_is_not_asked_for_media_queries(
    tmp_path: Path,
) -> None:
    """Nothing to judge is not the same as laid out badly."""
    note, html = project(tmp_path, LAID_OUT.replace("<style>", "<!--").replace("</style>", "-->"))

    _code, report = run(note, html)

    assert "layout/not-responsive" not in rules(report)


RANKED = LAID_OUT.replace(
    "<body><p>",
    '<body><section id="hero"></section><section id="trend"></section>'
    '<section id="context"></section><p>',
)


def with_layout(tmp_path: Path, **layout: object) -> dict[str, object]:
    document = manifest(tmp_path / "orders.csv")
    base = document["layout"]
    assert isinstance(base, dict)
    document["layout"] = {**base, **layout}
    return document


def test_several_figures_with_no_declared_reading_order_are_refused(tmp_path: Path) -> None:
    """The one layout decision that leaves no trace in the styling."""
    document = manifest(tmp_path / "orders.csv")
    figures = document["figures"]
    assert isinstance(figures, list)
    figures.append(dict(figures[0], label="Orders"))
    note, html = project(tmp_path, RANKED, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/no-reading-order" in rules(report)


def test_one_figure_needs_no_declared_order(tmp_path: Path) -> None:
    note, html = project(tmp_path, RANKED)

    _code, report = run(note, html)

    assert "layout/no-reading-order" not in rules(report)


def test_panels_out_of_the_declared_order_are_refused(tmp_path: Path) -> None:
    """The reader lands on whatever is first, whatever the ranking said."""
    document = with_layout(tmp_path, panels=["trend", "hero", "context"])
    note, html = project(tmp_path, RANKED, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/reading-order" in rules(report)
    assert "'hero' comes before 'trend'" in messages(report) or "'trend'" in messages(report)


def test_panels_in_the_declared_order_pass(tmp_path: Path) -> None:
    document = with_layout(tmp_path, panels=["hero", "trend", "context"])
    note, html = project(tmp_path, RANKED, document)

    _code, report = run(note, html)

    assert not [rule for rule in rules(report) if rule.startswith("layout/")]


def test_a_declared_panel_the_page_does_not_carry_is_refused(tmp_path: Path) -> None:
    document = with_layout(tmp_path, panels=["hero", "absent-panel"])
    note, html = project(tmp_path, RANKED, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/panel-missing" in rules(report)


def test_two_categories_on_the_same_colour_are_refused(tmp_path: Path) -> None:
    """Two things a reader cannot tell apart wherever they appear together."""
    document = with_layout(
        tmp_path, panels=["hero"], categories={"Online": "#2E86AB", "Retail": "#2e86ab"}
    )
    note, html = project(tmp_path, RANKED, document)

    code, report = run(note, html)

    assert code == 1
    assert "categories/shared-colour" in rules(report)


def test_a_distinct_category_map_passes(tmp_path: Path) -> None:
    document = with_layout(
        tmp_path, panels=["hero"], categories={"Online": "#2E86AB", "Retail": "#A23B72"}
    )
    note, html = project(tmp_path, RANKED, document)

    _code, report = run(note, html)

    assert "categories/shared-colour" not in rules(report)


def test_a_page_nested_three_levels_deep_is_still_found(tmp_path: Path) -> None:
    """A run that writes to output/2026/sales.html is not hiding it."""
    note, html = project(tmp_path, CLEAN_PAGE)
    deep = tmp_path / "output" / "2026"
    deep.mkdir(parents=True)
    (deep / "sales.html").write_text(CLEAN_PAGE, encoding="utf-8", newline="\n")

    code, report = run_with_project(note, html, tmp_path)

    assert code == 1
    assert "sales.html" in messages(report)


def test_every_run_says_what_it_did_not_verify(tmp_path: Path) -> None:
    """A green result that says nothing about its blind spots is read as 'the page is fine'."""
    note, html = project(tmp_path, CLEAN_PAGE)

    _code, report = run(note, html)

    unchecked = report["not_verified"]
    assert isinstance(unchecked, list)
    joined = " ".join(str(item) for item in unchecked)
    assert "overlapping" in joined
    assert "no width was rendered" in joined


def test_a_bounded_container_with_nothing_centring_it_is_refused(tmp_path: Path) -> None:
    """max-width and no automatic margin leaves the page against one edge. Found in a real page."""
    page = CLEAN_PAGE.replace(".board {", ".board { max-width: 1280px;")
    note, html = project(tmp_path, page)

    code, report = run(note, html)

    assert code == 1
    assert "layout/not-centred" in rules(report)
    assert ".board" in messages(report)


def test_a_centred_container_passes(tmp_path: Path) -> None:
    page = CLEAN_PAGE.replace(".board {", ".board { max-width: 1280px; margin: 0 auto;")
    note, html = project(tmp_path, page)

    _code, report = run(note, html)

    assert "layout/not-centred" not in rules(report)


def test_being_left_aligned_on_purpose_is_recorded_rather_than_refused(tmp_path: Path) -> None:
    document = with_layout(tmp_path, left_aligned=True)
    page = CLEAN_PAGE.replace(".board {", ".board { max-width: 1280px;")
    note, html = project(tmp_path, page, document)

    _code, report = run(note, html)

    assert "layout/not-centred" not in rules(report)


def test_an_element_bounded_for_legibility_is_not_a_page_column(tmp_path: Path) -> None:
    """An image or a code block capped for reading is not a container sitting against an edge."""
    page = CLEAN_PAGE.replace(".board {", "img, pre { max-width: 640px; }\n.board {")
    note, html = project(tmp_path, page)

    _code, report = run(note, html)

    assert "layout/not-centred" not in rules(report)


def test_a_responsive_page_with_no_declared_viewports_is_refused(tmp_path: Path) -> None:
    """The page claims to respond to width and nothing says which widths it has to work at."""
    document = manifest(tmp_path / "orders.csv")
    del document["layout"]
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/no-viewports-declared" in rules(report)


def test_a_declared_width_nobody_looked_at_is_refused(tmp_path: Path) -> None:
    document = with_layout(tmp_path, viewports=[375, 768, 1440])
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/not-observed" in rules(report)
    assert "768px" in messages(report)


def test_an_observation_that_says_nothing_is_refused(tmp_path: Path) -> None:
    """'Fine' is not an observation."""
    document = with_layout(tmp_path, viewports=[375], observed=[{"width": 375, "note": "   "}])
    note, html = project(tmp_path, CLEAN_PAGE, document)

    code, report = run(note, html)

    assert code == 1
    assert "layout/observation-empty" in rules(report)


def test_a_page_that_does_not_respond_to_width_is_not_asked_for_observations(
    tmp_path: Path,
) -> None:
    """It fails the responsive rule instead; being asked for both would say the same thing twice."""
    document = manifest(tmp_path / "orders.csv")
    del document["layout"]
    flat = CLEAN_PAGE.replace("repeat(auto-fit, minmax(280px, 1fr))", "1fr 1fr")
    note, html = project(tmp_path, flat, document)

    _code, report = run(note, html)

    assert "layout/no-viewports-declared" not in rules(report)
    assert "layout/not-responsive" in rules(report)


def test_centring_by_a_transform_counts(tmp_path: Path) -> None:
    """A translate is centring, and the rule should not ask for a margin as well."""
    page = CLEAN_PAGE.replace(
        ".board {", ".board { max-width: 1280px; left: 50%; transform: translateX(-50%);"
    )
    note, html = project(tmp_path, page)

    _code, report = run(note, html)

    assert "layout/not-centred" not in rules(report)


def test_centring_from_a_parent_is_a_known_limit_with_a_recorded_way_out(tmp_path: Path) -> None:
    """This is documented rather than fixed, because fixing it needs the document tree.

    A flex or grid ancestor with `justify-content: center` centres a bounded child without any
    declaration appearing in the child's own rule. Reading one rule at a time cannot see that, so
    the check flags it and the manifest carries the decision instead.
    """
    page = CLEAN_PAGE.replace(
        ".board {",
        "body { display: flex; justify-content: center; }\n.board { max-width: 1280px;",
    )
    note, html = project(tmp_path, page)

    _code, report = run(note, html)
    assert "layout/not-centred" in rules(report)
    assert "layout.left_aligned" in messages(report)

    document = with_layout(tmp_path, left_aligned=True)
    note, html = project(tmp_path, page, document)
    _code, report = run(note, html)
    assert "layout/not-centred" not in rules(report)
