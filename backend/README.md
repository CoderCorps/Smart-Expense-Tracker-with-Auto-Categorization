# Smart Expense Tracker — Backend

FastAPI backend boilerplate. See the accompanying workflow document for the
full build plan, task split, and API list — this README just covers running
it locally.

## Setup

```bash
uv sync              # from backend/ — creates .venv, installs from uv.lock
cp .env.example .env
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
│           ├── auth.py            # done
│           ├── upload.py          # Person A
│           ├── transactions.py    # done
│           ├── categorization.py  # Person B
│           └── dashboard.py       # Person C
└── services/                   # actual business logic, kept separate from
    ├── parsers/                # endpoints so it's testable without the API
    │   ├── csv_parser.py       # Person A — working baseline
    │   ├── pdf_parser.py       # Person A — real task, see file
    │   └── column_mapper.py    # Person A — working baseline
    ├── categorization/
    │   ├── rule_based.py       # Person B — working baseline
    │   └── ml_classifier.py    # Person B — stretch goal, see file
    └── analytics/
        └── aggregations.py     # Person C — stubbed, see file
```

## Who owns what

See the workflow document for the full task breakdown. Short version:
auth and core transaction CRUD are already built as shared foundation.
Upload/parsing, categorization, and dashboard analytics are each one
person's module — every file above that says "Person X" in its docstring
is that person's to build, test, and open a PR for.
