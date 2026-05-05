# Stock Management System

Phase 1: Foundation & Core Product Management.

## Stack
- Backend: FastAPI + SQLAlchemy + PostgreSQL (SQLite in tests) + Redis
- Frontend: Electron + React + Vite + Zustand

## Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env             # adjust DATABASE_URL etc.
alembic upgrade head             # apply migrations (Postgres)
python -m scripts.seed_admin     # creates admin@example.com / ChangeMe123!
uvicorn app.main:app --reload    # http://localhost:8000
```

Tests (uses SQLite, no Postgres needed):

```bash
cd backend
python -m pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev                 # Vite dev server on :5173
npm run electron:dev        # launches Electron pointing at the dev server
```

## Docker (full dev stack)

```bash
docker-compose up --build
# API on http://localhost:8000
```

## Phase 1 endpoints

- `POST /api/v1/auth/login` — returns access + refresh tokens
- `POST /api/v1/auth/refresh`
- `GET  /api/v1/auth/me`
- `POST /api/v1/admin/users` (admin only)
- `GET  /api/v1/admin/users` (admin only)
- `POST /api/v1/products` (admin/manager) — accepts `Idempotency-Key` header
- `GET  /api/v1/products` — search, filter, pagination
- `GET  /api/v1/products/{id}`
- `PUT  /api/v1/products/{id}` (admin/manager) — SKU/barcode/UoM immutable

## Default credentials (dev)

```
admin@example.com / ChangeMe123!
```

Change immediately in any non-development environment.
