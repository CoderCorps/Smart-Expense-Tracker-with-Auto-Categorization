"""
PERSON A OWNS THIS FILE. This one is a real task, not just a stub to fill in
blanks — bank statement PDFs are messy and this is the hardest single piece
of the whole backend. Budget real time for it.

The approach: pdfplumber can usually extract tables directly from a PDF
page if the bank statement has actual table structure (most do). The
starting point below gets you the raw extracted table; turning that into
a clean DataFrame with sensible column names is the actual work.

Suggested approach:
  1. Test against 2-3 real bank statement PDFs (ask around, or use sample
     ones from a quick search) — they vary a lot, don't design against just one
  2. If a page has no extractable table (scanned/image-based PDF), pdfplumber
     will return nothing useful — for now, just return an error for those
     rather than trying to OCR them (that's a stretch goal, not a requirement)
  3. Once you have rows, reuse column_mapper.suggest_mapping() on whatever
     headers you extract, same as the CSV path — don't build a separate
     mapping system for PDFs
"""

import pdfplumber


def parse_pdf(file_bytes: bytes) -> list[dict]:
    """
    Returns a list of dict rows extracted from tables found in the PDF.
    Currently a minimal starting point — extracts the first table found on
    each page and assumes the first row of each table is the header.

    TODO (Person B): handle multi-page statements where the header only
    appears on page 1, handle statements with no clean table structure,
    and normalize the extracted rows into the same shape parse_csv() returns
    (a DataFrame) so upload.py can treat CSV and PDF results identically.
    """
    import io

    all_rows: list[dict] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table or len(table) < 2:
                continue
            headers, *rows = table
            for row in rows:
                all_rows.append(dict(zip(headers, row)))

    return all_rows
