# API service — FastAPI

REST API: auth, business rules, database access, file I/O, email. Entity-scoped code under `app/domains/`.

## Layout

```text
api/
├── app/
│   ├── main.py              # PKG-6 — app factory, router mounts
│   ├── core/                # Shared infra + auth
│   └── domains/             # One folder per entity
└── tests/domains/
```

Migrations: `../db/alembic/` · File uploads: `../storage/uploads/` · Postgres: via Docker (root `docker-compose.yml`).

## Agent order

See [docs/entities/API_CATALOG.md](../docs/entities/API_CATALOG.md) — PKG-0 → PKG-6.

## Run locally

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Requires Postgres (`docker compose up -d` from repo root) and `.env` from `.env.example`.
