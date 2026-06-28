# Resume file

Metadata for an uploaded CV/resume. Binary stored on disk (`storage/uploads/`) or S3; this table holds the pointer.

---

## Purpose

- Track original filename, mime type, size, storage location
- Enable secure download via API (never expose raw filesystem path to client)

---

## Table: `resume_files`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `storage_key` | VARCHAR(500) | yes | Relative path or S3 key, e.g. `uploads/{uuid}.pdf` |
| `original_filename` | VARCHAR(255) | yes | As uploaded |
| `mime_type` | VARCHAR(100) | yes | e.g. `application/pdf` |
| `size_bytes` | INTEGER | yes | |
| `created_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `lead` | Lead | 1 file → 1 lead (v1) |

---

## Business rules

| Rule | Detail |
|------|--------|
| Allowed types | PDF, DOC, DOCX — validated on upload |
| Max size | 10 MB |
| Write | FastAPI saves bytes on `POST /leads`; insert row; link from lead |
| Read | `GET /leads/{id}/resume` streams file; auth internal only |
| Archived leads | Download allowed (D3); see [Preconditions](#preconditions) |
| Delete | Orphan cleanup on failed save; retention purge after archive (F2.5) |

---

## Preconditions

Readable operation names for API guardrails (F2.3). Route IDs (L5, S2, …) appear only in [Assigned API routes](#assigned-api-routes-agent-checklist). Permission checks are documented here but **out of scope** for F2.6 precondition unit tests.

| Operation | Who | Data / state rules | On failure |
|-----------|-----|-------------------|------------|
| **SaveResume** | Public (via CreateLead) | File required. Mime type ∈ {PDF, DOC, DOCX}. Size ≤ 10 MB. | 400 |
| **DownloadResume** | Internal — any account with `read_leads` | Lead must exist. Resume row + storage object must exist. **Archived leads allowed** (D3 — full read access to archived leads). Attorney/coordinator **read scope = all leads** with `read_leads`, not assignee-only (D1/D2); write remains assignee-scoped elsewhere. | 404 |
| **DeleteOrphanResume** | Internal (service rollback) | `storage_key` written but DB transaction rolled back. Best-effort delete from storage; no lead row required. | Log warning; do not fail caller |
| **PurgeExpiredResumes** | Background job (F2.5) | Lead has `archived_at` set. `now − archived_at ≥ RESUME_RETENTION_DAYS`. See [Retention & deletion policy](#retention--deletion-policy-f25). | Skip row; continue batch |

**DownloadResume — archived leads (confirmed):** Do **not** reject download when `leads.archived_at` is set. L14 archive is a soft-delete for list filtering only; resume binary remains downloadable until the retention job removes it.

**DownloadResume — attorney read scope (D1/D2):** Holders of `read_leads` (attorney, intake_coordinator, readonly, admin) may download any lead's resume regardless of `assigned_account_id`. Assignee scoping applies to **write** operations (`write_lead`), not read/download.

---

## Retention & deletion policy (F2.5)

Configurable cleanup of resume binaries after a lead is archived. Documented here; implementation tracked on feature board as **F2.5**.

| Setting | Default | Notes |
|---------|---------|-------|
| `RESUME_RETENTION_DAYS` | e.g. `365` | Env/configurable. `0` or unset disables automatic purge. |
| Clock anchor | `leads.archived_at` | Retention countdown starts when L14 sets archive timestamp. Active (non-archived) leads are never purged. |

**Background job — PurgeExpiredResumes**

1. Query leads where `archived_at IS NOT NULL` and `resume_file_id IS NOT NULL`.
2. For each row, if `now − archived_at ≥ RESUME_RETENTION_DAYS`:
   - Delete binary from storage via `storage_key` (local or S3 adapter).
   - **DB cleanup (implementer choice v1):** null `leads.resume_file_id` and delete `resume_files` row, *or* retain metadata row with tombstone flag. Prefer delete row + null FK for simpler DownloadResume 404 semantics.
3. Run on a schedule (e.g. daily cron / APScheduler). Idempotent — safe to re-run if file already gone.

**After purge:** **DownloadResume** returns **404** (resume missing). Lead row may remain archived for audit.

**Interaction with D3:** Archived leads stay fully readable **until** retention elapses; archive does not block download, deletion does.

---

## Storage adapter (implementation)

| Backend | `storage_key` example |
|---------|----------------------|
| Local | `uploads/a1b2c3d4.pdf` |
| S3 | `resumes/a1b2c3d4.pdf` |

Same interface: `save(bytes) → storage_key`, `open(key) → stream`.

---

## Actions

> **Agent rule:** List every route/service this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist).

### Assigned API routes (agent checklist)

**Implement in:** `api/src/api/leads_resume.py` (L5 mount), `api/src/services/storage.py`, `api/src/models/resume_file.py`

| ID | Type | Method | Path | Permission |
|----|------|--------|------|------------|
| L5 | HTTP | GET | `/api/v1/leads/{lead_id}/resume` | `read_leads` |
| S2 | Service | `validate_resume_upload`, `save_resume`, `open_stream`, `delete_orphan`, `purge_expired_resumes` | — | L1 save, L5 download, F2.5 job |

**Write path:** no standalone upload — `save_resume` called from L1 only.

### HTTP

#### L5 · `GET /api/v1/leads/{lead_id}/resume` — Download resume

**Permission:** `read_leads`

**Response `200`:** Binary stream

| Header | Value |
|--------|-------|
| `Content-Type` | From `resume_files.mime_type` |
| `Content-Disposition` | `attachment; filename="{original_filename}"` |

**Errors:** 404 if lead or file missing.

Never expose `storage_key` in JSON.

---

### Service — `StorageService`

```python
# api/src/services/storage.py

ALLOWED_MIME_TYPES = {"application/pdf", "application/msword", ...}
MAX_BYTES = 10 * 1024 * 1024

def validate_resume_upload(file: UploadFile) -> None:
    """Raise 400 if type/size invalid."""

def save_resume(db: Session, file: UploadFile) -> ResumeFile:
    """Write bytes to uploads_dir; insert resume_files row; return ORM."""

def open_stream(resume_file: ResumeFile) -> Iterator[bytes]:
    """Read from storage_key for StreamingResponse."""

def delete_orphan(storage_key: str) -> None:
    """Best-effort cleanup if DB transaction rolls back after save."""

def purge_expired_resumes(db: Session, *, now: datetime, retention_days: int) -> int:
    """F2.5 — delete storage + DB rows for leads past retention; return count purged."""
```

**Called by:** L1 (save), L5 (stream). No standalone upload endpoint.

---

## Proposed additions (pending approval)

| ID | Action | Notes |
|----|--------|-------|
| **RF1** | `GET /api/v1/resume-files/{file_id}` — metadata only | Returns `ResumeFileRead` (no binary). Permission: `read_leads`. |
| **RF2** | `GET /api/v1/resume-files/{file_id}/download` — direct download by file id | Alternative to L5 when UI has file id only. |
| **RF3** | `HEAD /api/v1/leads/{lead_id}/resume` — check existence / size | For UI without downloading full file. |
| **RF4** | `POST /api/v1/leads/{lead_id}/resume/replace` — upload new CV | Internal; rare. Requires new lead revision policy. |
| **RF5** | `GET /api/v1/resume-files/{file_id}/preview` — text extract preview | Plain-text snippet for LLM / UI; no full download. |

---
- [ ] SQLAlchemy model
- [ ] Storage service (local filesystem v1) — S2
- [ ] Upload validation in lead create (L1)
- [ ] Download endpoint L5 with content-disposition
