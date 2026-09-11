"""
Tests for services/parsers/pdf_parser.py.

Two kinds of test live here:

  * End-to-end tests that build a real PDF with reportlab and run
    parse_pdf() over the bytes. These cover the paths that depend on
    layout — most importantly, telling a debit from a credit when only
    one of the two columns carries a value.
  * Unit tests on the flat-text fallback, which takes a plain string
    and needs no PDF at all.

The layout names (A/B/C/D) match the ones in the parser's docstring.
"""

import io

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.app.services.parsers.pdf_parser import (
    PdfParseError,
    _parse_text_transactions,
    _split_trailing_amounts,
    parse_pdf,
)

# Column x positions (points from the left edge) used to draw the test
# statements. Money columns are right-aligned, the way a real bank
# statement lays them out.
_LEFT_MARGIN = 40
_TOP = 720
_ROW_HEIGHT = 18


def _draw_statement(
    headers: list[tuple[str, float, str]],
    rows: list[list[str]],
    title: str = "Bank Statement",
) -> bytes:
    """
    Render a single-page statement PDF.

    headers: (label, x position, "left" | "right") per column.
    rows: cell text per column; "" leaves the cell blank.
    """

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(_LEFT_MARGIN, _TOP + 30, title)

    def write(text: str, x: float, y: float, align: str) -> None:
        if not text:
            return
        if align == "right":
            pdf.drawRightString(x, y, text)
        else:
            pdf.drawString(x, y, text)

    pdf.setFont("Helvetica-Bold", 9)
    for label, x, align in headers:
        write(label, x, _TOP, align)

    pdf.setFont("Helvetica", 9)
    for index, row in enumerate(rows):
        y = _TOP - _ROW_HEIGHT * (index + 1)
        for value, (_, x, align) in zip(row, headers):
            write(value, x, y, align)

    pdf.save()
    return buffer.getvalue()


def _by_description(transactions: list[dict]) -> dict[str, dict]:
    return {t["description"]: t for t in transactions}


# =========================================================
# Layout A/B — separate debit and credit columns
# =========================================================

_DEBIT_CREDIT_HEADERS = [
    ("Date", 40, "left"),
    ("Description", 110, "left"),
    ("Debit", 380, "right"),
    ("Credit", 450, "right"),
    ("Balance", 540, "right"),
]


def test_debit_credit_layout_separates_spend_from_earn():
    """
    The regression that matters most: in a debit/credit statement the
    amounts are unsigned, and the ONLY thing distinguishing an expense
    from income is which column the number sits in. Reading these as
    all-earn (or all-spend) silently inverts the user's entire budget.
    """

    pdf_bytes = _draw_statement(
        _DEBIT_CREDIT_HEADERS,
        [
            ["01/08/2026", "Salary Credit", "", "1500.00", "6500.00"],
            ["02/08/2026", "Grocery Store", "86.42", "", "6413.58"],
            ["03/08/2026", "Rent Payment", "1200.00", "", "5213.58"],
            ["04/08/2026", "Interest", "", "12.50", "5226.08"],
        ],
    )

    parsed = _by_description(parse_pdf(pdf_bytes))

    assert parsed["Salary Credit"]["type"] == "earn"
    assert parsed["Salary Credit"]["amount"] == 1500.00

    assert parsed["Grocery Store"]["type"] == "spend"
    assert parsed["Grocery Store"]["amount"] == 86.42

    assert parsed["Rent Payment"]["type"] == "spend"
    assert parsed["Interest"]["type"] == "earn"


def test_debit_credit_layout_parses_every_row():
    pdf_bytes = _draw_statement(
        _DEBIT_CREDIT_HEADERS,
        [
            ["01/08/2026", "Salary Credit", "", "1500.00", "6500.00"],
            ["02/08/2026", "Grocery Store", "86.42", "", "6413.58"],
            ["03/08/2026", "Rent Payment", "1200.00", "", "5213.58"],
        ],
    )

    assert len(parse_pdf(pdf_bytes)) == 3


def test_value_date_column_does_not_override_transaction_date():
    """
    "Date" and "Value Date" both normalize to the canonical header
    "date". The first column is the transaction date and must win.
    """

    pdf_bytes = _draw_statement(
        [
            ("Date", 40, "left"),
            ("Value Date", 105, "left"),
            ("Description", 175, "left"),
            ("Debit", 400, "right"),
            ("Credit", 470, "right"),
            ("Balance", 555, "right"),
        ],
        [
            ["02/08/2026", "05/08/2026", "Grocery Store", "86.42", "", "4913.58"],
        ],
    )

    transactions = parse_pdf(pdf_bytes)

    assert len(transactions) == 1
    assert transactions[0]["date"] == "2026-08-02"


# =========================================================
# Layout C — one signed amount column
# =========================================================

def test_signed_amount_layout():
    pdf_bytes = _draw_statement(
        [
            ("Date", 40, "left"),
            ("Description", 110, "left"),
            ("Amount", 430, "right"),
            ("Balance", 540, "right"),
        ],
        [
            ["01-08-2026", "Salary", "1500.00", "6500.00"],
            ["02-08-2026", "Grocery Store", "-86.42", "6413.58"],
        ],
    )

    parsed = _by_description(parse_pdf(pdf_bytes))

    assert parsed["Salary"]["type"] == "earn"
    assert parsed["Grocery Store"]["type"] == "spend"
    # Amount is always stored as a positive magnitude; direction is
    # carried by `type`. Same invariant as docs/data_model.md.
    assert parsed["Grocery Store"]["amount"] == 86.42


# =========================================================
# Layout D — explicit type column
# =========================================================

def test_explicit_type_column_layout():
    pdf_bytes = _draw_statement(
        [
            ("Date", 40, "left"),
            ("Narration", 110, "left"),
            ("Type", 330, "left"),
            ("Amount", 450, "right"),
            ("Balance", 540, "right"),
        ],
        [
            ["01/08/2026", "Monthly Salary", "Credit", "1500.00", "6500.00"],
            ["02/08/2026", "Grocery Store", "Debit", "86.42", "6413.58"],
            ["03/08/2026", "Moved to savings", "Transfer Out", "500.00", "5913.58"],
        ],
    )

    parsed = _by_description(parse_pdf(pdf_bytes))

    assert parsed["Monthly Salary"]["type"] == "earn"
    assert parsed["Grocery Store"]["type"] == "spend"
    assert parsed["Moved to savings"]["type"] == "spend"


# =========================================================
# Cross-cutting behaviour
# =========================================================

def test_currency_symbols_and_thousands_separators():
    pdf_bytes = _draw_statement(
        _DEBIT_CREDIT_HEADERS,
        [
            ["01/08/2026", "Salary", "", "$1,500.00", "$6,500.00"],
            ["02/08/2026", "Laptop", "$1,299.99", "", "$5,200.01"],
        ],
    )

    parsed = _by_description(parse_pdf(pdf_bytes))

    assert parsed["Salary"]["amount"] == 1500.00
    assert parsed["Laptop"]["amount"] == 1299.99
    assert parsed["Laptop"]["type"] == "spend"


def test_multi_page_statement_without_repeated_header():
    """
    Page 2 of a statement usually drops the header row. The column
    positions found on page 1 have to carry over.
    """

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 9)
    for label, x, align in _DEBIT_CREDIT_HEADERS:
        if align == "right":
            pdf.drawRightString(x, _TOP, label)
        else:
            pdf.drawString(x, _TOP, label)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, _TOP - 18, "01/08/2026")
    pdf.drawString(110, _TOP - 18, "Salary")
    pdf.drawRightString(450, _TOP - 18, "1500.00")
    pdf.drawRightString(540, _TOP - 18, "6500.00")

    pdf.showPage()

    # Second page: rows only, no header.
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, _TOP, "02/08/2026")
    pdf.drawString(110, _TOP, "Grocery Store")
    pdf.drawRightString(380, _TOP, "86.42")
    pdf.drawRightString(540, _TOP, "6413.58")

    pdf.save()

    parsed = _by_description(parse_pdf(buffer.getvalue()))

    assert parsed["Salary"]["type"] == "earn"
    assert parsed["Grocery Store"]["type"] == "spend"


def test_wrapped_description_is_stitched_not_dropped():
    """
    A long description wraps onto a second line with no date and no
    amounts. The row must survive with both lines joined.
    """

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 9)
    for label, x, align in _DEBIT_CREDIT_HEADERS:
        if align == "right":
            pdf.drawRightString(x, _TOP, label)
        else:
            pdf.drawString(x, _TOP, label)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, _TOP - 18, "05/08/2026")
    pdf.drawString(110, _TOP - 18, "AMAZON MKTPLACE")
    pdf.drawRightString(380, _TOP - 18, "250.00")
    pdf.drawRightString(540, _TOP - 18, "6163.58")
    # Continuation line: description column only.
    pdf.drawString(110, _TOP - 34, "ORDER 12345")

    pdf.save()

    transactions = parse_pdf(buffer.getvalue())

    assert len(transactions) == 1
    assert transactions[0]["amount"] == 250.00
    assert transactions[0]["type"] == "spend"
    assert "AMAZON MKTPLACE" in transactions[0]["description"]
    assert "ORDER 12345" in transactions[0]["description"]


def test_duplicate_rows_are_removed():
    pdf_bytes = _draw_statement(
        _DEBIT_CREDIT_HEADERS,
        [
            ["02/08/2026", "Grocery Store", "86.42", "", "6413.58"],
            ["02/08/2026", "Grocery Store", "86.42", "", "6413.58"],
        ],
    )

    assert len(parse_pdf(pdf_bytes)) == 1


def test_statement_with_no_transactions_returns_empty_list():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 700, "This page has no table on it at all.")
    pdf.save()

    assert parse_pdf(buffer.getvalue()) == []


def test_non_pdf_bytes_raise_pdf_parse_error():
    """
    Callers turn this into a 4xx. Letting pdfplumber's own exception
    escape would surface as a 500 instead — see upload.py.
    """

    with pytest.raises(PdfParseError):
        parse_pdf(b"this is not a pdf")


# =========================================================
# Flat-text fallback (no PDF needed)
# =========================================================

def test_text_fallback_uses_balance_to_infer_direction():
    text = """Bank Statement
Date Description Debit Credit Balance
Opening Balance 5000.00
02/08/2026 Grocery Store 86.42 4913.58
03/08/2026 Salary 1500.00 6413.58
04/08/2026 Rent Payment 1200.00 5213.58"""

    parsed = _by_description(_parse_text_transactions(text))

    assert parsed["Grocery Store"]["type"] == "spend"
    assert parsed["Salary"]["type"] == "earn"
    assert parsed["Rent Payment"]["type"] == "spend"


def test_text_fallback_recovers_wrapped_row():
    text = """Date Description Debit Credit Balance
Opening Balance 6413.58
05/08/2026 AMAZON MKTPLACE
ORDER 250.00 6163.58"""

    transactions = _parse_text_transactions(text)

    assert len(transactions) == 1
    assert transactions[0]["amount"] == 250.00
    assert transactions[0]["type"] == "spend"
    assert "AMAZON MKTPLACE" in transactions[0]["description"]


def test_text_fallback_layout_detection_ignores_description_keywords():
    """
    "DEBIT CARD PURCHASE" in a description must not flip a
    signed-amount statement into the debit/credit layout.
    """

    text = """Date Description Amount Balance
02-08-2026 DEBIT CARD PURCHASE POS -86.42 4913.58
03-08-2026 Salary 1500.00 6413.58"""

    parsed = _by_description(_parse_text_transactions(text))

    assert parsed["DEBIT CARD PURCHASE POS"]["type"] == "spend"
    assert parsed["Salary"]["type"] == "earn"


@pytest.mark.parametrize(
    "line, expected_description, expected_amounts",
    [
        ("Grocery Store 86.42 4913.58", "Grocery Store", ["86.42", "4913.58"]),
        (
            "UPI/1234567/SWIGGY 250.00 6163.58",
            "UPI/1234567/SWIGGY",
            ["250.00", "6163.58"],
        ),
        ("Salary $1,500.00 $6,500.00", "Salary", ["$1,500.00", "$6,500.00"]),
        ("No amounts here", "No amounts here", []),
    ],
)
def test_split_trailing_amounts(line, expected_description, expected_amounts):
    """
    Amounts are the trailing run of numeric tokens. A reference number
    embedded in the description must stay in the description.
    """

    description, amounts = _split_trailing_amounts(line)

    assert description == expected_description
    assert amounts == expected_amounts
