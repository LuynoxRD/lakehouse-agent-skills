---
name: document-extraction-integrity
description: Gets data out of a document before anything treats it as a dataset, deciding first whether the file carries a text layer or has to be recognised, then checking the extracted values against the page they came from. Use when a source is a PDF, a word-processor file, a scan or a photograph of a receipt or a form, when a table has to be pulled off a page, when extracted text arrives with its columns interleaved, or when a number was read by recognition rather than typed.
---

# Document extraction integrity

## Overview

A document is not a dataset and it is not a file full of text either. It is a page: marks placed
at coordinates, whose reading order a human reconstructs by looking and a program has to guess.

That guess is where the damage happens, and it never announces itself. A two-column page comes
back interleaved. A table's amounts arrive in one block and its labels in another, and pairing
them by position shifts every row after the first wrapped line. A subtotal is counted as a line
item. A page that was a photograph returns nothing at all, and a run that adds up "the document"
adds up the pages that happened to have text.

Everything downstream is ordinary data work. This is the step that decides whether the data it
starts from is what the page says.

```
document → text layer or not? → extract → check against the page → hand off by shape
                    │
                    └── no text layer → recognise, and treat every value as a measurement
```

## When to Use

Use this skill whenever the source is a document rather than a dataset: a PDF, a word-processor
file, a scan, a photograph of a receipt, an invoice, a form.

Use it before deciding anything about shape. Whether the content is a table or prose cannot be
answered until the content exists as text, which is what makes this the step before the
`structured-vs-unstructured-routing` skill rather than a part of it.

Do **not** use it for a spreadsheet, which is a document with a grid already in it and belongs to
the `spreadsheet-integrity` skill. Once text exists, what its shape is belongs to
`structured-vs-unstructured-routing`, what happens to the values belongs to
`etl-before-dashboard`, and how much of the source went unread belongs to
`honest-data-limits-disclosure`.

## Core Process

### Step 1: Ask what kind of document this is, before extracting anything

Two questions, and the second is the one that decides the whole path.

1. **How many pages, and what is on them?** Page count, and whether they look uniform.
2. **Does each page carry a text layer?** Extract text per page and count the characters. A page
   built from text returns hundreds; a page that is a photograph returns none. **Count per page,
   never for the file**, because a document is routinely half one and half the other, and a
   whole-file count hides it completely.

Record both in `docs/data/profile.md`, per page. "The PDF has 14 pages, 11 with a text layer and
3 without" is a profile entry, and it is the sentence that stops a later total from being wrong.

### Step 2: With a text layer, extract, then fix the reading order rather than trusting it

Text in a page's content stream is in the order the marks were drawn, which is not the order a
person reads. Do not assume the two agree; check.

- **Extract with layout awareness where the tool offers it**, so columns and cells survive. Plain
  text extraction throws away the geometry that made the page readable.
- **Never pair two extracted lists by position.** A column of amounts and a column of labels come
  back as separate runs, and one wrapped description makes the lists different lengths, so every
  pair after the wrap is wrong while every value in it is real. Pair by coordinate, or by a key
  that appears in both.
- **Separate line items from summary rows.** A subtotal, a tax line and a total are numbers on the
  page that are not observations. Adding every number found is the same error as counting a Total
  row in a spreadsheet, and it is easier to make here because nothing is labelled.

### Step 3: With no text layer, recognise, and treat every value as a measurement

This is where a scan lands, and where a photograph of a receipt lands, which is the same problem
wearing a different extension.

- **Recognition has an error rate.** A recognised number is a measurement with uncertainty, not a
  read. Keep the per-value confidence the tool reports and put it in the record.
- **Digits are the worst case**, because a wrong digit is invisible downstream. Zero against the
  letter O, one against seven, five against S, eight against B: none of these produces something
  that looks wrong in a total.
- **Check the image before blaming the recogniser.** Resolution, skew, crop, glare and shadow
  decide the result more than the tool does. Say what the image was; a photograph taken at an
  angle in bad light has an error rate nothing downstream can repair.
- **Use the document's own checksum.** A receipt or an invoice prints its total. Sum the line
  items you recognised and compare. Agreement is real evidence; disagreement names the failure
  before anybody acts on it. A document with no internal check needs a second pass or a human.
- **Recognition through a hosted service is a transfer of the image.** A receipt carries a name, a
  card fragment, an address. Say where recognition runs, including when the answer is that it runs
  locally and nothing leaves, and take a hosted path through the `data-privacy-before-llm` skill
  first.

### Step 4: Say what the extraction cost, per page

Extraction is lossy and the loss is countable. Report pages read of pages present, pages with no
text layer, tables found, and rows dropped or merged. Those numbers are the input to the
`honest-data-limits-disclosure` skill, and without them a total silently covers whatever happened
to parse.

### Step 5: Check the extracted values against the page, not against the extraction

Reading the extraction back proves the extractor is consistent with itself, which it always is.
The check that means something compares against the source:

- Take a handful of values from different parts of the document, including one from the row after
  the first wrap, and read them off the rendered page.
- Compare any computed total with the total the document prints.
- Confirm the row count you extracted against the row count you can see.

Only then does the result become data, and only then does the shape question belong to the routing
skill.

> The shared reference `references/format-strategy.md` puts every format this pack meets side by side, with what reads it and what bites. It is the view to take when a source arrives in a format you have not handled before. A per-skill install does not carry it; without it you lose the comparison, not the formats this skill needs, which are above.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "The extraction returned text, so it worked." | It returned text in the order the marks were drawn. Whether that is the order the page reads is the thing you have not checked yet. |
| "The tool handles tables." | Some tables. Ruled ones mostly, unruled ones sometimes, ones spanning pages rarely. Which kind is on your page is a question with an answer. |
| "The numbers look right." | They are real numbers off the real page. The failure here is pairing them with the wrong labels, which leaves every value looking perfectly right. |
| "I summed everything on the page." | Then you added the subtotal and the total to the line items. The page prints its own total so you can catch exactly that. |
| "It is a clear photo, recognition will be fine." | Clear to you, at an angle, in shadow, at whatever resolution the phone chose. Say what the image was and keep the confidence values. |
| "Recognition got 99% of characters." | An invoice has a few dozen digits that matter. At 99% per character you should expect to be wrong somewhere in them, and you will not be able to see where. |
| "The scanned pages were empty anyway." | They returned no text. What is on them is a separate question, and answering it with silence is how a document gets reported on half-read. |
| "It is only a receipt." | It is a receipt with a name and an address on it, about to be sent to a service. That is the same decision as any other transfer. |

## Red Flags

Stop when any of these is true:

- Text was extracted and no per-page character count was taken.
- Two extracted lists are being paired by position.
- Every number on a page was summed without separating line items from summary rows.
- A page returned no text and the answer does not say so.
- A recognised value entered a total with no confidence recorded and no checksum compared.
- A document that prints its own total was extracted and the total was never checked against it.
- An image went to a hosted recogniser and the answer does not say where recognition ran.
- The extracted table has more or fewer rows than the page shows and nobody counted.

## Verification

- [ ] `docs/data/profile.md` records, per page, whether a text layer was found and how many
      characters it held.
- [ ] Values were paired by coordinate or by a shared key, never by position in two lists.
- [ ] Line items are separated from subtotals, taxes and totals, and the separation is stated.
- [ ] Any total computed from the extraction was compared with the total the document prints, and
      the comparison is in the answer.
- [ ] For recognised values, the confidence is recorded and the image conditions are described.
- [ ] The answer says where recognition ran, on this machine or at a service, even when nothing
      left the machine.
- [ ] Pages read out of pages present appears in the answer, not only in the log.
- [ ] At least one extracted value from after the first wrapped or merged row was read back off
      the rendered page and matched.
