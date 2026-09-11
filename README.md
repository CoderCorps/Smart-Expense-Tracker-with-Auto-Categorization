# Smart Expense Tracker

Upload a bank statement, get a categorized breakdown of where the money went.

A full-stack expense tracker built around one idea: importing a statement
should be the only work the user does. Everything after that — reading the
file, working out which column is which, deciding whether a row is an expense
or income, assigning a category — is the app's job.

**Stack:** FastAPI · SQLAlchemy · SQLite · pandas · scikit-learn ·
React 19 · TypeScript · Vite · Tailwind v4 · Recharts

---

## What it does

**Imports CSV and PDF statements from any bank.** Column names differ between
banks ("Txn Date" vs "Value Date", "Narration" vs "Particulars"), so the app
guesses the mapping, shows you a preview, and lets you correct it before
anything is saved.

PDF statements are parsed in three passes, stopping at the first that works:
ruled-table extraction, then word coordinates, then flat text. The middle pass
is the important one — plain text extraction flattens a statement row into a
single line, which loses the column a number sat in, and in a Debit/Credit
layout that column is the only thing separating an expense from income.

**Categorizes every transaction automatically.** Keyword rules run on import,
so nothing is ever uncategorized. Every category you correct by hand is stored
as a labeled training example; once there are enough, you can train a
per-account TF-IDF + logistic regression classifier that takes over wherever
it's more confident than the rules, and falls back to them when it isn't.

**Shows you where the money went.** Monthly totals, a category breakdown, a
spend-vs-earn trend, and insights that flag any category running well above
its own three-month average.

---

## Quickstart

Two terminals. Backend first.

```bash
cd backend
uv sync
cp .env.example .env
uv run poe seed-demo     # optional: 6 months of demo data
uv run poe dev           # http://localhost:8000 — docs at /docs
```

```bash
cd frontend
npm install
cp .env.example .env
npm run dev              # http://localhost:5173
```

If you seeded the demo data, sign in with **demo@example.com** /
**demo1234**. Otherwise create an account from the signup page.

---

## Architecture

```
backend/
  app/
    api/v1/endpoints/   HTTP only — thin, no business logic
    services/
      parsers/          CSV + PDF -> rows; column mapping; value normalization
      categorization/   keyword rules + per-user ML classifier
      analytics/        pandas aggregations behind the dashboard
    models/             SQLAlchemy tables — the shared data contract
    schemas/            Pydantic request/response shapes
  tests/                160 tests, incl. PDFs generated per statement layout

frontend/
  src/
    lib/                axios client, API calls by resource, shared types
    components/         UI primitives, chart components
    pages/              Dashboard, Transactions, Upload, Login, Signup
```

Endpoints stay thin so the logic under `services/` can be tested without
starting the API — which is why most of the test suite runs in milliseconds
against plain functions rather than over HTTP.

### Two invariants worth knowing

**Amount is always stored as a positive magnitude; direction lives in `type`.**
Both write paths enforce it — `TransactionCreate`'s validators for manual
entry, the import loop for CSV/PDF — so a transaction means the same thing
however it arrived.

**Dates are read day-first.** `02/08/2026` is 2 August. Statement parsing goes
through one shared implementation (`services/parsers/normalize.py`) so the CSV
and PDF paths can't disagree about it.

---

## Testing

```bash
cd backend && uv run poe test      # 160 tests
cd frontend && npm run build       # typecheck + production build
npm run lint
```

The PDF tests generate real PDFs with reportlab in each supported statement
layout, rather than asserting against fixture text — a parser that depends on
where words sit on the page has to be tested on a page.

CI runs both on every pull request (`.github/workflows/ci.yml`).

---

## API

Interactive docs at `http://localhost:8000/docs` once the backend is running.

| | |
|---|---|
| `POST /auth/signup` · `/auth/login` · `GET /auth/me` | JWT auth |
| `GET/POST /transactions`, `PUT /transactions/{id}/category` | CRUD + correction |
| `POST /upload/preview` -> `POST /upload/confirm` | two-step import |
| `GET /categorization/categories` · `training-status` · `POST /train` | categorization |
| `GET /dashboard/summary` · `category-breakdown` · `trends` · `insights` | analytics |

All paths are under `/api/v1`.
