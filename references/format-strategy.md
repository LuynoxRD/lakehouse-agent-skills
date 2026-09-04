# Format to strategy

What to reach for when a source arrives in a given format, and what each one costs. The value of
this file is the breadth: seeing every format beside every other is what tells you whether a
source is one step from a table or three, and no single skill can hold that view.

Each skill keeps inline the formats it cannot work without, because a per-skill install does not
carry this directory. What is lost without this file is the comparison, not any instruction.

The three columns that matter are the same every time. **What it is** decides which skill owns it.
**What reads it** decides whether anything has to be installed. **What bites** is the part nobody
finds out until the numbers are already wrong.

## Tabular, with or without a schema

| Format | What reads it | What bites |
| --- | --- | --- |
| `csv` | Standard library, any query engine, no extension | No types at all, so every reader guesses again. Delimiter, quoting, encoding and decimal separator are all undeclared. The `etl-before-dashboard` trap table is entirely about this. |
| `tsv` | The same, with the delimiter stated | Same as CSV, plus tabs inside values are indistinguishable from separators when quoting is absent. |
| `xlsx` | A spreadsheet library; a query engine needs an extension that is **fetched over the network on first use** | A workbook is a document, not a table. Round trips drop the stored result of every formula, and the column ceiling is not enforced by the writer. See `capacity-thresholds.md` and the `spreadsheet-integrity` skill. |
| `ods` | Not the same library as `xlsx` | The common spreadsheet library is `xlsx` and `xlsm` only. An `.ods` needs a different reader, and reaching for the familiar one produces an invalid-file error that reads like a corrupt file. |
| `parquet` | Query engines and the columnar library directly, no extension | Types survive exactly, which is the point. Statistics are optional, appending is not an operation, and a directory of files takes its schema from the first file in name order. See `capacity-thresholds.md`. |
| `orc` | The columnar library reads and writes it; a query engine generally needs an extension | Same family as Parquet and the same guarantees about types, but far less universally supported. Converting once to Parquet is usually cheaper than carrying the dependency. |
| `avro` | Needs an extension in a query engine, **fetched over the network on first use** | Row-oriented, so it is a transport format rather than an analytical one. Convert on arrival; querying it repeatedly reads whole records to answer column questions. |

## Semi-structured

All of these hold a shape that varies between records. The decision they share belongs to the
`structured-vs-unstructured-routing` skill: count how many keys appear in **every** record before
deciding this is not simply a table written awkwardly.

| Format | What reads it | What bites |
| --- | --- | --- |
| `json`, `jsonl`, `ndjson` | Standard library; a query engine reads it with no extension | A field present in only some records still becomes a column with nulls elsewhere, which is a feature and hides how rare it was. Report the share. Newline-delimited is streamable, a single top-level array is not. |
| `yaml` | Third party, **not** in the standard library | Written by people, so it carries their mistakes. Unquoted values are typed by guess, a bare colon and space ends a value, and version 1.1 readers turn `no`, `on` and `off` into booleans. That last one silently rewrites country codes. |
| `toml` | Standard library, read-only | Types are declared, which makes it the least surprising of these. It is a configuration format; a table stored in one is a table that outgrew it. |
| `ini` | Standard library | Every value is a string and there is no nesting. Duplicate keys resolve by a rule nobody remembers. |
| `xml` | Standard library | Attributes and child elements both carry data, so "flatten it" is ambiguous before you decide which is which. Namespaces make tag names longer than the tags you can see. Parse with a reader that does not resolve external entities. |
| `html` | Standard library for parsing, a table reader for tables | A page's tables are the easy part. Whether the numbers in them are the numbers rendered depends on whether the page computed anything after loading. |

## Documents, which are not text until something extracts it

The data does not exist as text yet, so the shape question cannot be asked. This is the step
before routing, and it belongs to the `document-extraction-integrity` skill.

| Format | What reads it | What bites |
| --- | --- | --- |
| `pdf` with a text layer | An extraction library, third party | Text comes back in the order the marks were drawn, not the order the page reads. Columns interleave, and pairing two extracted lists by position misaligns everything after the first wrapped line while every value stays real. |
| `pdf` without a text layer | Recognition, and a decision about where it runs | Extraction returns nothing and says nothing. Count characters **per page**, never per file, because a document is routinely half one and half the other. |
| `docx` | An extraction library, third party | The file is a zip of XML. Tables, footnotes, headers and tracked changes are separate parts, and a naive text read can splice a footnote number into a total. |
| A photograph of a receipt or a form | Recognition, exactly as for a scan | The same problem as a scanned PDF with a different extension. Digits are the worst case, the document's printed total is the checksum to check against, and the image itself is personal data before it is anything else. |

## Not a source for this pipeline

Audio, video, executables and disk images are not datasets and no skill here treats them as one.

The one narrow case is where **the data is the metadata**: capture timestamps on a set of
photographs, durations across a media library. That is a tabular source that happens to live
inside binary containers, so extract the metadata into a table and everything after it is ordinary
work. It is not format support, and it does not make the container a source.

## The rule underneath the table

Two questions decide the strategy, in this order, and neither is about the extension.

1. **Is the data already text?** If not, extraction comes first and it is lossy in ways that have
   to be counted.
2. **Does the format declare its types?** If it does, they survive and nobody guesses. If it does
   not, every reader guesses separately and two of them will eventually disagree, which is why the
   pipeline persists to a format that declares them and reads from there afterwards.
