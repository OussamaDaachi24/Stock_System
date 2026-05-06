# Stock Management System

Single-tenant inventory & stock management system. Append-only ledger, atomic
reservations, full audit trail, role-based access (operator / manager / admin /
viewer).

## Stack
- Backend: FastAPI + SQLAlchemy + PostgreSQL (SQLite in tests) + Redis
- Frontend: Electron + React + Vite + Zustand
- Auth: JWT (access + refresh)
- Idempotency: client-supplied `Idempotency-Key` header, Redis-backed (memory fallback)

## Quick start

### Docker (recommended for full stack)

```bash
docker-compose up --build
# API on http://localhost:8000  (Swagger at /docs)
```

### Backend (local)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env             # adjust DATABASE_URL, SECRET_KEY, REDIS_URL
alembic upgrade head
python -m scripts.seed_admin     # creates admin@example.com / ChangeMe123!
uvicorn app.main:app --reload    # http://localhost:8000
pytest -q                        # tests use SQLite, no infra needed
```

### Frontend (local dev)

```bash
cd frontend
cp .env.example .env             # VITE_API_BASE=http://localhost:8000
npm install
npm run dev                      # Vite dev server on :5173
npm run electron:dev             # launches Electron pointing at dev server
```

### Frontend (Electron desktop build)

```bash
cd frontend
npm run build                    # vite build
npm run electron:build           # produces dist-electron/*.exe (Windows)
```

## API surface (v1)

Auth & users — `/api/v1/auth/*`, `/api/v1/admin/users`
Products — `/api/v1/products` (search, CRUD, immutable SKU/barcode/UoM)
Inventory — `/api/v1/inventory/{ledger,snapshot,adjustments,low-stock,reconcile}`
Suppliers — `/api/v1/suppliers`
Purchase orders — `/api/v1/purchase-orders`
Receipts — `/api/v1/receipts` (`+ /complete`, `/put-away-tasks`)
Returns — `/api/v1/returns` (`+ /disposition`, `/credit-memo`)
Credit memos — `/api/v1/credit-memos/{id}/issue`
Reservations — `/api/v1/reservations` (atomic, expiring, idempotent)
Reports — `/api/v1/reports/inventory-export` (queue → poll → download)
Admin ops — `/api/v1/admin/{backups,restore}`
Health & metrics — `/api/v1/health`, `/api/v1/health/full`, `/api/v1/metrics`

OpenAPI / Swagger UI is available at `/docs`. ReDoc at `/redoc`.

## Frontend screens

- **Dashboard** — system metrics, low-stock alerts, quick links
- **Products** — list, search, create, edit (admin/manager)
- **Receiving** — barcode/SKU scan, line builder, discrepancy alerts, complete
- **Returns** — intake form, queue, inspection & disposition modal
- **Reservations** — quick reserve with available-stock display, release
- **Suppliers** — list, create
- **Purchase Orders** — list, create with line items
- **Reports** — inventory export (CSV/JSON), poll, download
- **Admin** (admin only) — users, backups (trigger/list/restore), system status

## Domain rules (enforced)

1. Inventory ledger is append-only (no UPDATE/DELETE in code paths).
2. Stock changes always go through ledger entries; snapshot is a derived cache.
3. Reservations use `SELECT … FOR UPDATE` with available-stock check.
4. Every mutation writes an `audit_logs` entry.
5. POST endpoints accept `Idempotency-Key`; duplicates return cached response.
6. Reservations expire automatically (job releases them; ledger gets `release` entry).

See `.claude/CLAUDE.md` and `.claude/IMPLEMENTATION_WORKFLOW.md` for full domain
rules and phase-by-phase delivery notes.

## Running tests

```bash
cd backend && pytest -q
cd frontend && npx tsc --noEmit && npm run build
```

CI workflow runs both on every PR (`.github/workflows/ci.yml`) plus a Docker
image build on `main`.

## Default credentials (development only)

```
admin@example.com / ChangeMe123!
```

Change immediately in any non-development environment.

## Production checklist

- Set `SECRET_KEY` to a long random value.
- Configure a real `DATABASE_URL` (PostgreSQL) and `REDIS_URL`.
- Run `alembic upgrade head` before serving.
- Replace the seeded admin password.
- Front the API behind HTTPS; keep CORS origins tight.
- Schedule the reconciliation, reservation expiry, and orphan-cleanup jobs
  (currently exposed as endpoints; wire to cron or Celery beat in deployment).
- Take regular backups (`POST /api/v1/admin/backups`) and store offsite.
