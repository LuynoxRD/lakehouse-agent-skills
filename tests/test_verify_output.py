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

CLEAN_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Sales</title></head>
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
<head><meta charset="utf-8"><title>Sales</title></head>
<body>
  <div class="tile">{EMBEDDED_DOCUMENT}</div>
  <p>Revenue 25.50 across delivered orders only</p>
</body>
</html>
"""


def manifest(table: Path, *, value: float = 25.50) -> dict[str, object]:
    """A manifest that declares one figure and the query behind it."""
    return {
        "table": str(table),
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
