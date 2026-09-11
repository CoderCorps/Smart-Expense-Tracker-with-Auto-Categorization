# Smart Expense Tracker — Backend

FastAPI backend. This README covers running and working on it; see the
root README for what the project does and the overall architecture.

## Setup

```bash
uv sync              # from backend/ — creates .venv, installs from uv.lock
cp .env.example .env
```

Seed a demo account with six months of transactions, so the dashboard has
something to render while you work on it:

```bash
uv run poe seed-demo     # demo@example.com / demo1234
```

(`pip install -r requirements.txt` into a manually-created venv still works
too — `requirements.txt` and `pyproject.toml` are kept in sync.)

## Run

The app's own imports use the `backend.app...` package path, so uvicorn needs
the repo root on `sys.path`. From `backend/`, that's handled for you by the
`poe` tasks (`pyproject.toml`'s `[tool.poe.tasks]`, via `--app-dir ..`):

```bash
uv run poe dev      # dev server with --reload, http://localhost:8000
uv run poe start    # production, no reload
```

Equivalent commands run from the repo root instead (no `poe`, no `cd`):

```bash
uv run --project backend uvicorn backend.app.main:app --reload   # dev
uv run --project backend python -m backend.app.main              # production
```

Either way, interactive docs (auto-generated from the code, always up to
date) are at `http://localhost:8000/docs`.

## Test

```bash
uv run poe test
```

The PDF parser tests build real PDFs with reportlab in each statement layout
the parser supports. That matters because the parser reads word coordinates
to recover which column a number sat in, and fixture text can't exercise
that.

## Database

SQLite at `backend/expense_tracker.db`, created on startup by
`Base.metadata.create_all()` — no migration tool, which is the intentional
choice at this size.

A relative `DATABASE_URL` is resolved against `backend/`, not your working
directory (see the validator in `core/config.py`). Without that, `poe dev`
and `poe seed-demo` write to different files and the database looks empty
for no visible reason.

## Project structure

```
app/
├── main.py                  # FastAPI app setup, CORS, startup DB seeding
├── core/
│   ├── config.py            # Settings loaded from .env
│   └── security.py          # Password hashing + JWT (done, don't need to touch)
├── db/
│   └── database.py          # SQLAlchemy engine/session setup
├── models/                  # SQLAlchemy tables — the shared data contract
│   ├── user.py
│   ├── category.py
│   └── transaction.py
├── schemas/                 # Pydantic request/response shapes
├── api/
│   ├── deps.py               # get_current_user — use this to require login
│   └── v1/
│       ├── router.py         # wires all endpoint modules together
│       └── endpoints/
│           ├── auth.py            # signup / login / me
│           ├── upload.py          # two-step CSV+PDF import
│           ├── transactions.py    # CRUD + category correction
│           ├── categorization.py  # categories, retrain, training status
│           └── dashboard.py       # analytics endpoints
├── scripts/
│   └── seed_demo.py         # `poe seed-demo`
└── services/                   # business logic, kept separate from the
    ├── parsers/                # endpoints so it's testable without the API
    │   ├── csv_parser.py       # raw CSV -> DataFrame
    │   ├── pdf_parser.py       # tables -> word coords -> text, in that order
    │   ├── column_mapper.py    # guesses which column is which
    │   └── normalize.py        # shared date/money parsing for both paths
    ├── categorization/
    │   ├── rule_based.py       # keyword rules; always the fallback
    │   └── ml_classifier.py    # per-user TF-IDF + logistic regression
    └── analytics/
        └── aggregations.py     # pandas aggregations for the dashboard
```

## Conventions

- **Endpoints stay thin.** Logic lives in `services/`; endpoints handle HTTP
  concerns and translate service exceptions into status codes.
- **Amount is stored as a positive magnitude**, with direction in `type`.
  Both write paths enforce it. See `docs/data_model.md`.
- **Dates are day-first** — `02/08/2026` is 2 August. All statement value
  parsing goes through `services/parsers/normalize.py` so the CSV and PDF
  paths can't drift apart.
- **Trained ML models are per-user** and written to `backend/ml_models/`
  (gitignored). A shared model would apply one account's corrections to
  everyone else's transactions.
