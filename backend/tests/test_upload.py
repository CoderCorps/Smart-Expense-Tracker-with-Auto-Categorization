"""
End-to-end tests for the CSV / PDF import flow.

These drive the two-step preview -> confirm sequence over HTTP, which is
where the parsers, the column mapper, the categorizer and the transaction
model all meet. Most of the bugs worth catching live in the seams between
them rather than inside any one piece.
"""

import io

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from backend.app.api.v1.endpoints.upload import MAX_UPLOAD_BYTES, _preview_store
from backend.app.models.transaction import Transaction, TransactionSource, TransactionType

SIMPLE_CSV = b"""Date,Description,Amount,Type
02/08/2026,SWIGGY ORDER 99213,450.50,Debit
03/08/2026,Monthly Salary,"50,000.00",Credit
04/08/2026,UBER TRIP,231.00,Debit
"""


@pytest.fixture(autouse=True)
def clear_preview_store():
    """The preview store is module-level state; don't leak it between tests."""
    _preview_store.clear()
    yield
    _preview_store.clear()


def _upload(client: TestClient, headers: dict, name: str, content: bytes):
    return client.post(
        "/api/v1/upload/preview",
        files={"file": (name, io.BytesIO(content), "application/octet-stream")},
        headers=headers,
    )


def _statement_pdf() -> bytes:
    """A debit/credit statement with one blank column per row."""

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    columns = [("Date", 40), ("Description", 110)]
    money = [("Debit", 380), ("Credit", 450), ("Balance", 540)]

    pdf.setFont("Helvetica-Bold", 9)
    for label, x in columns:
        pdf.drawString(x, 720, label)
    for label, x in money:
        pdf.drawRightString(x, 720, label)

    rows = [
        ("01/08/2026", "Monthly Salary", "", "50000.00", "52000.00"),
        ("02/08/2026", "SWIGGY ORDER 99213", "450.50", "", "51549.50"),
        ("03/08/2026", "UBER TRIP", "231.00", "", "51318.50"),
    ]

    pdf.setFont("Helvetica", 9)
    for index, (date, description, debit, credit, balance) in enumerate(rows):
        y = 720 - 18 * (index + 1)
        pdf.drawString(40, y, date)
        pdf.drawString(110, y, description)
        for value, x in ((debit, 380), (credit, 450), (balance, 540)):
            if value:
                pdf.drawRightString(x, y, value)

    pdf.save()
    return buffer.getvalue()


# =========================================================
# Preview step
# =========================================================

class TestPreview:
    def test_csv_preview_suggests_mapping(self, client, auth_headers):
        response = _upload(client, auth_headers, "statement.csv", SIMPLE_CSV)

        assert response.status_code == 200
        body = response.json()

        assert body["row_count"] == 3
        assert body["raw_headers"] == ["Date", "Description", "Amount", "Type"]
        assert body["mapping"] == {
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "type": "Type",
        }
        assert len(body["sample_rows"]) == 3

    def test_pdf_preview_normalizes_to_standard_columns(self, client, auth_headers):
        response = _upload(client, auth_headers, "statement.pdf", _statement_pdf())

        assert response.status_code == 200
        body = response.json()

        assert body["row_count"] == 3
        assert set(body["raw_headers"]) == {"date", "description", "amount", "type"}

    def test_unsupported_extension_is_rejected(self, client, auth_headers):
        response = _upload(client, auth_headers, "statement.txt", b"nope")

        assert response.status_code == 400
        assert "csv" in response.json()["detail"].lower()

    def test_empty_file_is_rejected(self, client, auth_headers):
        response = _upload(client, auth_headers, "statement.csv", b"")

        assert response.status_code == 400

    def test_oversized_file_is_rejected(self, client, auth_headers):
        oversized = b"a,b\n" + b"1,2\n" * (MAX_UPLOAD_BYTES // 4)

        response = _upload(client, auth_headers, "statement.csv", oversized)

        assert response.status_code == 413

    def test_corrupt_pdf_returns_422_not_500(self, client, auth_headers):
        """A malformed PDF is the user's problem to fix, not a server error."""

        response = _upload(client, auth_headers, "statement.pdf", b"definitely not a pdf")

        assert response.status_code == 422

    def test_image_only_pdf_explains_itself(self, client, auth_headers):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.drawString(40, 700, "Nothing tabular here")
        pdf.save()

        response = _upload(client, auth_headers, "scan.pdf", buffer.getvalue())

        assert response.status_code == 422
        assert "scanned" in response.json()["detail"].lower()

    def test_preview_requires_auth(self, client):
        response = _upload(client, {}, "statement.csv", SIMPLE_CSV)

        assert response.status_code == 401


# =========================================================
# Confirm step
# =========================================================

class TestConfirm:
    def _preview_id(self, client, auth_headers, name="statement.csv", content=SIMPLE_CSV):
        response = _upload(client, auth_headers, name, content)
        assert response.status_code == 200
        return response.json()["upload_id"]

    def test_csv_import_saves_rows(
        self, client, auth_headers, seed_categories, db: Session
    ):
        upload_id = self._preview_id(client, auth_headers)

        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["saved_count"] == 3
        assert response.json()["skipped_count"] == 0

        saved = client.get("/api/v1/transactions", headers=auth_headers).json()
        by_description = {t["description"]: t for t in saved}

        # Direction comes from the Type column.
        assert by_description["Monthly Salary"]["type"] == "earn"
        assert by_description["SWIGGY ORDER 99213"]["type"] == "spend"

        # Thousands separators survive the round trip.
        assert by_description["Monthly Salary"]["amount"] == 50000.00

        # Amount is stored as a positive magnitude regardless of direction.
        assert all(t["amount"] > 0 for t in saved)

        assert by_description["SWIGGY ORDER 99213"]["source"] == "csv"

    def test_dates_are_read_day_first(
        self, client, auth_headers, seed_categories
    ):
        """
        02/08/2026 is 2 August, not 8 February. The PDF path already read
        it that way; the CSV path used to disagree because it handed the
        string to pandas.
        """

        upload_id = self._preview_id(client, auth_headers)

        client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        saved = client.get("/api/v1/transactions", headers=auth_headers).json()
        dates = {t["description"]: t["date"] for t in saved}

        assert dates["SWIGGY ORDER 99213"] == "2026-08-02"
        assert dates["UBER TRIP"] == "2026-08-04"

    def test_transactions_are_auto_categorized(
        self, client, auth_headers, seed_categories
    ):
        upload_id = self._preview_id(client, auth_headers)

        client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        saved = client.get("/api/v1/transactions", headers=auth_headers).json()
        categories = {t["description"]: t["category_name"] for t in saved}

        assert categories["SWIGGY ORDER 99213"] == "Food & Dining"
        assert categories["UBER TRIP"] == "Travel & Transport"

    def test_pdf_import_saves_rows_with_correct_direction(
        self, client, auth_headers, seed_categories
    ):
        upload_id = self._preview_id(
            client, auth_headers, "statement.pdf", _statement_pdf()
        )

        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "date",
                    "description": "description",
                    "amount": "amount",
                    "type": "type",
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["saved_count"] == 3

        saved = client.get("/api/v1/transactions", headers=auth_headers).json()
        by_description = {t["description"]: t for t in saved}

        assert by_description["Monthly Salary"]["type"] == "earn"
        assert by_description["SWIGGY ORDER 99213"]["type"] == "spend"
        assert by_description["UBER TRIP"]["type"] == "spend"
        assert by_description["UBER TRIP"]["source"] == "pdf"

    def test_rows_without_a_usable_amount_are_skipped_not_failed(
        self, client, auth_headers, seed_categories
    ):
        """An opening-balance row has no amount. It's skipped and reported."""

        csv = (
            b"Date,Description,Amount,Type\n"
            b"01/08/2026,Opening Balance,-,-\n"
            b"02/08/2026,SWIGGY ORDER,450.50,Debit\n"
        )

        upload_id = self._preview_id(client, auth_headers, "statement.csv", csv)

        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        body = response.json()
        assert body["saved_count"] == 1
        assert body["skipped_count"] == 1
        assert len(body["errors"]) == 1

    def test_unknown_column_in_mapping_is_rejected(
        self, client, auth_headers, seed_categories
    ):
        upload_id = self._preview_id(client, auth_headers)

        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Nonexistent",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Nonexistent" in response.json()["detail"]

    def test_confirming_twice_fails(self, client, auth_headers, seed_categories):
        upload_id = self._preview_id(client, auth_headers)
        mapping = {
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "type": "Type",
        }

        first = client.post(
            "/api/v1/upload/confirm",
            json={"upload_id": upload_id, "mapping": mapping},
            headers=auth_headers,
        )
        second = client.post(
            "/api/v1/upload/confirm",
            json={"upload_id": upload_id, "mapping": mapping},
            headers=auth_headers,
        )

        assert first.status_code == 200
        assert second.status_code == 404

    def test_another_user_cannot_confirm_your_upload(
        self, client, auth_headers, auth_headers_user_2, seed_categories, db: Session
    ):
        """
        upload_id is an unguessable uuid4, but the lookup is scoped to its
        owner anyway — a leaked id must not import someone else's
        statement into a different account.
        """

        upload_id = self._preview_id(client, auth_headers)

        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": upload_id,
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers_user_2,
        )

        assert response.status_code == 404
        assert db.query(Transaction).count() == 0

    def test_unknown_upload_id_returns_404(self, client, auth_headers):
        response = client.post(
            "/api/v1/upload/confirm",
            json={
                "upload_id": "00000000-0000-0000-0000-000000000000",
                "mapping": {
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount",
                    "type": "Type",
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
