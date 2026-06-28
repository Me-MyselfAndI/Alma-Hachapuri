# Alma Lead Intake

Monorepo with **four components**: web application, API service, database, and file storage.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Node.js** 18+ | Web application | [nodejs.org](https://nodejs.org) |
| **Python** 3.11+ | API service | [python.org](https://python.org) |
| **Docker Desktop** | Database + Mailpit (recommended) | [docker.com](https://www.docker.com/products/docker-desktop/) |

No accounts required for local dev (no GitHub, Resend, or OpenAI until you choose to add them).

> **Note:** Docker was not detected in the initial setup environment. Install Docker Desktop for the easiest DB/email stack, or install [PostgreSQL for Windows](https://www.postgresql.org/download/windows/) and match credentials in `.env`.

## Quick start

### One command (after setup)

From the **repo root** (clone anywhere — no fixed drive path):

```powershell
python scripts/setup.py   # once: venv, pip, npm, .env
python scripts/dev.py run --target both   # Docker + migrations + API + webapp
```

Or: `npm run setup` then `npm run dev` (full stack). Aliases: `npm start` / `python scripts/start.py`. Test and build: `npm test`, `npm run build`. See [docs/RUN_LOCALLY.md](docs/RUN_LOCALLY.md).

Stop with **Ctrl+C**.

### Manual steps (optional)

<details>
<summary>Run each component separately</summary>

#### 1. Environment

```powershell
copy .env.example .env
```

#### 2. Database + Mailpit (Docker)

```powershell
docker compose up -d
```

Mailpit UI: http://localhost:8025

#### 3. API service (FastAPI)

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health

#### 4. Web application (Next.js)

New terminal:

```powershell
cd webapp
npm install
npm run dev
```

App: http://localhost:3000

</details>

## Project layout

```text
webapp/           Web application (Next.js) — public form + internal UI
api/              API service (FastAPI) — business logic, auth, I/O
db/               Database (PostgreSQL) — Alembic migrations
storage/          File storage — resume uploads (local disk; S3 later)
docs/             Requirements, architecture, entities, features
docker-compose.yml   Postgres + Mailpit for local dev
```

## Documentation

**Local setup:** [docs/RUN_LOCALLY.md](docs/RUN_LOCALLY.md)

See `docs/` — especially `ARCHITECTURE.md`, `entities/`, and `FEATURES.md`.
