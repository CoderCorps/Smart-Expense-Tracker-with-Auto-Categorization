"""
CSV / PDF statement import.

The two-step flow (preview -> confirm) exists because the user needs a
chance to fix a wrong column-mapping guess before we save 500 transactions
with the amount column mapped to the wrong field. The frontend will:
  1. Upload the file to /upload/preview, show the user the guessed mapping
     + a sample of rows, let them adjust it in a dropdown per field
  2. Submit the corrected mapping to /upload/confirm, which actually parses
     every row, categorizes it, and saves it

Both the CSV and PDF paths are wired up end to end. PDF statements are
normalized to the same four columns a CSV would have (date, description,
amount, type) by services/parsers/pdf_parser.py, so everything downstream
of the preview step is shared.

NOTE ON _preview_store: parsed-but-unconfirmed uploads are kept in memory
here, keyed by a random upload_id, so /confirm doesn't have to re-parse the
file. This is intentionally simple for a project this size — it resets if
the server restarts, which is fine. Don't over-engineer this into a real
job queue / temp file system unless you have a specific reason to. It does
cap its own size and age, because an abandoned preview would otherwise
hold its DataFrame until the process exits.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.category import Category
from backend.app.models.transaction import (
    CategorySource,
    Transaction,
    TransactionSource,
    TransactionType,
)
from backend.app.models.user import User
from backend.app.schemas.upload import (
    STANDARD_FIELDS,
    ColumnMappingConfirm,
    ColumnMappingSuggestion,
    UploadResult,
)
from backend.app.services.categorization.ml_classifier import MLCategorizer
from backend.app.services.categorization.rule_based import categorize
from backend.app.services.parsers.column_mapper import suggest_mapping
from backend.app.services.parsers.csv_parser import CsvParseError, parse_csv
from backend.app.services.parsers.normalize import clean_text, parse_date, parse_money
from backend.app.services.parsers.pdf_parser import PdfParseError, parse_pdf

router = APIRouter(prefix="/upload", tags=["upload"])

# Uploads are read fully into memory to be parsed, so the cap is what
# keeps one oversized file from taking the process down. Bank statements
# are small; 10 MB is already generous.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Bounds on _preview_store, so abandoned previews can't accumulate.
PREVIEW_TTL = timedelta(minutes=30)
MAX_PREVIEWS = 50

# Only the first N skipped rows are reported back. A badly-mapped 10k-row
# file would otherwise return a 10k-entry error list.
MAX_REPORTED_ERRORS = 20


@dataclass
class _Preview:
    """A parsed-but-unconfirmed upload waiting for its column mapping."""

    user_id: int
    dataframe: pd.DataFrame
    filename: str
    source: TransactionSource
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


_preview_store: dict[str, _Preview] = {}


def _evict_stale_previews() -> None:
    """Drop expired previews, then the oldest if we're still over cap."""

    cutoff = datetime.now(timezone.utc) - PREVIEW_TTL

    for upload_id in [
        key
        for key, preview in _preview_store.items()
        if preview.created_at < cutoff
    ]:
        _preview_store.pop(upload_id, None)

    while len(_preview_store) > MAX_PREVIEWS:
        oldest = min(_preview_store, key=lambda k: _preview_store[k].created_at)
        _preview_store.pop(oldest, None)


def categorize_transaction(
    description: str,
    categorizer: MLCategorizer,
) -> tuple[str, str]:
    """
    Categorize a description, preferring the ML model when it's confident.

    The categorizer is built once per import and passed in — it belongs to
    one user (see ml_classifier.py), and rebuilding it per row would
    re-read the model file thousands of times.
    """

    prediction = categorizer.predict(description)

    if prediction:
        return prediction.category_name, "ml"

    return categorize(description), "rule_based"


@router.post("/preview", response_model=ColumnMappingSuggestion)
async def preview_upload(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    filename = (file.filename or "").strip()

    if not filename:
        raise HTTPException(status_code=400, detail="The upload has no filename")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="That file is empty")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"That file is larger than the "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit"
            ),
        )

    lowered = filename.lower()

    if lowered.endswith(".csv"):
        source = TransactionSource.CSV
        try:
            dataframe = parse_csv(file_bytes)
        except CsvParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    elif lowered.endswith(".pdf"):
        source = TransactionSource.PDF
        try:
            rows = parse_pdf(file_bytes)
        except PdfParseError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"That file could not be opened as a PDF: {exc}",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No transactions could be read from this PDF. Scanned or "
                    "image-only statements aren't supported — if your bank "
                    "offers a CSV export, use that instead."
                ),
            )

        dataframe = pd.DataFrame(rows)

    else:
        raise HTTPException(
            status_code=400, detail="Only .csv and .pdf files are supported"
        )

    if dataframe.empty:
        raise HTTPException(
            status_code=422, detail="That file has no rows in it"
        )

    _evict_stale_previews()

    upload_id = str(uuid.uuid4())
    _preview_store[upload_id] = _Preview(
        user_id=current_user.id,
        dataframe=dataframe,
        filename=filename,
        source=source,
    )

    raw_headers = [str(column) for column in dataframe.columns]

    return ColumnMappingSuggestion(
        upload_id=upload_id,
        raw_headers=raw_headers,
        mapping=suggest_mapping(raw_headers),
        sample_rows=dataframe.head(5).fillna("").astype(str).to_dict(orient="records"),
        row_count=len(dataframe),
    )


def normalize_transaction_type(value: str) -> TransactionType | None:
    """
    Map a statement's own wording for direction onto our two types.

    Returns None for anything unrecognised — including the "-" banks put
    in the type column of an opening-balance row — so the caller can skip
    the row and say why rather than guessing.
    """

    text = clean_text(value).lower()

    earn_values = {
        "earn",
        "credit",
        "cr",
        "deposit",
        "salary",
        "refund",
        "income",
        "received",
        "transfer in",
    }

    spend_values = {
        "spend",
        "debit",
        "dr",
        "withdrawal",
        "withdraw",
        "transfer",
        "transfer out",
        "payment",
        "purchase",
        "expense",
    }

    if text in earn_values:
        return TransactionType.EARN

    if text in spend_values:
        return TransactionType.SPEND

    return None


@router.post("/confirm", response_model=UploadResult)
def confirm_upload(
    payload: ColumnMappingConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preview = _preview_store.get(payload.upload_id)

    # The id is an unguessable uuid4, but scoping the lookup to its owner
    # means a leaked id still can't import someone else's statement into
    # this account.
    if preview is None or preview.user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail="Upload not found or already confirmed"
        )

    dataframe = preview.dataframe

    missing_fields = [f for f in STANDARD_FIELDS if not payload.mapping.get(f)]
    if missing_fields:
        raise HTTPException(
            status_code=400, detail=f"Missing mapping for: {', '.join(missing_fields)}"
        )

    unknown_columns = [
        column
        for field_name, column in payload.mapping.items()
        if field_name in STANDARD_FIELDS and column not in dataframe.columns
    ]
    if unknown_columns:
        raise HTTPException(
            status_code=400,
            detail=f"No such column in the file: {', '.join(unknown_columns)}",
        )

    categories_by_name = {c.name: c.id for c in db.query(Category).all()}

    # Loaded once for the whole import, not per row.
    categorizer = MLCategorizer(current_user.id)

    date_column = payload.mapping["date"]
    description_column = payload.mapping["description"]
    amount_column = payload.mapping["amount"]
    type_column = payload.mapping["type"]

    saved_count = 0
    skipped_count = 0
    errors: list[str] = []

    def skip(row_number: int, reason: str) -> None:
        nonlocal skipped_count
        skipped_count += 1
        if len(errors) < MAX_REPORTED_ERRORS:
            errors.append(f"Row {row_number}: {reason}")

    for position, (_, row) in enumerate(dataframe.iterrows(), start=1):
        try:
            raw_description = clean_text(row[description_column])
            if not raw_description:
                skip(position, "no description")
                continue

            transaction_date = parse_date(row[date_column])
            if transaction_date is None:
                skip(position, f"unrecognised date {row[date_column]!r}")
                continue

            raw_amount = parse_money(row[amount_column])
            # Opening-balance and subtotal rows have a blank or "-" amount.
            if raw_amount is None or raw_amount == 0:
                skip(position, "no usable amount")
                continue

            txn_type = normalize_transaction_type(row[type_column])
            if txn_type is None:
                # Some exports carry no real type column and encode
                # direction in the sign of the amount instead.
                if raw_amount < 0:
                    txn_type = TransactionType.SPEND
                elif clean_text(row[type_column]):
                    skip(
                        position,
                        f"unrecognised type {clean_text(row[type_column])!r}",
                    )
                    continue
                else:
                    txn_type = TransactionType.EARN

            category_name, category_source = categorize_transaction(
                raw_description, categorizer
            )

            db.add(
                Transaction(
                    user_id=current_user.id,
                    date=transaction_date,
                    description=raw_description,
                    raw_description=str(row[description_column]),
                    # Amount is always stored as a positive magnitude;
                    # direction lives in `type`. Same invariant the manual
                    # entry path enforces via TransactionCreate.
                    amount=abs(raw_amount),
                    type=txn_type,
                    category_id=categories_by_name.get(category_name),
                    category_source=(
                        CategorySource.ML
                        if category_source == "ml"
                        else CategorySource.RULE_BASED
                    ),
                    source=preview.source,
                )
            )
            saved_count += 1

        except Exception as exc:  # noqa: BLE001 - one bad row must not kill the import
            skip(position, str(exc))

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Could not save these transactions: {exc}"
        ) from exc

    # Only drop the preview once the rows are safely committed, so a failed
    # import can be retried without re-uploading the file.
    _preview_store.pop(payload.upload_id, None)

    if skipped_count > len(errors):
        errors.append(f"... and {skipped_count - len(errors)} more skipped rows")

    return UploadResult(
        saved_count=saved_count, skipped_count=skipped_count, errors=errors
    )
