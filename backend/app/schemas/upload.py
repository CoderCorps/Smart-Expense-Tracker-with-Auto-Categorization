from pydantic import BaseModel

# The 4 fields every transaction needs, regardless of what the source
# file's columns were originally called.
STANDARD_FIELDS = ["date", "description", "amount", "type"]


class ColumnMappingSuggestion(BaseModel):
    """
    Returned by POST /upload/preview. Shows the raw headers found in the
    file, a best-guess mapping to our standard fields, and a few sample
    rows so the frontend can show the user a preview table before they
    confirm. `mapping` maps STANDARD_FIELDS -> the raw column name we
    matched it to (or null if we couldn't guess).
    """

    upload_id: str  # temp id referencing the parsed-but-not-yet-saved file
    raw_headers: list[str]
    mapping: dict[str, str | None]
    sample_rows: list[dict]
    row_count: int


class ColumnMappingConfirm(BaseModel):
    """
    Sent by the frontend once the user has reviewed/corrected the mapping
    from the preview step. This is what actually triggers parsing + saving
    all rows + running auto-categorization on each one.
    """

    upload_id: str
    mapping: dict[str, str]  # must have all of STANDARD_FIELDS filled in


class UploadResult(BaseModel):
    saved_count: int
    skipped_count: int
    errors: list[str] = []
