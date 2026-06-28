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

Migrations: `db/alembic/` · File uploads: `storage/uploads/` · Postgres: via Docker (root `docker-compose.yml`).

Configuration and uploads paths are resolved from the **repo root** (`api/src/core/paths.py`). The root `.env` file is loaded automatically — you do not need to copy it into `api/` unless you want overrides.

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

Schema is owned by Alembic in `db/alembic/`. Applied automatically by `python scripts/start.py`, or manually:

```powershell
# From repo root
python scripts/start.py --skip-webapp --skip-docker   # migrate + API only, if Docker already up

# Or run Alembic directly:
cd db
../api/.venv/Scripts/python.exe -m alembic upgrade head   # Windows
# ../api/.venv/bin/python -m alembic upgrade head         # macOS/Linux
```

See [`db/README.md`](../db/README.md) for migration authoring details.
