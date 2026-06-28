# Backend fixes log

Changelog of API/backend fixes applied during the 2026-06-27 audit and follow-up sessions. Excludes webapp work.

For open items and deferred work, see [NEXT_STEPS.md](NEXT_STEPS.md).

---

## Summary

| Area | Fixes |
|------|-------|
| Lead intake (L1b) | Atomic verify claim, idempotent retry, 422 on bad pending data |
| Email (E3) | Verification retry reissues working token |
| LLM enrichment (F7.1) | Dummy extractor + background queue |
| Lead API (L2/L3) | `archived_at` exposed on responses |
| Storage (F2.5) | Retention days config wired (job still TBD) |
| Docs | 5-state lifecycle, A9 attorney/account, JWT auth model |

**Tests:** 251 passing (`api/tst/`). Run: `cd api && .venv\Scripts\python.exe -m pytest tst -q`

**Migration required:** `c4e8f2a1b3d6` adds `lead_intake_pending.lead_id`.

---

## 1. L1b concurrent verify — atomic claim + idempotent retry

**Problem:** Two simultaneous verify requests with the same token could both create a lead (race on `used_at`).

**Solution:** Row-level lock + claim at start + `lead_id` for idempotent retries.

| File | Change |
|------|--------|
| `api/src/domains/lead/intake_claim.py` | **New.** `load_pending_for_verify` (`SELECT … FOR UPDATE`), `claim_pending_for_verify`, `resolve_completed_lead` |
| `api/src/domains/lead/service.py` | `verify_and_create_lead` uses claim module; sets `pending.lead_id` on success |
| `api/src/domains/lead/models.py` | Added nullable `lead_id` FK → `leads.id` on `LeadIntakePending` |
| `api/src/core/config.py` | `verification_processing_stale_minutes` (default **5**) |
| `.env.example` | `VERIFICATION_PROCESSING_STALE_MINUTES=5` |
| `db/alembic/versions/c4e8f2a1b3d6_pending_intake_lead_id.py` | **New migration** |

**Behavior:**

| Situation | HTTP | Notes |
|-----------|------|-------|
| First verify | 201 | Sets `used_at` at claim start, `lead_id` on commit |
| Retry after success | 201 | Same `lead_id` — no duplicate lead, S7 not re-run |
| Concurrent in-flight (&lt; 5 min, no `lead_id`) | 409 | `"Verification already in progress"` |
| Stuck claim (&gt; 5 min, no `lead_id`) | 201 | Stale reclaim allows retry |
| Expired token | 410 | Unchanged |

**Tests:** `api/tst/domains/lead/test_intake_claim.py`, updates in `test_lead_service.py` (`test_idempotent_retry_returns_same_lead`, `test_in_progress_returns_409`, `test_stale_claim_allows_retry`).

**Docs:** `docs/entities/lead.md` (pending table, L1b errors/side effects), `docs/NEXT_STEPS.md`.

---

## 2. L1b missing temp resume → 422 (not 500)

**Problem:** If the temp resume file was missing on disk at verify time, L1b returned an unhandled 500.

**Solution:** `_temp_resume_metadata` raises **422** with `"Pending intake data invalid: temp resume file missing"`.

| File | Change |
|------|--------|
| `api/src/domains/lead/service.py` | `_temp_resume_metadata` maps missing file to 422 |

**Tests:** `test_missing_temp_resume_returns_422` in `test_lead_service.py`.

---

## 3. Verification email retry (E3) — working link

**Problem:** E3 retry for failed `email_verification` emails used placeholder `RETRY_NOT_AVAILABLE` in the verify URL (raw token is never stored, only hash).

**Solution:** On retry, **reissue** a fresh token: update `token_hash` + extend `expires_at`, send email with valid link.

| File | Change |
|------|--------|
| `api/src/domains/lead/tokens.py` | **New.** `hash_verification_token`, `reissue_verification_token`, `ensure_utc` |
| `api/src/domains/email/service.py` | `retry_failed` calls `reissue_verification_token` for `email_verification` template |

**Tests:** `test_retry_verification_reissues_token` in `test_email_service.py`.

**Known follow-up:** If SMTP fails after reissue, token is invalidated before send succeeds — see [NEXT_STEPS.md](NEXT_STEPS.md) (reissue-after-send).

---

## 4. LLM enrichment dummy + background queue (F7.1)

**Problem:** `EnrichmentService` was a log-only stub; flag on gave false impression of working enrichment.

**Solution:** Dummy JSON written to `custom_fields`; runs via FastAPI `BackgroundTasks` after L1b response (non-blocking).

| File | Change |
|------|--------|
| `api/src/domains/lead/enrichment.py` | **New.** `extract_custom_fields_dummy`, `run_lead_enrichment`, `schedule_lead_enrichment` |
| `api/src/domains/lead/router.py` | L1b verify routes call `background_tasks.add_task(schedule_lead_enrichment, …)` when flag on |
| `api/src/domains/lead/service.py` | Removed inline `EnrichmentService` stub |

**Dummy payload shape:**

```json
{
  "_source": "dummy_llm_v1",
  "years_experience": 5,
  "primary_skills": ["communication", "project_management"],
  "education_level": "bachelors",
  "lead_id": "<uuid>"
}
```

**Config:** `ENABLE_LLM_ENRICHMENT=false` (default off).

**Tests:** `api/tst/domains/lead/test_enrichment.py`.

**Docs:** `docs/FEATURES.md` (F7.1 In Progress), `docs/entities/lead.md`, `docs/ARCHITECTURE.md`.

---

## 5. `archived_at` on lead list/detail responses

**Problem:** D3 requires archived leads to remain readable; prospect routes exposed `archived_at` but L2/L3 did not.

**Solution:** Added `archived_at` to API schemas and router builders.

| File | Change |
|------|--------|
| `api/src/domains/lead/schemas.py` | `archived_at` on `LeadRead` and `LeadListItem` |
| `api/src/domains/lead/router.py` | `_build_lead_read`, `_build_list_item` include `archived_at` |

---

## 6. Resume retention config (F2.5 — partial)

**Problem:** `RESUME_RETENTION_DAYS` documented in assumptions but missing from config; purge job not built.

**Solution:** Config + env wired; helper reads default from settings. **Background purge job still deferred.**

| File | Change |
|------|--------|
| `api/src/core/config.py` | `resume_retention_days: int = 365` |
| `.env.example` | `RESUME_RETENTION_DAYS=365` |
| `api/src/domains/resume_file/service.py` | `is_past_retention(..., retention_days=None)` uses settings when omitted |

---

## 7. Documentation corrections

| Topic | Files updated | Change |
|-------|---------------|--------|
| Lead state count | `docs/entities/lead.md`, `docs/entities/README.md` | **7-state → 5-state** (IN_CONTACT/ON_HOLD removed) |
| A9 assignment | `docs/ASSUMPTIONS.md` | Attorney = **role on `accounts`**; FK is **`assigned_account_id`**, not separate attorney entity |
| A4/A5 | `docs/ASSUMPTIONS.md` | Removed stale User/Attorney table language |
| JWT vs authorization | `docs/entities/account.md`, `permission.md`, `role.md`, `api/src/core/security.py`, `docs/ARCHITECTURE.md` | JWT `permissions[]` for **UI**; API **`require_permission` re-reads DB role** |
| Enrichment path | `docs/entities/lead.md` | Points to `enrichment.py`, not `api/src/services/enrichment.py` |
| L1b pending model | `docs/entities/lead.md` | `used_at` = claim start; added `lead_id` column |
| Kanban | `docs/FEATURES.md` | F7.1 In Progress; link to NEXT_STEPS |
| Audit tracking | `docs/NEXT_STEPS.md` | **New** — done/deferred/open items |

---

## New / moved modules

```
api/src/domains/lead/
  enrichment.py    # F7.1 dummy LLM + background worker
  intake_claim.py  # L1b row lock + claim outcomes
  tokens.py        # Token hash, reissue, UTC normalize (L1a, E3)
```

---

## Environment variables added

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENABLE_LLM_ENRICHMENT` | `false` | Turn on dummy enrichment after L1b |
| `RESUME_RETENTION_DAYS` | `365` | F2.5 retention window (purge job TBD) |
| `VERIFICATION_PROCESSING_STALE_MINUTES` | `5` | Reclaim stuck L1b pending rows |

---

## Migrations

| Revision | Description |
|----------|-------------|
| `c4e8f2a1b3d6` | `lead_intake_pending.lead_id` nullable FK → `leads.id` |

Apply:

```powershell
cd db
..\api\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## Explicitly not fixed (deferred)

Documented in [NEXT_STEPS.md](NEXT_STEPS.md):

- D4 misconfiguration → public **503** (still **500** today)
- F2.5 background purge job
- Real OpenAI / resume extraction (F7.1)
- E3 retry: reissue token only after successful SMTP
- Webapp (F5.x)
- F8.1 error tracking / alerting

---

## Related

- [NEXT_STEPS.md](NEXT_STEPS.md) — open items and verification steps
- [FEATURES.md](FEATURES.md) — kanban status
- [entities/lead.md](entities/lead.md) — L1a/L1b spec
