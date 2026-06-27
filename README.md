# Alma Lead Intake

Monorepo: **Next.js** frontend + **FastAPI** backend + **PostgreSQL** + local file uploads.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Node.js** 18+ | Next.js | [nodejs.org](https://nodejs.org) |
| **Python** 3.11+ | FastAPI | [python.org](https://python.org) |
| **Docker Desktop** | PostgreSQL + Mailpit (recommended) | [docker.com](https://www.docker.com/products/docker-desktop/) |

No accounts required for local dev (no GitHub, Resend, or OpenAI until you choose to add them).

> **Note:** Docker was not detected in the initial setup environment. Install Docker Desktop for the easiest DB/email stack, or install [PostgreSQL for Windows](https://www.postgresql.org/download/windows/) and match credentials in `.env`.

## Quick start

### 1. Environment

```powershell
copy .env.example .env
```

### 2. Infrastructure (PostgreSQL + Mailpit)

```powershell
docker compose up -d
```

Mailpit UI: http://localhost:8025

### 3. Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health

### 4. Frontend (Next.js)

New terminal:

```powershell
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

## Project layout

```text
backend/          FastAPI — API, auth, DB, files, email
frontend/         Next.js — public form + internal UI
docs/             Requirements, architecture, entities, features
docker-compose.yml
uploads/          Created at runtime for resume files
```

## Documentation

See `docs/` — especially `ARCHITECTURE.md`, `entities/`, and `FEATURES.md`.
