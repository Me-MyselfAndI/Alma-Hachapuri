# Database — PostgreSQL

Structured data for the lead intake system. **PostgreSQL** locally via Docker; Alembic migrations live here.

## Layout

```text
db/
├── alembic/           # Schema migrations
│   └── versions/
└── README.md
```

## Local run

From repo root:

```powershell
docker compose up -d postgres
```

Connection (default): `postgresql://alma:alma@localhost:5432/alma` — see root `.env.example`.

## Migrations

Alembic is wired up: `db/alembic.ini` + `db/alembic/env.py` import the
application's settings and ORM metadata from `../api/src/` (env.py prepends
`api/` to `sys.path`, then imports `src.domains` so every model is registered
on `Base.metadata` before autogenerate runs).

```powershell
# From repo root (preferred — paths are repo-relative):
python scripts/start.py --skip-webapp

# Or run Alembic directly from db/:
cd db
../api/.venv/Scripts/python.exe -m alembic upgrade head   # Windows
# ../api/.venv/bin/python -m alembic upgrade head         # macOS/Linux
```

The initial schema (all 7 tables: `accounts`, `prospects`, `leads`,
`resume_files`, `lead_state_history`, `email_notifications`,
`lead_intake_pending`) lives in `alembic/versions/` and was generated with
`alembic revision --autogenerate -m "initial schema"` against a live local
Postgres (`docker compose up -d postgres` from the repo root).

To create a new migration after changing models:

```powershell
cd db
..\api\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

## Who uses this

Only the **API service** (`../api/`) connects to Postgres. The webapp never talks to the database directly.
