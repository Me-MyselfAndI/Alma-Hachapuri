# Assumptions

Facts we treat as true but the brief does not fully specify — without them the project does not hang together. These are **not** tech stack choices (see `ARCHITECTURE.md`) and **not** settled design work still in **PLAN** (see `FEATURES.md`).

When an assumption is confirmed or replaced, note it in the decision log.

---

## Product & domain

| ID | Assumption | Impact if wrong | Status |
|----|------------|-----------------|--------|
| A1 | **Single organization** — one firm / company; no multi-tenant isolation for v1 | Org scoping on all entities and auth | Open |
| A2 | **Prospect is a durable entity**, separate from Lead; **one prospect → many leads** (same person identified by email may submit again) | Duplicate prospect rows or lost history | Confirmed |
| A3 | **Lead** holds required intake fields, optional metadata (e.g. `source`), state, resume reference, and optional `custom_fields` JSON | Drives API schema and DB design | Open |
| A4 | **Attorneys use the internal system** — log in, view leads, take actions on leads they are permitted to work | Auth/RBAC scope if attorneys are email-only | Open |
| A5 | **Attorney is an internal role** — `User` with role(s), optionally linked to an `Attorney` profile; prospects never get accounts | Separate login surfaces, duplicate identity | Open |
| A7 | **Optional `source` on lead** (referral, organic, etc.) — not in brief; cheap metadata | Nullable field only | Open |
| A8 | **LLM custom-field enrichment is optional** — behind a feature flag; failure must not block lead submission | Async path + graceful degradation | Open |
| A9 | **Lead assignment on create** — auto-assign default attorney; manual override allowed; stored as `assigned_attorney_id` | Notification routing, write-scope rules | Open |

---

## Users & access

| ID | Assumption | Impact if wrong | Status |
|----|------------|-----------------|--------|
| A11 | **Prospects never authenticate** — public form only; no prospect portal | Broader auth and UI scope | Open |
| A17 | **Resumes contain PII** — careful storage; no resume body in application logs by default | Security and compliance posture | Open |

---

## Decision log

| Date | Decision | Supersedes |
|------|----------|------------|
| 2026-06-27 | One prospect → many leads (same email re-submit creates new lead, same prospect) | — |
| 2026-06-27 | Auth: JWT in FastAPI (OAuth2 password flow) | — |
| 2026-06-27 | Database: PostgreSQL (docker-compose locally) | — |
| 2026-06-27 | File storage: local `./uploads/` with swappable storage interface | — |
| 2026-06-27 | Lead assignment: auto-assign default attorney on create; manual override (F6.1 direction) | — |
