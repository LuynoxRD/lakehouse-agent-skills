---
name: spreadsheet-integrity
description: Protects a workbook's structure when a spreadsheet is read or written, by never rewriting the source and by naming exactly what a round trip through a library drops. Use when a task edits, saves or converts an xlsx file, when a workbook carries formulas, named ranges, merged cells, number formats or validation rules, or when a result has to be written back into a spreadsheet someone else maintains.
---

# Spreadsheet integrity

## Overview

A workbook is a document, not a table. Alongside the values it holds formulas, the results those
formulas last produced, number formats, named ranges, merged regions, validation rules,
conditional formatting, charts and sometimes macros. Reading it into a data frame keeps the
values and nothing else, and writing that frame back replaces the document with a picture of its
values.

The damage is quiet. The file still opens, the sheet still has the right columns, and the loss
shows up later in a cell that used to hold a number and now holds nothing.

One rule follows from that:

```
source.xlsx ──read──► work ──write──► output.xlsx
     │
     └── never written to, never the output path
```

## When to Use

Use this skill whenever a task writes to a spreadsheet: editing a workbook, adding a column,
refreshing figures, converting a sheet, or handing a result back in the file it came in.

Use it when reading, too, if the numbers wanted are produced by formulas. A library does not
evaluate formulas; it can only return the value a spreadsheet application last computed and
stored, if one is there.

Do **not** use it for delimited text. A CSV has no structure to lose, and the order of profiling,
cleaning and persisting values belongs to the `etl-before-dashboard` skill. What was and was not
read out of a workbook is a coverage claim and belongs to the `honest-data-limits-disclosure`
skill. This skill owns only what happens to the document.

## Core Process

### Step 1: Inventory the document before touching it

Write the inventory into `docs/data/profile.md` before anything is opened for writing. It is the
same artifact the profile stage always produces, under a heading for the document itself: a
workbook is profiled twice, once for what its values are and once for what its structure is, and
only the second one makes a loss visible later.

Per sheet, record: the number of sheets and their order, which cells hold formulas, whether a
computed result is stored next to each one, the named ranges, the merged ranges, the validation
rules, the conditional formatting rules, the charts and images, the number formats that are not
the default, and whether the file carries macros.

Then answer the question that decides everything downstream: **do the numbers come from formulas
or from typed values?** If they come from formulas, the values read back are the ones a
spreadsheet application computed and saved. Nothing in a library recomputes them.

### Step 2: The source file is read-only

Write the result somewhere else: a new file, or a new sheet in a new file. Leave the source
byte-identical, including its modification time where the platform allows it.

This is not caution for its own sake. An in-place write is a full rewrite of the document by a
library that did not author it, and the parts it does not model are gone at that moment, before
anyone has looked at the result.

### Step 3: If it must be written in place, state the loss list first, then prove it

Sometimes the workbook itself is the deliverable. Then the loss list is published before the
write, not discovered afterwards. Measured against `openpyxl` 3.1.5, over three consecutive
load-and-save cycles:

| Part of the document | What a round trip does |
| --- | --- |
| Charts | kept |
| Pivot tables | kept; the library documents read support so they survive in an existing file |
| Conditional formatting | kept |
| Data validation rules | kept |
| Defined and named ranges | kept |
| Merged cell ranges | kept |
| Number formats | kept |
| **The stored result of every formula** | **always dropped** |
| Shapes and other drawing objects | dropped |
| Embedded images | dropped when the imaging dependency is absent, and nothing warns |
| Macros | dropped unless the file is opened with the option that preserves them, which keeps them as an opaque blob rather than something to edit |
| Rich text inside a cell | flattened unless rich text is asked for explicitly |

The reputation of these libraries is that they wreck workbooks. Measured, they keep more than
that suggests, and the one thing they always drop is the one nothing warns about. A cell holding
`=B2*C2` and the number `30` comes back holding `=B2*C2` and nothing. Every later reader asking
for values instead of formulas gets an empty cell where a number used to be, and an empty cell
averages, sums and charts as absence, not as an error.

So the in-place path has three parts, in this order: write the loss list into the cleaning log,
make the change, then reopen the written file and compare it against the Step 1 inventory,
including a values-only read of at least one formula cell. "It saved without an error" is not
evidence.

### Step 4: Respect the ceilings, and do not trust the library to enforce them

A worksheet holds at most **1,048,576 rows by 16,384 columns**. A library may enforce one limit
and not the other: `openpyxl` refuses a row past the last one with an explicit error, and accepts
a column past the last one without a word, writing a cell address beyond the grid into a file
that will not open correctly.

Check the shape against both ceilings before writing, rather than relying on an exception that
only exists for one of them. Data that does not fit does not belong in a worksheet; persist it as
a columnar table and keep the workbook for the summary.

### Step 5: Hand back what changed, in the file and in words

Alongside the output, state which sheets were written, which were copied untouched, and anything
from the loss list that actually applied to this workbook. A loss that applied and went unsaid is
the failure this skill exists to prevent.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "The library reads and writes Excel, so a round trip is safe." | It reads a rectangle of values and writes a new document. What made the file a workbook was never in the frame to write back. |
| "I only changed one cell." | The write rebuilds the whole document. The blast radius is the file, not the cell. |
| "The formulas are still there, so nothing was lost." | The formulas are there and their results are not. The next reader asking for values gets empty cells. |
| "These libraries destroy workbooks anyway, so there is nothing left to protect." | Measured, they keep charts, pivot tables, validation, names, merges and formats. Believing the exaggeration is what stops anyone from checking the one real loss. |
| "Whoever opens it in a spreadsheet will see the numbers recalculated." | Only if a spreadsheet opens it. A pipeline reading values first gets nothing, and reports it as missing data. |
| "It is a copy, so the original is safe." | A copy missing the stored results is a copy of the wrong thing, and it is the copy everyone will use. |
| "There is a backup." | A backup makes the loss recoverable, not visible. Nobody restores a backup for a problem they never noticed. |
| "The file is small, so the row limit is irrelevant." | The limit that bites is the column one, because nothing raises an error when it is crossed. |

## Red Flags

Stop when any of these is true:

- The output path equals the input path.
- The source workbook's modification time changed during the work.
- A values-only read returns nothing where a number was expected.
- A data frame was written to an xlsx file and described as an edit to the original.
- A macro-enabled workbook was saved without the option that preserves macros.
- A column index above 16,384 or a row index above 1,048,576 was written or computed.
- The work is finished and no inventory of the original exists to compare against.

## Verification

- [ ] `docs/data/profile.md` carries a section for the document itself, listing sheets, formulas,
      names, merges, validation, conditional formatting, charts and number formats found in the
      original.
- [ ] The source file is byte-identical to what arrived, and the output was written elsewhere.
- [ ] If the write was in place, the loss list appeared before the write and every item that
      applied to this workbook is named in the answer.
- [ ] The written file was reopened and compared against the inventory, including a values-only
      read of at least one formula cell.
- [ ] The shape was checked against both worksheet ceilings, not only the one that raises.
- [ ] Anything the round trip dropped is stated in the answer, not only in the log.
