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
| A4 | **Attorneys use the internal system** — log in as an `accounts` row with `role=attorney`, view leads, take permitted actions | Auth/RBAC scope if attorneys are email-only | Open |
| A5 | **Attorney is a role on `accounts`, not a separate table** — merged model (see decision log 2026-06-27); prospects never get accounts | Separate login surfaces, duplicate identity | Confirmed |
| A7 | **Optional `source` on lead** (referral, organic, etc.) — not in brief; cheap metadata | Nullable field only | Open |
| A8 | **LLM custom-field enrichment is optional** — behind a feature flag; failure must not block lead submission | Async path + graceful degradation | Open |
| A9 | **Lead assignment on create** — auto-assign default attorney (`accounts.role=attorney` + `is_default_assignee=true`); manual override via L4; stored as **`assigned_account_id`** FK → `accounts.id` (not a separate attorney entity) | Notification routing, write-scope rules | Confirmed |

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
| 2026-06-27 | File storage: local `storage/uploads/` with swappable storage interface | — |
| 2026-06-27 | Lead assignment: auto-assign default attorney on create; manual override (F6.1 direction) | — |
| 2026-06-27 | Merge Account + Attorney → single `accounts` table; **`assigned_account_id`** on leads (attorney = role value, not separate entity) | Separate attorneys table; `assigned_attorney_id` column name |
| 2026-06-27 | RBAC: `accounts.role` enum (immutable) + `ROLE_PERMISSIONS` in code | roles/permissions DB tables |
| 2026-06-27 | Lead states (superseded): PENDING, REACHED_OUT, IN_CONTACT, QUALIFIED, DISQUALIFIED, ON_HOLD, CLOSED | Brief minimum only |
| 2026-06-27 | Lead states (current): PENDING ⇄ REACHED_OUT (whose-turn ping-pong) + QUALIFIED / DISQUALIFIED → CLOSED. Dropped IN_CONTACT & ON_HOLD — "how long waiting / going cold" derived from `leads.state_changed_at` timestamp instead of extra statuses | 7-state model above |
| 2026-06-27 | **Email verification before lead create** — public intake sends verification email with link; **lead row created only after** link clicked (see Flow A1/A2) | Immediate create on form submit |
| 2026-06-27 | **API guardrail decisions (F2.3):** D1/D2 attorneys **read all** leads/resumes (write still scoped); D3 **archived leads fully accessible**; D5 default assignee must be **active**; D6 `is_default_assignee` on non-attorney → **422**; D7 email **lowercase normalized** on write; D9 prospect routes **in v1** | — |
| 2026-06-27 | **D8** — same-status transition is a **no-op, no history row** | — |
| 2026-06-27 | **D4** — if no active attorney exists with `is_default_assignee=true` when VerifyEmailAndCreateLead runs, the API **throws a misconfiguration error** that is captured by the error-tracking hook (F8.1). Admin-update guards (see decision below) make this state unreachable in normal operation; the error is for the unlucky edge case (deploy without seed, race condition). | "explore options" |
| 2026-06-27 | **Admin-update guards** on `accounts`: cannot clear `is_default_assignee` on the only active default attorney; cannot deactivate the only active default attorney. New default must be set in the same transaction. | — |
| 2026-06-27 | **F2.5 retention:** `RESUME_RETENTION_DAYS = 365` default; background job purges resume files (and DB row) after that many days past `archived_at` | — |
| 2026-06-27 | **Webapp auth (Q-W1):** staff session in **HttpOnly cookie** set by Next.js route (`POST /api/auth/login`); JWT not exposed to client JS; Next forwards Bearer to FastAPI | localStorage proposal |
| 2026-06-27 | **Webapp decisions (Q-W2–Q-W12):** bootstrap `/auth/me` (W2-A); middleware (W3-B); landing (W4-C); Next proxy (W5-B); resume Next proxy (W6-B); verify POST+GET (W7-C); transition buttons (W8-A); friendly 403 (W9-B); client fetch (W10-A); filters state+mine (W11-B+C); shadcn (W12-B) | — |
| 2026-06-27 | **Product brand:** **Hachapuri** (not Alma — Alma is assessment sender only). Staff + public UI use this name. | — |
| 2026-06-27 | **Staff UI product choices:** "Waiting since" list column in v1; state transitions immediate (no confirm modal); stretch features (history, email log, export, assignee UI, admin) deferred per `WEBAPP_STAFF_LAYOUT_PLAN.md` §9.1 | — |
| 2026-06-27 | **DownloadResume** allowed for **archived** leads; resume **retention/deletion policy** after configurable period (feature F2.5) | Block download when archived |