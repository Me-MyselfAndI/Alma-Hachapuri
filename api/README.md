# API service — FastAPI

REST API: auth, business rules, database access, file I/O, email. Entity-scoped code under `src/domains/`.

## Layout

```text
api/
├── src/                     # Application code
│   ├── main.py              # App factory + router mounts
│   ├── core/                # Shared infra + auth
│   └── domains/             # One folder per entity
└── tst/                     # Pytest tests, mirror domain layout
    └── domains/
```

Migrations: `../db/alembic/` · File uploads: `../storage/uploads/` · Postgres: via Docker (root `docker-compose.yml`).

## Build order

See [docs/entities/API_CATALOG.md](../docs/entities/API_CATALOG.md) — Database foundation → Permissions → Account & login → Prospect & resume → Lead & state history → Email → Router wiring.

## Run locally

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

## Run tests

```powershell
cd api
python -m pytest tst/ -q
```

Requires Postgres (`docker compose up -d` from repo root) and `.env` from `.env.example`.

## Database migrations

Schema is owned by Alembic in `../db/alembic/`. Apply the schema before running the API:

```powershell
cd ../db
..\api\.venv\Scripts\python.exe -m alembic upgrade head
```

See [`../db/README.md`](../db/README.md) for migration authoring details.
