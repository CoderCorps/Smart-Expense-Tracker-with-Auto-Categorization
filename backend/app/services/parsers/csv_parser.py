"""
CSV statement parsing.

Deliberately thin: it returns the file's raw columns untouched, because
the user gets to correct the column mapping in the preview step before
anything is saved. Interpreting the values — dates, money, direction —
happens after that, in upload.py, via services/parsers/normalize.py.

Keeping value parsing out of here is what lets the CSV and PDF paths
agree on what a date or an amount means.
"""

import io

import pandas as pd


class CsvParseError(Exception):
    """Raised when a file can't be read as a CSV at all."""


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Return a DataFrame with the raw columns exactly as found in the file.

    Every column is read as text (`dtype=str`). Letting pandas infer
    types looks helpful but isn't: it silently reads "02/08/2026" as a
    US month-first date, and drops the leading zero from an account
    reference. normalize.parse_date/parse_money handle the conversion
    later, consistently with the PDF path.

    Raises:
        CsvParseError: the bytes aren't readable as CSV.
    """

    try:
        dataframe = pd.read_csv(
            io.BytesIO(file_bytes),
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=True,
        )
    except UnicodeDecodeError as exc:
        raise CsvParseError(
            "That file isn't UTF-8 text. Re-export it as a UTF-8 CSV."
        ) from exc
    except pd.errors.EmptyDataError as exc:
        raise CsvParseError("That file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise CsvParseError(f"That file isn't valid CSV: {exc}") from exc

    # Strip header whitespace so " Amount " maps like "Amount".
    dataframe.columns = [str(column).strip() for column in dataframe.columns]

    # Drop rows that are entirely blank — a trailing newline or a spacer
    # row between sections would otherwise be reported as a skipped row.
    if not dataframe.empty:
        dataframe = dataframe[
            dataframe.apply(lambda row: any(str(v).strip() for v in row), axis=1)
        ].reset_index(drop=True)

    return dataframe
