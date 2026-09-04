#!/usr/bin/env python3
"""Generate the workbook for the spreadsheet-integrity eval.

The trap only exists if the file carries what a spreadsheet application would have stored:
formulas *and* the results they last produced. A library never computes a result, so writing the
workbook is not enough. After saving, the sheet XML is reopened and the cached values are written
in beside their formulas, which is what makes a round trip measurably lossy rather than
theoretically lossy.

Everything else in the file is there to be preserved: a named range, merged cells, validation,
conditional formatting, a chart and a non-default number format all survive a round trip, so a
run that reports them as casualties is guessing rather than checking.

Needs the ``fixtures`` extra (``uv sync --extra fixtures``). Deterministic: every value is fixed.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
WORKBOOK = HERE / "quarterly_budget.xlsx"

# Department, forecast, actual. The variance column is a formula whose result is cached.
ROWS = [
    ("Platform", 120000, 131400),
    ("Data", 86000, 79250),
    ("Support", 54000, 54000),
    ("Research", 97500, 112300),
    ("Operations", 143000, 138900),
]


def build() -> None:
    """Write the workbook with every structural feature the loss list mentions."""
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.workbook.defined_name import DefinedName
    from openpyxl.worksheet.datavalidation import DataValidation

    book = Workbook()
    sheet = book.active
    sheet.title = "Budget"
    sheet.append(["department", "forecast", "actual", "variance", "over_budget"])
    for index, (department, forecast, actual) in enumerate(ROWS, start=2):
        sheet.append([department, forecast, actual])
        sheet[f"D{index}"] = f"=C{index}-B{index}"
        sheet[f"E{index}"] = f'=IF(D{index}>0,"yes","no")'
        for column in ("B", "C", "D"):
            sheet[f"{column}{index}"].number_format = "#,##0.00"

    total_row = len(ROWS) + 2
    sheet[f"A{total_row}"] = "Total"
    sheet[f"B{total_row}"] = f"=SUM(B2:B{total_row - 1})"
    sheet[f"C{total_row}"] = f"=SUM(C2:C{total_row - 1})"
    sheet[f"D{total_row}"] = f"=SUM(D2:D{total_row - 1})"

    sheet.merge_cells(f"A{total_row + 2}:E{total_row + 2}")
    sheet[f"A{total_row + 2}"] = "Figures are provisional until the quarter closes."

    validation = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
    sheet.add_data_validation(validation)
    validation.add(f"E2:E{total_row - 1}")

    sheet.conditional_formatting.add(
        f"D2:D{total_row - 1}",
        CellIsRule(operator="lessThan", formula=["0"], stopIfTrue=False),
    )
    book.defined_names.add(DefinedName("BudgetTable", attr_text=f"Budget!$A$1:$E${total_row}"))

    chart = BarChart()
    chart.title = "Forecast against actual"
    chart.add_data(Reference(sheet, min_col=2, max_col=3, min_row=1, max_row=total_row - 1))
    chart.set_categories(Reference(sheet, min_col=1, min_row=2, max_row=total_row - 1))
    sheet.add_chart(chart, "G2")

    notes = book.create_sheet("Notes")
    notes.append(["The variance column is computed in the sheet, not typed."])
    notes.append(["Refreshed manually at the end of each month."])

    book.save(WORKBOOK)


def cached_results() -> dict[str, str]:
    """The value a spreadsheet application would have stored next to each formula."""
    values: dict[str, str] = {}
    for index, (_department, forecast, actual) in enumerate(ROWS, start=2):
        values[f"D{index}"] = str(actual - forecast)
    total_row = len(ROWS) + 2
    values[f"B{total_row}"] = str(sum(forecast for _d, forecast, _a in ROWS))
    values[f"C{total_row}"] = str(sum(actual for _d, _f, actual in ROWS))
    values[f"D{total_row}"] = str(sum(actual - forecast for _d, forecast, actual in ROWS))
    return values


def inject_cached_values() -> int:
    """Store each formula's last result beside it, the way a spreadsheet would have.

    A written workbook holds ``<f>C2-B2</f>`` and no value, so a round trip has nothing to drop
    and the fixture would prove nothing. Rewriting the archive with ``<v>`` elements produces the
    file that arrives from a person: formula and result together, only one of which survives.
    """
    values = cached_results()
    with zipfile.ZipFile(WORKBOOK) as archive:
        members = [(item, archive.read(item.filename)) for item in archive.infolist()]

    injected = 0
    rewritten: list[tuple[zipfile.ZipInfo, bytes]] = []
    for item, payload in members:
        if item.filename.endswith("worksheets/sheet1.xml"):
            text = payload.decode("utf-8")
            for cell, result in values.items():
                pattern = re.compile(
                    rf'(<c r="{cell}"[^>]*>)(<f>[^<]*</f>)(?!<v>)', re.IGNORECASE
                )
                text, count = pattern.subn(rf"\1\2<v>{result}</v>", text)
                injected += count
            payload = text.encode("utf-8")
        rewritten.append((item, payload))

    with zipfile.ZipFile(WORKBOOK, "w", zipfile.ZIP_DEFLATED) as archive:
        for item, payload in rewritten:
            archive.writestr(item, payload)
    return injected


def main() -> None:
    """Write the workbook, then make its formulas carry the results they produced."""
    build()
    injected = inject_cached_values()
    if injected != len(cached_results()):
        raise SystemExit(
            f"expected {len(cached_results())} cached values, wrote {injected}; "
            "the sheet XML did not have the shape this generator assumes"
        )
    print(f"wrote {WORKBOOK} ({WORKBOOK.stat().st_size} bytes, {injected} cached results)")


if __name__ == "__main__":
    main()
