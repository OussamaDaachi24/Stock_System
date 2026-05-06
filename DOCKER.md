# Docker Setup — Stock Management System

Complete full-stack containerized setup. One command to run everything.

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- ~2 GB disk space
- Ports 80, 8000, 5432, 6379 available (or modify `docker-compose.yml`)

### Run

```bash
docker-compose up --build
```

Wait 30–60 seconds for all services to start and health checks to pass.

Then open:
- **Web UI:** http://localhost
- **API Swagger:** http://localhost:8000/docs
- **API ReDoc:** http://localhost:8000/redoc

### Default credentials

```
admin@example.com / ChangeMe123!
```

Change immediately for production use.

---

## What's running

| Service | Port | Purpose |
|---------|------|---------|
| **nginx (web)** | 80 | React SPA + static assets + API proxy |
| **FastAPI (api)** | 8000 | REST API backend |
| **PostgreSQL** | 5432 | Database |
| **Redis** | 6379 | Idempotency cache & session store |

---

## Common tasks

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f web
docker-compose logs -f postgres
```

### Stop everything

```bash
docker-compose down
```

### Stop but keep data

```bash
docker-compose stop
docker-compose start  # Resume later
```

### Full reset (delete DB)

```bash
docker-compose down -v
docker-compose up --build
```

### Run backend tests

```bash
docker-compose exec api pytest -q
```

### Access database CLI

```bash
docker-compose exec postgres psql -U stock -d stock_db
```

### Access redis CLI

```bash
docker-compose exec redis redis-cli
```

---

## Configuration

Edit `docker-compose.yml` to:
- Change `SECRET_KEY` (line 17) to a random value for production
- Change port bindings (e.g., `"8000:8000"` → `"8001:8000"` to use port 8001 locally)
- Add environment variables (e.g., `ENVIRONMENT: production`)

---

## Production deployment

For production, use this compose file with:
1. A real `SECRET_KEY` (use `openssl rand -hex 32`)
2. A production PostgreSQL database (managed RDS, etc.)
3. External Redis (ElastiCache, etc.)
4. HTTPS reverse proxy (CloudFront, nginx, etc.)
5. Update `docker-compose.yml` to reference external services

Example:

```yaml
  api:
    environment:
      DATABASE_URL: postgresql+psycopg2://user:pass@prod-db.example.com:5432/stock
      REDIS_URL: redis://prod-redis.example.com:6379/0
      SECRET_KEY: <generated-production-secret>
      ENVIRONMENT: production
```

---

## Troubleshooting

### Port already in use

```bash
# Change port in docker-compose.yml, e.g. 8001:8000
# Then access API at http://localhost:8001
```

### Services not starting

```bash
docker-compose logs -f  # Check error messages
docker-compose down -v && docker-compose up --build  # Full reset
```

### Can't login

- Default user: `admin@example.com` / `ChangeMe123!`
- If seed_admin failed, check logs: `docker-compose logs api`
- Manually create a user via API:
  ```bash
  curl -X POST http://localhost:8000/api/v1/admin/users \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <token>" \
    -d '{"email":"test@example.com","name":"Test","password":"Password123!","role":"admin"}'
  ```

### Frontend shows "Cannot GET /"

- Wait for `web` service to be healthy: `docker-compose ps`
- Check nginx logs: `docker-compose logs web`

### API returns 502

- API service may still be starting (migrations running)
- Check: `docker-compose logs api`
- Wait 30 seconds and refresh

---

## Development workflow

While containers are running:

1. **Edit backend code** → Changes auto-reload (uvicorn --reload)
   ```bash
   docker-compose logs -f api  # Watch for changes
   ```

2. **Edit frontend code** → Requires rebuild
   ```bash
   docker-compose down web
   docker-compose up web --build
   ```

3. **Run backend tests** → Inside container
   ```bash
   docker-compose exec api pytest tests/
   ```

---

## File structure

```
Stock_System/
├── docker-compose.yml         ← Main orchestration
├── backend/
│   ├── Dockerfile             ← API image
│   ├── app/                   ← FastAPI app
│   └── ...
├── frontend/
│   ├── Dockerfile             ← React + nginx image
│   ├── nginx.conf             ← Proxy rules
│   ├── src/                   ← React source
│   └── ...
├── DOCKER.md                  ← This file
└── README.md                  ← Project docs
```
