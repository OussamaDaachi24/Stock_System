FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc netcat-openbsd curl \
    && pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

COPY . .

EXPOSE 8000

# Wait for postgres, run migrations, seed admin, start server
CMD ["sh", "-c", "\
    echo 'Waiting for postgres...' && \
    while ! nc -z postgres 5432; do sleep 1; done && \
    sleep 2 && \
    echo 'Running migrations...' && \
    python -m alembic upgrade head && \
    echo 'Seeding admin user...' && \
    python -m scripts.seed_admin && \
    echo 'Starting server...' && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
