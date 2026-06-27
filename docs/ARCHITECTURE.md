# Architecture

Architecture-relevant view of the project: requirements that drive design, domain model, technical choices, and access model. Original brief lives in `REQUIREMENTS.md`. Unspecified truths we rely on live in `ASSUMPTIONS.md`. Work still to scope lives in `FEATURES.md` (**PLAN**).

---

## System overview

The brief mandates **FastAPI** (API) and **Next.js** (web app). That is an architectural choice, not a deployment choice — it does **not** mean “everything runs locally.” Local is how we **develop and demo**; production is still the same **two-process, client–server** shape.

### What the stack implies

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Web app** | Next.js | Public lead form, internal authenticated UI, routing, client state |
| **API** | FastAPI | REST (or similar) endpoints, auth, validation, business logic, file ingest |
| **Data** | Database + blob storage | Leads, prospects, users; resume files |
| **External** | Email provider (+ optional LLM) | Transactional mail; async enrichment |

Next.js does **not** replace the backend — it talks to FastAPI over HTTP. That forces:

- An explicit **API contract** (routes, request/response shapes, errors)
- **CORS** (and/or a BFF/proxy) when browser and API are on different origins
- **Auth across services** — token or cookie strategy shared by Next.js and FastAPI
- **File upload flow** — browser → API (multipart), API → blob storage (not “upload straight to DB from React”)
- **Two deployable units** (minimum) in any real environment

### Local vs deployed

| | Local dev | Deployed (assessment / production) |
|---|-----------|-------------------------------------|
| **Purpose** | Run locally, Loom demo, README instructions | Same architecture, reachable URLs |
| **Next.js** | `localhost:3000` | Vercel, container, or static+SSR host |
| **FastAPI** | `localhost:8000` | Container, Railway, Fly.io, etc. |
| **Database** | SQLite or Docker Postgres | Managed Postgres (or equivalent) |
| **Files** | Local `./uploads` or MinIO | S3-compatible bucket |
| **Email** | Mailpit / Mailhog / console / real API with test key | Real transactional provider |

“Run locally” in submission guidance means **you can stand the full stack up on a developer machine** — not that the design is local-only or monolithic.

### Component diagram

```text
                    ┌─────────────────────────────────────┐
                    │           Next.js (web)              │
                    │  ┌─────────────┐ ┌───────────────┐  │
                    │  │ Public form │ │ Internal UI   │  │
                    │  │ (no auth)   │ │ (auth)        │  │
                    │  └──────┬──────┘ └───────┬───────┘  │
                    └─────────┼────────────────┼──────────┘
                              │ HTTP           │
                              ▼                │
                    ┌─────────────────────────┴──────────┐
                    │         FastAPI (API)               │
                    │  /leads  /auth  /users  /uploads    │
                    └───┬─────────┬──────────┬───────────┘
                        │         │          │
            ┌───────────▼──┐  ┌───▼───┐  ┌───▼────────┐
            │  PostgreSQL  │  │ Blob  │  │ Email API  │
            │  (or SQLite) │  │ store │  │ (+ LLM)    │
            └──────────────┘  └───────┘  └────────────┘
```

### Alternative they did *not* ask for

A single **Next.js full-stack** app (Route Handlers / Server Actions only, no FastAPI) would be simpler to deploy but **violates the brief**. The mandated split is the architecture.

### Repository layout (proposed)

Monorepo — one Git repo, two apps, shared docs:

```text
AlmaAssessment/
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── api/                # Routers (leads, auth, users, health)
│   │   ├── core/               # Config, security, deps
│   │   ├── models/             # DB models (SQLAlchemy)
│   │   ├── schemas/            # Pydantic request/response
│   │   ├── services/           # Business logic, email, storage, LLM jobs
│   │   └── main.py             # App entrypoint
│   ├── alembic/                # Migrations (if Postgres)
│   ├── tests/
│   ├── pyproject.toml          # or requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js
│   ├── app/                    # App Router pages
│   │   ├── (public)/           # Lead form — no auth
│   │   └── (internal)/         # Leads list/detail — auth required
│   ├── components/
│   ├── lib/                    # API client, auth helpers
│   ├── package.json
│   └── Dockerfile
├── docs/                       # Requirements, architecture, features, …
├── docker-compose.yml          # API + web + Postgres + Mailpit (local)
├── .env.example                # Shared env var template
└── README.md                   # How to run locally
```

| Path | Owns |
|------|------|
| `backend/` | All persistence, auth validation, file storage, email send, background jobs |
| `frontend/` | UI only; calls backend via `NEXT_PUBLIC_API_URL` (or Next.js rewrite proxy) |
| `docs/` | Design/requirements — not runtime |
| `docker-compose.yml` | One command to boot the full stack for demo |

**Boundary rule:** frontend never talks to the DB or email provider directly — always through FastAPI.

---

## Requirements → architecture mapping

| Requirement (brief) | Architectural consequence |
|---------------------|----------------------------|
| Public lead form + file upload | Public API route, file validation, blob storage, no auth |
| Emails to prospect + attorney | Email adapter, templates, outbound log (recommended) |
| Authenticated internal UI | Auth layer, session/JWT, protected API routes |
| Lead state updates | State field + history/audit (recommended) |
| FastAPI + Next.js | **Separate web and API tiers** — see [System overview](#system-overview) |
| Persist data + email service | Database + external email provider (choices below) |

---

## Domain entities

Detailed schemas: [`entities/`](entities/README.md).

| Entity | Purpose | Key relationships |
|--------|---------|-------------------|
| **Prospect** | Person who may submit multiple times; anchor for communication | 1 prospect → N leads |
| **Lead** | Intake submission: required fields, state, source, resume ref, `custom_fields` | N leads → 1 prospect; assigned attorney (planned) |
| **User** | Internal account (login) | Has [Role](entities/role.md); may link 1:1 to Attorney profile |
| **Attorney** | Staff profile for lead handlers | Linked to User; assignment + notifications (planned) |
| **Resume / file asset** | Stored CV + metadata (name, mime, size, storage key) | 1 resume → 1 lead (v1) |
| **Email notification** (recommended) | Outbound log: recipient, template, status, lead_id | Audit, retries, debugging |
| **Lead state history** (recommended) | Who changed state, when, from → to | Audit for internal UI |

**Config / constants (not entities):** feature flags (env), email templates (code/config).

**RBAC entities:** [Role](entities/role.md), [Permission](entities/permission.md), join `role_permissions` — see `entities/`.

**Explicitly out of scope (v1):** Campaign (mass outreach), Case/Matter (see below).

---

## Lead vs case / matter

| Concept | What it is | In this project? |
|---------|------------|------------------|
| **Lead** | Pre-client intake — form submission, screening, first contact | **Yes** — core entity |
| **Case / matter** | Formal legal engagement after retention — client file, filings, deadlines, billing, opposing counsel | **No** — downstream practice-management concern |

The brief covers **individual intake processing**: submit → notify → attorney reaches out → mark state. It does not cover signing a client, opening a matter, court calendar, or document production. A lead might *become* a client/matter in a real firm, but that conversion is outside this assignment unless we explicitly expand scope.

---

## Technical choices

Decisions we make to implement the brief — not assumptions. **The brief does not specify database or hosting**; only “persist data” + FastAPI + Next.js. Those remain open until we pick them below.

### Decided

| Area | Choice | Notes |
|------|--------|-------|
| **API framework** | FastAPI | Required by brief |
| **Web framework** | Next.js | Required by brief |
| **Architecture** | Split monorepo — frontend calls API over HTTP | See [System overview](#system-overview) |
| **Auth** | JWT in FastAPI (OAuth2 password flow) | Next.js login → `/auth/token`; Bearer on internal routes |
| **Database** | PostgreSQL via docker-compose (local) | SQLAlchemy + Alembic; RDS on AWS later |
| **File storage** | Local `./uploads/` + storage interface | S3 adapter swap later |

### Recommended rationale (archived)

| Area | Why this pick | AWS equivalent |
|------|---------------|------------------|
| JWT in FastAPI | Built-in patterns; no Cognito setup | Cognito |
| PostgreSQL docker | Production-credible; one compose service | RDS / Aurora |
| Local uploads | Zero config for assessment demo | S3 |

**Auth flow (minimal):**

```text
Next.js login form → POST /auth/token (FastAPI) → JWT
Internal pages → Authorization: Bearer <token> on API calls
Public lead form → no auth
```

**Not recommended for speed (this project):**

| Option | Why skip for v1 |
|--------|-----------------|
| Cognito / Auth0 | Extra service, callback URLs, user pool setup |
| NextAuth + multiple providers | More wiring for split stack; Credentials provider still calls FastAPI |
| MinIO in docker | S3-compatible but extra container; local disk is enough for demo |
| SQLite only | Fastest boot, but weaker story for relational demo + migrations at scale |

### Who talks to what

PostgreSQL and `./uploads` are **not** standalone products you call from the browser. **FastAPI sits in the middle** and owns all backend I/O.

```text
Next.js  ──HTTP (REST)──▶  FastAPI  ──SQL──▶       PostgreSQL
                           FastAPI  ──read/write──▶  ./uploads/  (or S3)
                           FastAPI  ──SMTP/API──▶    Email provider
```

| Component | What it is | Who uses it |
|-----------|------------|-------------|
| **Next.js** | UI | Browser; calls **FastAPI only** |
| **FastAPI** | Your API + business logic | SQLAlchemy/psycopg → Postgres; writes files to disk; sends email |
| **PostgreSQL** | Database server (docker locally, RDS on AWS) | **FastAPI only** — not exposed to frontend |
| **`./uploads/`** | Folder on the API server's disk | **FastAPI** saves CV on POST; serves download via e.g. `GET /leads/{id}/resume` |

So: Postgres replaces “where rows live”; local uploads replace “where files live.” **You still implement** the FastAPI routes (`POST /leads`, file handling, etc.). Same pattern as AWS — RDS and S3 don't replace FastAPI; FastAPI uses them.

### Still open

| Area | Options | Notes |
|------|---------|-------|
| **Hosting** | Local + docker-compose for demo | Cloud optional for submission |
| **Email** | **Mailpit** (local) + **Resend** or SES (real) | Mailpit = fastest local; Resend = simple API |
| **LLM enrichment** | OpenAI API | Async background task; feature flag |

---

## Roles & permissions (draft)

Permission **types** and candidate roles are **PLAN** (`F6.2`). Exact role→permission mapping is deferred.

### Permission dimensions (may vary by role)

| Permission | Meaning |
|------------|---------|
| `read_leads` | View lead list and detail |
| `write_lead` | Update lead fields / state (may be scoped to assigned leads only) |
| `assign_lead` | Change `assigned_attorney_id` |
| `read_prospect` | View prospect profile and linked leads |
| `manage_users` | Create/disable internal users |
| `manage_attorneys` | Manage attorney profiles |

### Candidate roles (mapping TBD)

| Role | Typical user |
|------|--------------|
| **admin** | Firm admin, IT |
| **attorney** | Licensed attorney |
| **intake_coordinator** | Paralegal / intake staff |
| **readonly** | Partner, reporting |

**Assignment model (`F6.1`):** Auto-assign default attorney on create; manual override. How assignment interacts with `write_lead` scope — TBD in F6.2.

---

## AWS mapping (illustrative)

If we deployed on AWS instead of local/docker, the brief’s **FastAPI** and **Next.js** map to compute/hosting layers — not to managed data or messaging services.

| Concern | AWS service (typical) | Maps to in our stack |
|---------|----------------------|----------------------|
| **Web UI** | Amplify Hosting, S3 + CloudFront, or ECS/Fargate serving Next.js | **Next.js** — pages, public form, internal UI |
| **HTTP API** | API Gateway + Lambda *or* ALB + ECS/Fargate *or* App Runner | **FastAPI** — REST, auth, business logic, file ingest |
| **Relational data** | RDS (PostgreSQL) or Aurora | **PostgreSQL** (docker locally) |
| **Resume files** | S3 | **Local `./uploads`** (S3 adapter later) |
| **Outbound email** | SES | **Still TBD** — called from FastAPI |
| **Async LLM job** | SQS + Lambda, or background worker on ECS | **Still TBD** — triggered by FastAPI after lead create |
| **Secrets / config** | Secrets Manager, SSM Parameter Store | Feature flags, API keys |
| **Auth (optional)** | Cognito | **JWT in FastAPI** (recommended for v1) |

**Summary:** Next.js replaces a **static/SSR web host**. FastAPI replaces an **API compute tier** (Lambda or container). Database, files, email, queue, and auth provider remain **separate AWS services** — same separation as in the architecture diagram.

---

## Feature flags

Standard config — no extra entity complexity:

- `ENABLE_LLM_ENRICHMENT` — run resume extraction job
- (Future) e.g. `ENABLE_AUTO_ASSIGN` — toggle default assignment behavior

---

## Related docs

- `REQUIREMENTS.md` — original brief
- `ASSUMPTIONS.md` — unspecified truths we rely on
- `FEATURES.md` — backlog and **PLAN** items
