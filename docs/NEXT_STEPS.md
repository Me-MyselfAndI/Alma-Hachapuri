# Next steps — audit follow-up

Tracks open work and deferred items. Uses plain descriptions — see [FIXES_LOG.md](FIXES_LOG.md) for completed backend fixes.

---

## Done recently

| Item | What changed |
|------|----------------|
| **Lead auto-assignment** | New leads assign to the **active attorney with the fewest in-process leads** (`PENDING`, `REACHED_OUT`, `QUALIFIED`, not archived). If **no active attorney** exists → **503** `"No active attorney available for lead assignment"`. `is_default_assignee` kept for admin D4 guards only. |
| **Public intake validation** | `POST /api/v1/leads/verification-requests` validates name/email via Pydantic (`EmailStr`, length, strip whitespace) → **422** on bad input. |
| **Rate limiting (slowapi)** | Same endpoint: **5 requests/minute per IP** (configurable). **429** when exceeded. Disabled in tests via `RATE_LIMIT_ENABLED=false`. |
| **Verification email policy** | Only sent from public form submit. Staff **cannot** retry failed verification emails — applicant resubmits the form. |
| **Attorney write scope tests** | Service + HTTP route tests: attorneys blocked from mutating unassigned leads; admin can mutate any. |
| **HTTP route RBAC tests** | `role_client` fixture + `test_lead_routes.py` — real accounts, permissions enforced. |
| **Lead list performance** | Assignee names batch-loaded (one query per page, not per row). |
| **CSV export** | Adds `state_changed_at`, `archived_at`; `X-Export-Total-Count` + `X-Export-Truncated` when over 10,000 rows. |

**Tests:** run `cd api && .venv\Scripts\python.exe -m pytest tst -q`

---

## Deferred — implement later

| Item | Plan |
|------|------|
| **Rate limiting on public intake** | **Done** — slowapi on `POST /api/v1/leads/verification-requests`; see `VERIFICATION_REQUEST_RATE_LIMIT`. |
| **Verification email retry ordering** | **Removed** — staff cannot retry verification emails; applicant resubmits the form. |
| **API starts when DB/seed failed** | Startup seed failure is logged but API still boots; `/health` stays ok. Options: fail-fast env flag or readiness probe checking DB + at least one active attorney. |
| **Resume purge background job** | `RESUME_RETENTION_DAYS` configured; no scheduler deletes files after archive + retention window. |
| **Real resume LLM enrichment** | Replace dummy JSON; optional resume text preview API for UI + model input. |
| **Operational error tracking** | Sentry/Logfire/email alert on misconfiguration and unexpected 5xx. |
| **Production SMTP (TLS + auth)** | Current mail uses plain `SMTP(host, port)` — fine for Mailpit; production needs TLS, credentials, and likely a relay (SendGrid, SES, etc.). |
| **Staff webapp** | Public pages done; staff list/detail/transitions per [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md). |

---

## Open — medium / low

| Item | Status | Notes |
|------|--------|-------|
| **Assignee can be intake coordinator** | Confirm product intent | `PATCH /api/v1/leads/{id}` allows assigning to attorney **or** intake coordinator. Docs mention `list_assignable_accounts()` API — not built. |
| **Verification token in email URL** | Low risk for v1 | Token is one-time; still visible in logs/Referer if user clicks email link (GET). Webapp verify page should POST. |
| **Enrichment not durable** | By design for now | Post-verify enrichment uses in-process `BackgroundTasks` — lost on restart. Real job queue if enrichment becomes critical. |
| **Seed does not repair missing attorneys** | Document / optional fix | Seed is insert-only; won't recreate deactivated attorneys. Load-balancing needs ≥1 active attorney. |
| **Logout is client-side only** | Intentional v1 | Stateless JWT — server returns 204; client clears cookie/token. |
| **Doc / cosmetic drift** | Low | Entity checklists unchecked, `SESSION_CONTEXT.md` stale, Python version strings differ across READMEs. |

---

## Reference — elaborations

### API starts even when setup failed

On startup the app calls demo-account seed inside a try/except. If Postgres is down or seed fails, the process still listens on port 8000 and `/health` returns ok. The first **email verify → create lead** call may then fail with **503** (no active attorney). Mitigations: document in run-local guide, add `/health/ready` that checks DB + `SELECT 1` active attorney, or `FAIL_FAST_ON_SEED_ERROR=true`.

### Verification email retry can invalidate the link

When staff retries a failed verification email, the system generates a **new** token and updates the database **before** sending. If SMTP fails again, the prospect's original link no longer works and they never received the new one. Fix: send first, update token only on success (or rollback token on failure).

### Rate limiting

Implemented with **slowapi** on `POST /api/v1/leads/verification-requests`. Default **5/minute per client IP**. Env: `RATE_LIMIT_ENABLED`, `VERIFICATION_REQUEST_RATE_LIMIT`. In-memory storage (fine for single instance); use Redis storage URL for multi-instance later.

### Public intake validation — approach used

**Pydantic v2** (already in stack): `LeadVerificationRequestInput` with `EmailStr`, `StringConstraints(strip_whitespace=True, min_length=1, max_length=100)`. Resume file rules stay in `validate_resume_file()` (type, size). No new dependency.

### Assignee = intake coordinator

Manual reassignment allows coordinators, not just attorneys. Auto-assign on create picks **attorneys only** (load-balanced). If coordinators should never own leads, narrow PATCH validation; if they should, add them to the assignee picker API when built.

### Verification token in URL — is it an issue?

**Moderate, not critical** for v1: tokens are single-use and short-lived (24h). Risk is leakage via proxy logs, browser history, or Referer if the verify page loads third-party assets. Mitigation: webapp verify page reads `?token=` client-side then **POST**s to `/api/v1/leads/verify` so the token doesn't stay in server access logs on verify. Email links may still use GET for one-click compatibility.

### Non-deterministic default assignee flag

Admin `is_default_assignee` is now **orthogonal** to intake assignment (load balancing). Multiple defaults are still bad for D4 admin guards — `resolve_default_assignee` now uses `ORDER BY created_at` for determinism when checking admin config.

### Enrichment durability

`BackgroundTasks` run in the same process after the HTTP response. Server restart = task lost; lead exists but `custom_fields` may stay empty. Acceptable for optional dummy enrichment; use Celery/RQ/ARQ + Redis when real LLM enrichment matters.

### Seed does not heal broken config

Re-running seed skips existing emails — it won't reactivate a deactivated attorney or create one if all were deleted. Operations need at least one active `role=attorney` account for intake to work.

---

## Related docs

- [FIXES_LOG.md](FIXES_LOG.md) — completed audit fixes
- [FEATURES.md](FEATURES.md) — kanban
- [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) — staff UI next
