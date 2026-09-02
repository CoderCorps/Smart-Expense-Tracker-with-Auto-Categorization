"""
PERSON A OWNS THIS FILE (uses parsers + column_mapper, which are also theirs).

The two-step flow (preview -> confirm) exists because the user needs a
chance to fix a wrong column-mapping guess before we save 500 transactions
with the amount column mapped to the wrong field. The frontend will:
  1. Upload the file to /upload/preview, show the user the guessed mapping
     + a sample of rows, let them adjust it in a dropdown per field
  2. Submit the corrected mapping to /upload/confirm, which actually parses
     every row, categorizes it, and saves it

CSV path is fully wired up and working end to end. PDF path calls
pdf_parser.parse_pdf(), which is still a stub — see that file for the task.

NOTE ON _preview_store: parsed-but-unconfirmed uploads are kept in memory
here, keyed by a random upload_id, so /confirm doesn't have to re-parse the
file. This is intentionally simple for a project this size — it resets if
the server restarts, which is fine. Don't over-engineer this into a real
job queue / temp file system unless you have a specific reason to.
"""

import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.category import Category
from app.models.transaction import CategorySource, Transaction, TransactionSource, TransactionType
from app.models.user import User
from app.schemas.upload import (
    STANDARD_FIELDS,
    ColumnMappingConfirm,
    ColumnMappingSuggestion,
    UploadResult,
)
from app.services.categorization.categorizer import categorize_transaction
from app.services.parsers.column_mapper import suggest_mapping
from app.services.parsers.csv_parser import parse_csv
from app.services.parsers.pdf_parser import parse_pdf

router = APIRouter(prefix="/upload", tags=["upload"])

# upload_id -> (DataFrame, original filename). See note in the module
# docstring above on why this is in-memory.
_preview_store: dict[str, tuple[pd.DataFrame, str]] = {}


@router.post("/preview", response_model=ColumnMappingSuggestion)
async def preview_upload(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()

    if file.filename.lower().endswith(".csv"):
        df = parse_csv(file_bytes)
    elif file.filename.lower().endswith(".pdf"):
        rows = parse_pdf(file_bytes)
        if not rows:
            raise HTTPException(
                status_code=422,
                detail="Could not extract a table from this PDF. (PDF parsing is still "
                "a work in progress — see services/parsers/pdf_parser.py)",
            )
        df = pd.DataFrame(rows)
    else:
        raise HTTPException(status_code=400, detail="Only .csv and .pdf files are supported")

    upload_id = str(uuid.uuid4())
    _preview_store[upload_id] = (
        df,
        file.filename.lower()
    )

    mapping = suggest_mapping(list(df.columns))
    sample_rows = df.head(5).fillna("").to_dict(orient="records")

    return ColumnMappingSuggestion(
        upload_id=upload_id,
        raw_headers=list(df.columns),
        mapping=mapping,
        sample_rows=sample_rows,
        row_count=len(df),
    )


def normalize_transaction_type(value: str):
    value = str(value).strip().lower()

    if value in {
        "earn",
        "credit",
        "cr",
        "deposit",
        "salary",
        "refund",
        "income",
        "received",
    }:
        return TransactionType.EARN

    if value in {
        "spend",
        "debit",
        "dr",
        "withdrawal",
        "transfer",
        "payment",
        "purchase",
        "expense",
        "withdraw",
    }:
        return TransactionType.SPEND

    return None

@router.post("/confirm", response_model=UploadResult)
def confirm_upload(
    payload: ColumnMappingConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stored = _preview_store.get(payload.upload_id)

    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found or already confirmed"
        )

    df, filename = stored
    print("\n========== CONFIRM DEBUG ==========")
    print("Upload ID:", payload.upload_id)
    print("Filename:", filename)
    print("DataFrame shape:", df.shape)
    print("DataFrame columns:", list(df.columns))
    print("DataFrame:")
    print(df.to_string())
    print("===================================\n")


    missing_fields = [f for f in STANDARD_FIELDS if f not in payload.mapping]
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Missing mapping for: {missing_fields}")

    categories_by_name = {c.name: c.id for c in db.query(Category).all()}

    saved_count = 0
    errors: list[str] = []
    print("========== STARTING ROW LOOP ==========")
    print("Number of rows:", len(df))

    for idx, row in df.iterrows():
        print("PROCESSING ROW:", idx)
        print(row.to_dict())
        try:
            print("STEP 1: entering try")
            raw_description = str(row[payload.mapping["description"]])
            print("STEP 2: description =", raw_description)
            category_name, category_source = categorize_transaction(
                raw_description
            )
            print("STEP 3: category =", category_name, category_source)

            type_column = payload.mapping.get("type")
            print("STEP 4: type_column =", type_column)

            raw_amount_text = (
                str(row[payload.mapping["amount"]])
                .replace(",", "")
                .replace("$", "")
                .strip()
            )
            print("STEP 5: amount =", raw_amount_text)
            # Skip rows with no usable amount, such as Opening Balance
            if raw_amount_text in {"", "-"}:
                continue

            raw_amount = float(raw_amount_text)

            if type_column and type_column in df.columns:
                raw_type = str(row[type_column]).strip().lower()

                txn_type = normalize_transaction_type(raw_type)

                # Skip rows such as Opening Balance where type is "-"
                if txn_type is None:
                    continue

            else:
                if raw_amount < 0:
                    txn_type = TransactionType.SPEND
                else:
                    txn_type = TransactionType.EARN

            amount = abs(raw_amount)

            transaction = Transaction(
                user_id=current_user.id,
                date=pd.to_datetime(
                    row[payload.mapping["date"]]
                ).date(),
                description=raw_description,
                raw_description=raw_description,
                amount=amount,
                type=txn_type,
                category_id=categories_by_name.get(category_name),
                category_source=(
                    CategorySource.ML
                    if category_source == "ml"
                    else CategorySource.RULE_BASED
                ),
                source=(
                    TransactionSource.PDF
                    if filename.endswith(".pdf")
                    else TransactionSource.CSV
                ),
            )
            print("BEFORE DB ADD")
            print(transaction)

            db.add(transaction)
            saved_count += 1

        except Exception as exc:
            errors.append(f"Row {idx}: {exc}")

    db.commit()
    del _preview_store[payload.upload_id]

    return UploadResult(saved_count=saved_count, skipped_count=len(errors), errors=errors)
