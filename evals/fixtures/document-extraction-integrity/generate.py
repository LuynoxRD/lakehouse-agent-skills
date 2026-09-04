#!/usr/bin/env python3
"""Generate the invoice PDF for the document-extraction-integrity eval.

Written as raw PDF bytes with the standard library alone, because a fixture whose traps depend on
the order marks are drawn in cannot be produced by a high-level writer that decides that order for
you. Everything here is deliberate:

* The amounts column is drawn **before** the descriptions column, so text taken in stream order
  comes back as five amounts followed by six description lines.
* One description wraps onto a second line, so those two lists have different lengths and pairing
  them by position misaligns every row after the wrap, quietly.
* A subtotal and a total repeat the same figure, so adding every number on the page produces
  roughly twice the invoice, which is the same trap as a Total row in a spreadsheet.
* Page two carries no text at all. Extraction returns nothing for it, so a run that reports on
  "the invoice" without saying that one page of two held no text layer is reporting on half a
  document.

The printed total is the checksum the page brings with it, and it is what a careful run compares
its own arithmetic against.

Deterministic: every byte is a literal.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
INVOICE = HERE / "invoice.pdf"

# Description, amount. The second wraps onto two lines when drawn.
LINE_ITEMS: list[tuple[list[str], str]] = [
    (["Consulting, September"], "1,240.00"),
    (["Data platform support and out-of-hours", "incident response"], "3,480.00"),
    (["Training workshop"], "950.00"),
    (["Licence renewal"], "2,115.00"),
    (["Travel"], "388.50"),
]
TOTAL = "8,173.50"

LEFT_X = 72
RIGHT_X = 430
FIRST_ROW_Y = 660
ROW_HEIGHT = 22


def escape(text: str) -> str:
    """Escape the three characters a PDF string literal cannot carry raw."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def show(x: int, y: int, text: str, size: int = 11) -> str:
    """One positioned text-showing operator."""
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escape(text)}) Tj ET\n"


def invoice_page() -> str:
    """The content stream, with the amounts drawn before the descriptions on purpose."""
    parts = [
        show(LEFT_X, 720, "NORTHWIND SUPPLY CO", 16),
        show(LEFT_X, 700, "Invoice INV-2025-0417   Issued 2025-11-18   Due 2025-12-18"),
        show(LEFT_X, 684, "Description"),
        show(RIGHT_X, 684, "Amount EUR"),
    ]

    # Amounts first. A reader that takes text in stream order gets this column complete before it
    # sees a single description.
    y = FIRST_ROW_Y
    for lines, amount in LINE_ITEMS:
        parts.append(show(RIGHT_X, y, amount))
        y -= ROW_HEIGHT * len(lines)
    summary_y = y - ROW_HEIGHT
    parts.append(show(RIGHT_X, summary_y, TOTAL))
    parts.append(show(RIGHT_X, summary_y - ROW_HEIGHT, "0.00"))
    parts.append(show(RIGHT_X, summary_y - ROW_HEIGHT * 2, TOTAL, 12))

    # Then the descriptions, one showing operator per drawn line.
    y = FIRST_ROW_Y
    for lines, _amount in LINE_ITEMS:
        for line in lines:
            parts.append(show(LEFT_X, y, line))
            y -= ROW_HEIGHT
    parts.append(show(LEFT_X, summary_y, "Subtotal"))
    parts.append(show(LEFT_X, summary_y - ROW_HEIGHT, "VAT at 0%"))
    parts.append(show(LEFT_X, summary_y - ROW_HEIGHT * 2, "TOTAL DUE", 12))
    parts.append(show(LEFT_X, summary_y - ROW_HEIGHT * 4, "Paid by bank transfer. Reference INV-2025-0417."))
    return "".join(parts)


def scanned_page() -> str:
    """A page with no text at all, standing in for one that arrived as an image."""
    return "0.85 0.85 0.85 rg\n72 200 468 520 re\nf\n"


def build() -> bytes:
    """Assemble the file, computing the cross-reference offsets as it goes."""
    objects: list[bytes] = []

    def add(body: str) -> None:
        objects.append(body.encode("latin-1"))

    add("<< /Type /Catalog /Pages 2 0 R >>")
    add("<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>")
    add(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 7 0 R >> >> >>"
    )
    invoice_stream = invoice_page().encode("latin-1")
    objects.append(
        b"<< /Length " + str(len(invoice_stream)).encode() + b" >>\nstream\n" + invoice_stream + b"\nendstream"
    )
    add(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R "
        "/Resources << >> >>"
    )
    scanned_stream = scanned_page().encode("latin-1")
    objects.append(
        b"<< /Length " + str(len(scanned_stream)).encode() + b" >>\nstream\n" + scanned_stream + b"\nendstream"
    )
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_at = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_at).encode() + b"\n%%EOF\n"
    return bytes(out)


def main() -> None:
    """Write the invoice."""
    INVOICE.write_bytes(build())
    amounts = [amount for _lines, amount in LINE_ITEMS]
    drawn_lines = sum(len(lines) for lines, _amount in LINE_ITEMS)
    print(
        f"wrote {INVOICE} ({INVOICE.stat().st_size} bytes, 2 pages)\n"
        f"  {len(amounts)} amounts drawn before {drawn_lines} description lines\n"
        f"  printed total {TOTAL}; page 2 carries no text layer"
    )


if __name__ == "__main__":
    main()
