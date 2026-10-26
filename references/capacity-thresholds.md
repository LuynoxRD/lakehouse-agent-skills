# Capacity thresholds

The hard limits that decide whether an approach works at all, collected in one place. Each skill
that needs one of these keeps it inline as well, because a per-skill install does not carry this
directory; what this file adds is the whole set side by side, which is what you want when
choosing between two approaches rather than following one.

Every number here was verified by running the tool named, not recalled. Where a limit is
documented but unverified, it says so.

## Worksheets

| Limit | Value | Verified behaviour |
| --- | --- | --- |
| Rows per worksheet | **1,048,576** | `openpyxl` 3.1.5 raises `ValueError` naming the limit when a row past it is addressed. |
| Columns per worksheet | **16,384** (the last is `XFD`) | `openpyxl` 3.1.5 **does not check this**. Addressing column 16,385 returns a cell called `XFE1` and writes it without an error, producing a file a spreadsheet cannot open correctly. |

The asymmetry is the point: one limit fails loudly and the other fails silently, so the column
count has to be checked in code rather than left to an exception.

### What a round trip through a spreadsheet library costs

Measured on `openpyxl` 3.1.5 over three consecutive load-and-save cycles: charts, pivot tables,
conditional formatting, data validation, defined names, merged ranges and number formats all
survive. **The stored result of every formula is always dropped.** A cell holding a formula and
the number it produced comes back holding the formula and nothing, so any later read that asks
for values instead of formulas gets an empty cell where a number used to be.

## Columnar files

| Property | What is guaranteed |
| --- | --- |
| Schema and types | Recorded in the file footer and returned unchanged. A 32-bit integer written is a 32-bit integer read. |
| Per-column statistics | **Optional.** Usually written, and switchable off at write time, in which case the file has none. Verified with `pyarrow` 25.0.1: writing with statistics disabled leaves the column metadata reporting no statistics. An optimisation that may be present, never proof that a scan was avoided. |
| Appending to a finished file | **Not an operation.** The footer is written after the data and closes the file, so more data means another file. |
| Schema across a directory of files | The reader takes the schema from the **first file in name order**. A column that only later files have is dropped from the result with no error, no warning and no nulls; the same column in the first file survives with older rows nulled. Verified with `pyarrow` 25.0.1. Whether a field survives a read therefore depends on the file names the writer chose. |

## Query engine extensions

Verified on DuckDB 1.5.5, 1.5.6 and 2.0.0, in the Python package on Linux and Windows and in the
1.5.5 and 2.0.0 command-line binaries; 2.0 changed none of it. On a clean install, an
`ATTACH … (TYPE postgres)` installs `postgres_scanner` from the extension repository before it
even tries to connect.

| Bundled and loaded already | Fetched over the network on first use |
| --- | --- |
| `json`, `parquet` | `iceberg`, `delta`, `excel`, `httpfs`, `postgres_scanner`, `sqlite_scanner` |

To check a machine, read `install_mode` in `duckdb_extensions()`: `STATICALLY_LINKED` is bundled,
`REPOSITORY` was downloaded. `installed = true` alone says neither, because an extension an
earlier statement fetched reads as installed from then on.

An extension in the right-hand column is downloaded and installed **without prompting** when a
statement first needs it, and persists under the user's home directory. Once it is on disk,
disabling automatic installation no longer prevents its use, so the check belongs before the first
statement rather than after. On a machine that is offline, audited, or subject to a policy about
what it downloads, that is a blocker rather than a detail.

Attach syntax that was verified at the same time: the options require parentheses, as in
`ATTACH '<connection>' AS live (TYPE postgres, READ_ONLY)`. Without them the statement does not
parse, which is the safe failure. An option the engine does not recognise raises an error naming
it, which is how a real option is told apart from a remembered one.

## When a directory of files stops being enough

Not a capacity threshold in rows or bytes. The trigger is always **change**, never size:
correcting or deleting individual rows, more than one writer, a column that has to survive being
added, two reads of the same path having to agree, or needing the data as it stood earlier. A
dataset that only grows, is written once and read many times, does not cross any of these lines
however large it gets.
