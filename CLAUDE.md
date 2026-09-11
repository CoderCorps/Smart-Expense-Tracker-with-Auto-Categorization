# Smart Expense Tracker

Monorepo: `backend/` (FastAPI, SQLAlchemy, SQLite) + `frontend/` (React + Vite + TS + Tailwind v4).

**This file is tracked in git on purpose.** It documents the repo layout and
the conventions everyone is expected to follow, so it has to be visible to
everyone who clones the repo. It was previously listed in `.gitignore`, which
is how one branch ended up rebuilding the entire backend at the repo root
instead of working inside `backend/app/`.

## Running locally

Backend:
```bash
cd backend
uv sync
cp .env.example .env
uv run poe dev         # dev server with --reload, http://localhost:8000, docs at /docs
uv run poe start       # production (no --reload)
uv run poe test        # pytest
uv run poe seed-demo   # 6 months of demo data — demo@example.com / demo1234
```
`poe` (poethepoet, a dev dependency) runs these as named tasks defined in
`backend/pyproject.toml`'s `[tool.poe.tasks]`. The app's own imports use the
`backend.app...` package path, so both server tasks pass uvicorn `--app-dir ..`
to put the repo root on `sys.path` regardless of `poe` running with `backend/`
as its cwd.

Without `poe`, from the repo root instead:
```bash
uv run --project backend uvicorn backend.app.main:app --reload   # dev
uv run --project backend python -m backend.app.main              # production
```

Frontend:
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm run dev             # http://localhost:5173
```
Backend CORS (`backend/app/core/config.py`) already allows `localhost:5173`.

## Status

Everything below is built and covered by tests. `backend/tests/` has 160
tests and CI (`.github/workflows/ci.yml`) runs them plus the frontend build
on every PR — a red suite on `main` is a bug, not the normal state.

- **Auth**: signup / login / me, JWT.
- **Transactions**: CRUD, filtering, pagination, category correction.
- **Import**: CSV and PDF, two-step preview -> confirm with a correctable
  column mapping.
- **Categorization**: keyword rules always; a per-user TF-IDF + logistic
  regression model takes over where it's more confident.
- **Analytics**: summary, category breakdown, trends, spike insights.

## Backend conventions

- **Endpoints stay thin.** Business logic lives in `app/services/` so it can
  be tested without starting the API. Endpoints translate service exceptions
  into status codes — a malformed input should be a 4xx naming the problem,
  never a 500.
- **Amount is always stored as a positive magnitude; direction lives in
  `type`.** Enforced in both write paths: `TransactionCreate`'s validators
  for manual entry, and the import loop in `upload.py`. See
  `docs/data_model.md`.
- **Dates are day-first** — `02/08/2026` is 2 August. All statement value
  parsing goes through `app/services/parsers/normalize.py`; don't reimplement
  date or money parsing anywhere else, because that's exactly how the CSV and
  PDF paths came to disagree.
- **Trained ML models are per-user**, written to `backend/ml_models/`
  (gitignored), and never consulted for a different user. A description is
  sensitive text and "AMZN MKTP" means different things to different people.
- **A relative `DATABASE_URL` resolves against `backend/`**, not the cwd (see
  the validator in `core/config.py`), so `poe dev` and `poe seed-demo` always
  mean the same file.
- **PDF parsing tries three passes per page**, in order: ruled tables, word
  coordinates, flat text. The word-coordinate pass exists because plain text
  extraction loses which column a number sat in — and in a Debit/Credit
  layout that column is the only thing distinguishing an expense from income.
  Don't "simplify" it back to text-only.

## Frontend conventions

- API calls live in `frontend/src/lib/resources.ts` (grouped by resource,
  thin wrappers over `frontend/src/lib/api.ts`'s axios instance). Add new
  calls there, not inline in components.
- Types in `frontend/src/lib/types.ts` are hand-mirrored from
  `backend/app/schemas/*.py` — no shared codegen. Keep them in sync manually
  when a schema changes.
- Async fetching goes through `frontend/src/lib/useAsync.ts`, which tracks
  loading/error/data and discards results from a stale request. Prefer it
  over hand-rolled `useEffect` + three `useState`s.
- Auth token lives in `localStorage` (`TOKEN_KEY` in `lib/api.ts`); a 401
  response redirects to `/login` via an axios interceptor.
- Styling: Tailwind v4 (`@tailwindcss/vite` plugin, no separate config file —
  tokens are defined as CSS custom properties + `@theme inline` in
  `frontend/src/index.css`). Light/dark are both fully specified there; don't
  hardcode hex colors in components, use the `surface-*`, `text-*`,
  `series-*`, `status-*` Tailwind classes.
- Charts: recharts, using the `series-1..8` fixed-order categorical palette
  (`frontend/src/lib/palette.ts` — `colorForCategory()` assigns by category
  name in first-seen order, capped at 8 slots + "Other"). This follows the
  project's dataviz skill: never assign chart color by rank/index of the
  current filter, only by identity. Both the light and dark palettes have
  been validated against that skill's checker; don't change a series hex
  without re-running it.
- Shared UI primitives (`Button`, `Card`, `Input`, `Select`, `Skeleton`,
  `EmptyState`, `ErrorState`) are in `frontend/src/components/ui.tsx` — reuse
  them rather than one-off styled elements.
- A panel that's still loading shows a skeleton, and one that failed shows
  `ErrorState` with a retry. Don't render `0` for data that hasn't arrived —
  a zero is a real value here and showing a fake one lies about the numbers.

## Don't

- Don't build a real job queue or persistent store for in-progress uploads —
  `upload.py`'s in-memory `_preview_store` is intentionally simple for a
  project this size (see its docstring). It bounds its own size and age;
  that's as far as it needs to go.
- Don't add Alembic/migrations — `Base.metadata.create_all()` on startup is
  the intentional choice for a project this size (see `main.py`).
- Don't reach for Redux/Zustand/react-query — the app is small enough that
  local state + `useAsync` + the one `AuthContext` is enough. Revisit only if
  this actually becomes a pain.
- Don't pin `pandas` back below 2.3 — 2.2.2 predates numpy 2.x and segfaults
  in `to_datetime`, which took down the whole dashboard rather than failing
  one request.
