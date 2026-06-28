# Lead

Intake submission — core entity. Holds form data, workflow state, assignment, and optional enrichment.

---

## Purpose

- Persist each prospect form submission
- Track state (5-state lifecycle — F2.1 confirmed)
- Link to prospect, resume, assigned account (attorney-role)

---

## Table: `leads`


| Column                | Type         | Required               | Notes                                                                                                                            |
| --------------------- | ------------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `id`                  | UUID         | PK                     |                                                                                                                                  |
| `prospect_id`         | UUID         | FK → `prospects.id`    |                                                                                                                                  |
| `first_name`          | VARCHAR(100) | yes                    | Denormalized from form at submit time                                                                                            |
| `last_name`           | VARCHAR(100) | yes                    |                                                                                                                                  |
| `email`               | VARCHAR(255) | yes                    | Denormalized — snapshot at submit                                                                                                |
| `resume_file_id`      | UUID         | FK → `resume_files.id` |                                                                                                                                  |
| `state`               | VARCHAR(50)  | yes                    | Default `PENDING`. See lifecycle below                                                                                           |
| `state_changed_at`    | TIMESTAMPTZ  | yes                    | Set on create and on every state change; powers "how long waiting / going cold" (replaces the old `IN_CONTACT`/`ON_HOLD` states) |
| `source`              | VARCHAR(100) | no                     | Optional attribution (A7)                                                                                                        |
| `custom_fields`       | JSONB        | no                     | LLM-extracted; null until enriched (F7.1)                                                                                        |
| `assigned_account_id` | UUID         | FK → `accounts.id`     | Set on create (F6.1); assignee must have assignable role                                                                         |
| `archived_at`         | TIMESTAMPTZ  | no                     | Set by L14; null = active                                                                                                        |
| `created_at`          | TIMESTAMPTZ  | yes                    |                                                                                                                                  |
| `updated_at`          | TIMESTAMPTZ  | yes                    |                                                                                                                                  |


---

## State lifecycle (confirmed — F2.1, simplified 2026-06-27)

The lifecycle is a **whose-turn-is-it ping-pong** plus a fit decision. The old `IN_CONTACT` / `ON_HOLD` states were removed: they only differed by *how long* a lead had been waiting, which is now derived from `state_changed_at` (no separate status needed).


| State          | Meaning (whose turn)                                                                             | What triggers leaving it                                     |
| -------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| `PENDING`      | **Our turn** — new submission *or* the prospect just replied; we owe the next action (**brief**) | Staff contacts/responds → `REACHED_OUT`; or staff judges fit |
| `REACHED_OUT`  | **Their turn** — we contacted/responded; awaiting the prospect (**brief**)                       | Prospect replies → back to `PENDING`; or staff judges fit    |
| `QUALIFIED`    | Staff decided **good fit**; moving toward engagement                                             | Engagement concluded → `CLOSED`                              |
| `DISQUALIFIED` | Staff decided **not a fit** / declined / out of scope / went cold                                | Closed out → `CLOSED`                                        |
| `CLOSED`       | Terminal — resolved either way (won, lost, abandoned)                                            | —                                                            |


**Key ideas:**

- `PENDING` ⇄ `REACHED_OUT` flips every time the ball changes court. A prospect reply moves it **back to `PENDING`** (our turn again).
- **"How long have we waited / is this going cold?"** = `now − state_changed_at` — a timestamp, not a status. A long stay in `REACHED_OUT` is what used to be "on hold."
- **Qualify / disqualify is a human staff decision**, made at any point it is the lead's turn — not an automatic rule.

**Transition rules (v1):**

```text
PENDING → REACHED_OUT | QUALIFIED | DISQUALIFIED
REACHED_OUT → PENDING | QUALIFIED | DISQUALIFIED
QUALIFIED → CLOSED
DISQUALIFIED → CLOSED
CLOSED → (terminal)
```

Invalid transition → 400. Every change appends to `lead_state_history` and updates `state_changed_at`.

---

## Relationships


| Relation              | Target             | Cardinality                    |
| --------------------- | ------------------ | ------------------------------ |
| `prospect`            | Prospect           | N leads → 1 prospect           |
| `resume_file`         | Resume file        | 1 lead → 1 file (v1)           |
| `assigned_account`    | Account            | N leads → 1 account (assignee) |
| `state_history`       | Lead state history | 1 lead → N history rows        |
| `email_notifications` | Email notification | 1 lead → N emails              |


---

## Business rules


| Rule                     | Detail                                                                                                                                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Public intake (two-step) | **RequestLeadVerification** stores pending intake + temp resume and sends verification email — **no lead row yet**. **VerifyEmailAndCreateLead** (token from email link) runs full create orchestration. |
| Email normalization (D7) | Lowercase + trim on every write (`RequestLeadVerification`, prospect find-or-create, lead denormalized `email`)                                                                                          |
| State update             | Internal only; attorney/admin per F6.2                                                                                                                                                                   |
| On verify + create (L1b) | Find-or-create prospect; promote resume; auto-assign account; send emails (S7); optionally queue LLM job                                                                                                 |
| Denormalized names/email | Snapshot at verify time — prospect update does not retro-edit old leads                                                                                                                                  |
| Read scope (D1)          | Attorneys with `read_leads` see **all** leads/resumes in list and detail — not limited to assigned rows                                                                                                  |
| Archived access (D3)     | Archived leads remain readable by id (GetLead, DownloadResume, sub-routes); excluded from ListLeads unless `include_archived=true`                                                                       |


---

## Pending intake (pre-lead)

Until email is verified, form data lives outside `leads`.

### Table: `lead_intake_pending` *(proposed name — confirm at implementation)*


| Column                          | Type         | Required | Notes                                                         |
| ------------------------------- | ------------ | -------- | ------------------------------------------------------------- |
| `id`                            | UUID         | PK       |                                                               |
| `token_hash`                    | VARCHAR(255) | yes      | Hash of single-use verification token (never store raw token) |
| `email`                         | VARCHAR(255) | yes      | Lowercase normalized (D7)                                     |
| `first_name`                    | VARCHAR(100) | yes      |                                                               |
| `last_name`                     | VARCHAR(100) | yes      |                                                               |
| `source`                        | VARCHAR(100) | no       | Optional attribution (A7)                                     |
| `temp_resume_path`              | VARCHAR(500) | yes      | Pending file location until L1b promotes                      |
| `temp_resume_original_filename` | VARCHAR(255) | yes      |                                                               |
| `temp_resume_mime_type`         | VARCHAR(100) | yes      |                                                               |
| `temp_resume_size_bytes`        | BIGINT       | yes      |                                                               |
| `expires_at`                    | TIMESTAMPTZ  | yes      | Token TTL — **TBD** (see open questions; e.g. 24–72 h)        |
| `used_at`                       | TIMESTAMPTZ  | no       | Set when L1b **claim** starts (row lock); prevents concurrent double-create |
| `lead_id`                       | UUID         | FK       | Set when L1b completes; idempotent verify retries return this lead          |
| `created_at`                    | TIMESTAMPTZ  | yes      |                                                               |


**Cleanup:** Orphan pending rows + temp files after expiry (background job — out of scope v1 unless trivial).

---

## API touchpoints


| Operation                | Endpoint                                                       | Auth     | Action                                                |
| ------------------------ | -------------------------------------------------------------- | -------- | ----------------------------------------------------- |
| RequestLeadVerification  | `POST /leads/verification-requests`                            | Public   | Store pending intake; send verification email         |
| VerifyEmailAndCreateLead | `GET /leads/verify?token=` (link) · `POST /leads/verify` (SPA) | Public   | Consume token; create lead (+ prospect, file, emails) |
| ListLeads                | `GET /leads`                                                   | Internal | List with filters (state, assignee)                   |
| GetLead                  | `GET /leads/{id}`                                              | Internal | Detail incl. prospect, resume URL, custom_fields      |
| UpdateLead               | `PATCH /leads/{id}`                                            | Internal | Update state, assignment                              |


---

## Pydantic schemas (proposed)


| Schema                            | Use                                           |
| --------------------------------- | --------------------------------------------- |
| `LeadVerificationRequestForm`     | Public multipart — RequestLeadVerification    |
| `LeadVerificationRequestResponse` | 202 / check-your-email payload                |
| `LeadVerifyRequest`               | POST body with `token` (SPA path)             |
| `LeadCreateResponse`              | Public success after VerifyEmailAndCreateLead |
| `LeadRead`                        | API response                                  |
| `LeadUpdate`                      | Internal PATCH (state, assigned_account_id)   |
| `LeadListItem`                    | Dashboard row                                 |


---

## Preconditions

Guardrails that must hold **before** each operation succeeds. Permission checks (`read_leads`, `write_lead`, etc.) are separate — see [permission.md](permission.md). Readable operation names match [ARCHITECTURE.md](../ARCHITECTURE.md) Flow A/B.


| Operation                    | Route ID | Must hold                                                                                                                                                                                                                                                                                                |
| ---------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RequestLeadVerification**  | L1a      | No auth. Valid multipart: `first_name`, `last_name`, `email`, `resume` (PDF/DOC/DOCX, ≤10 MB). Email normalized lowercase (D7). Resume saved to temp storage. Pending row + token created. Verification email send **must succeed** — otherwise rollback pending + temp file; **no lead row**.           |
| **VerifyEmailAndCreateLead** | L1b      | No auth. Token present and matches pending row. Token **not expired** and **not already used**. Pending intake + temp resume exist. On success: single transaction for prospect (S1), resume promote (S2), assignee (S3), lead insert, history (S6), then S7 emails + optional S8. Mark token `used_at`. |
| **ListLeads**                | L2       | Valid JWT. Caller has `read_leads`. **D1:** attorneys see **all** leads — no assignee filter unless caller passes `assigned_account_id` or `mine=true`. Active leads only unless `include_archived=true`.                                                                                                |
| **GetLead**                  | L3       | Valid JWT. `read_leads`. Lead exists. **D3:** `archived_at` set does **not** block access — 404 only when id missing. **D1:** any attorney may read any lead.                                                                                                                                            |
| **UpdateLead**               | L4       | Valid JWT. `write_lead` (write scope still assigned-lead for attorneys per F6.2). Lead exists. Valid transition if `state` changes. `assign_lead` if reassigning. **D3:** archived leads remain addressable by id.                                                                                       |
| **DownloadResume**           | L5       | Valid JWT. `read_leads`. Lead + resume exist. **D3:** allowed for archived leads. **D1:** attorneys may download any lead's resume. Spec: [resume-file.md](resume-file.md).                                                                                                                              |
| **ListLeadEmails**           | L6       | Valid JWT. `read_emails`. Lead exists. **D3:** archived OK. Spec: [email-notification.md](email-notification.md).                                                                                                                                                                                        |
| **GetLeadStateHistory**      | L7       | Valid JWT. `read_leads`. Lead exists. **D3:** archived OK. Spec: [lead-state-history.md](lead-state-history.md).                                                                                                                                                                                         |
| **TransitionLead**           | L10      | Valid JWT. `write_lead`. Lead exists. `to_state` allowed by transition matrix. **D3:** archived leads still transition-capable (or document if blocked — v1: allow).                                                                                                                                     |
| **ExportLeads**              | L13      | Valid JWT. `export_leads`. Same filter semantics as ListLeads (D1, `include_archived`).                                                                                                                                                                                                                  |
| **ArchiveLead**              | L14      | Valid JWT. `write_lead`. Lead exists and not already archived (re-archive → idempotent 204 or 404 — pick at implement). Sets `archived_at`.                                                                                                                                                              |


**Prospect routes (D9 — in v1):** [prospect.md](prospect.md) P1/P2 require `read_prospect`; lead existence for nested lists follows same D3 rules.

Implementation helpers: `api/src/domains/lead/preconditions.py` (tested by `api/tst/domains/lead/test_lead_preconditions.py`).

---

## Actions

> **Agent rule:** List every route/service this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist).

### Assigned API routes (agent checklist)

**Implement in:** `api/src/domains/lead/router.py`, `api/src/domains/lead/service.py`, `api/src/domains/lead/preconditions.py`, enrichment (optional)


| ID  | Operation                            | Type    | Method | Path                                  | Permission       | Spec                                     |
| --- | ------------------------------------ | ------- | ------ | ------------------------------------- | ---------------- | ---------------------------------------- |
| L1a | **RequestLeadVerification**          | HTTP    | POST   | `/api/v1/leads/verification-requests` | public           | below                                    |
| L1b | **VerifyEmailAndCreateLead**         | HTTP    | GET    | `/api/v1/leads/verify`                | public           | below                                    |
| L1b | **VerifyEmailAndCreateLead**         | HTTP    | POST   | `/api/v1/leads/verify`                | public           | below (SPA)                              |
| L2  | **ListLeads**                        | HTTP    | GET    | `/api/v1/leads`                       | `read_leads`     | below                                    |
| L3  | **GetLead**                          | HTTP    | GET    | `/api/v1/leads/{lead_id}`             | `read_leads`     | below                                    |
| L4  | **UpdateLead**                       | HTTP    | PATCH  | `/api/v1/leads/{lead_id}`             | `write_lead`     | below                                    |
| L10 | **TransitionLead**                   | HTTP    | POST   | `/api/v1/leads/{lead_id}/transitions` | `write_lead`     | below                                    |
| L13 | **ExportLeads**                      | HTTP    | GET    | `/api/v1/leads/export`                | `export_leads`   | below                                    |
| L14 | **ArchiveLead**                      | HTTP    | DELETE | `/api/v1/leads/{lead_id}`             | `write_lead`     | below                                    |
| S4  | `LeadService.create_lead`            | Service | —      | —                                     | L1b orchestrator | below + [API_CATALOG.md](API_CATALOG.md) |
| S4a | `LeadService.request_verification`   | Service | —      | —                                     | L1a              | below                                    |
| S4b | `LeadService.verify_and_create_lead` | Service | —      | —                                     | L1b              | below                                    |
| S5  | `LeadService.update_lead`            | Service | —      | —                                     | L4               | below                                    |
| S8  | `schedule_lead_enrichment`           | Service | —      | —                                     | L1b (flag)       | below                                    |


**Mount sub-routers from other packages (do not reimplement):**


| ID  | Operation               | Owner doc                                      | Path                                    |
| --- | ----------------------- | ---------------------------------------------- | --------------------------------------- |
| L5  | **DownloadResume**      | [resume-file.md](resume-file.md)               | `/api/v1/leads/{lead_id}/resume`        |
| L6  | **ListLeadEmails**      | [email-notification.md](email-notification.md) | `/api/v1/leads/{lead_id}/emails`        |
| L7  | **GetLeadStateHistory** | [lead-state-history.md](lead-state-history.md) | `/api/v1/leads/{lead_id}/state-history` |


**Calls on L1b (import other services):** S1 [prospect.md](prospect.md), S2 [resume-file.md](resume-file.md), S3 [account.md](account.md), S6 [lead-state-history.md](lead-state-history.md), S7 [email-notification.md](email-notification.md).

**L1a calls:** temp storage write, verification email send (template `email_verification` — add to email doc), pending row insert.

> **ID note:** Old monolithic **L1** split into **L1a** (request) + **L1b** (verify + create). Do not expose `POST /api/v1/leads` as direct create.

### Lead route index (L1a–L14)


| ID  | Operation                | Method | Path                           | Defined in                                     | Purpose                         |
| --- | ------------------------ | ------ | ------------------------------ | ---------------------------------------------- | ------------------------------- |
| L1a | RequestLeadVerification  | POST   | `/leads/verification-requests` | below                                          | Public — pending intake + email |
| L1b | VerifyEmailAndCreateLead | GET    | `/leads/verify?token=`         | below                                          | Email link — create lead        |
| L1b | VerifyEmailAndCreateLead | POST   | `/leads/verify`                | below                                          | SPA — `{ "token": "..." }`      |
| L2  | ListLeads                | GET    | `/leads`                       | below                                          | List / filter                   |
| L3  | GetLead                  | GET    | `/leads/{id}`                  | below                                          | Detail                          |
| L4  | UpdateLead               | PATCH  | `/leads/{id}`                  | below                                          | Update assignee, etc.           |
| L5  | DownloadResume           | GET    | `/leads/{id}/resume`           | [resume-file.md](resume-file.md)               | Download CV                     |
| L6  | ListLeadEmails           | GET    | `/leads/{id}/emails`           | [email-notification.md](email-notification.md) | Email log for lead              |
| L7  | GetLeadStateHistory      | GET    | `/leads/{id}/state-history`    | [lead-state-history.md](lead-state-history.md) | State change audit              |
| L10 | TransitionLead           | POST   | `/leads/{id}/transitions`      | below                                          | State transition + note         |
| L13 | ExportLeads              | GET    | `/leads/export`                | below                                          | CSV export                      |
| L14 | ArchiveLead              | DELETE | `/leads/{id}`                  | below                                          | Archive (soft)                  |


> **Naming:** **L6/L7** = HTTP routes (sub-entities). **S6/S7** in orchestration = service calls on verify+create — different IDs.

### HTTP

#### L1a · **RequestLeadVerification** · `POST /api/v1/leads/verification-requests`

**Content-Type:** `multipart/form-data`


| Part         | Type                        | Required                    |
| ------------ | --------------------------- | --------------------------- |
| `first_name` | string                      | yes                         |
| `last_name`  | string                      | yes                         |
| `email`      | string (email)              | yes — stored lowercase (D7) |
| `source`     | string                      | no                          |
| `resume`     | file (PDF/DOC/DOCX, ≤10 MB) | yes                         |


**Response `202` — `LeadVerificationRequestResponse`:**

```json
{
  "message": "Check your email to confirm your submission.",
  "email": "jane@example.com"
}
```

`email` echoes normalized address (for UI display only).

**Errors:** 400 (file type/size); 422 (validation); 502/503 if verification email cannot be sent (pending row rolled back).

**Side effects:** Insert `lead_intake_pending`; save resume to **temp** storage; send verification email with link `{WEBAPP_URL}/verify?token={token}` (exact URL TBD). **No** prospect row, **no** lead row, **no** S7.

See [API_CATALOG.md](API_CATALOG.md#orchestration-lead-intake-l1a--l1b).

---

#### L1b · **VerifyEmailAndCreateLead** · `GET /api/v1/leads/verify` · `POST /api/v1/leads/verify`

**GET** — email link (browser): `?token={opaque_token}`

**POST** — SPA / JSON clients:

```json
{ "token": "opaque-token-from-email" }
```

**Response `201` — `LeadCreateResponse`:**

```json
{
  "id": "uuid",
  "state": "PENDING",
  "message": "Thank you for your submission."
}
```

**Errors:** 400 (`token` missing); 404 (unknown token); 410 (expired token); 409 (verification **in progress** — another request holds the claim); 422 (pending data invalid). **Idempotent retry:** if verify already completed (`lead_id` set), returns **201** with the same lead (no duplicate create).

**Side effects:** Load pending by token with row lock; claim row (`used_at`); run create orchestration (S1–S7, optional S8); set `lead_id` on pending; promote temp resume. Stale reclaim after `VERIFICATION_PROCESSING_STALE_MINUTES` (default 5) if claim stuck without `lead_id`. See [API_CATALOG.md](API_CATALOG.md#orchestration-lead-intake-l1a--l1b).

---

#### L2 · **ListLeads** · `GET /api/v1/leads` — List leads (internal)

**Permission:** `read_leads`

**Scope (D1):** Attorneys and other roles with `read_leads` receive **all** active leads — not restricted to `assigned_account_id = self`. Use `?mine=true` or `?assigned_account_id=` to narrow intentionally.

**Query — `LeadListParams`:**


| Param                 | Type            | Default                                                                                                           |
| --------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------- |
| `state`               | lead state enum | —                                                                                                                 |
| `assigned_account_id` | UUID            | —                                                                                                                 |
| `mine`                | bool            | false — if true, filter to `assigned_account_id` = current JWT account (convenience; same as passing your own id) |
| `include_archived`    | bool            | false                                                                                                             |
| `page`                | int             | 1                                                                                                                 |
| `page_size`           | int             | 20                                                                                                                |


**L8 not added:** `GET /leads/mine` would duplicate L2 — use `?mine=true` or `?assigned_account_id={your_id}`.

**Response `200` — `Paginated[LeadListItem]`:**

```json
{
  "items": [
    {
      "id": "uuid",
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "state": "PENDING",
      "source": null,
      "assigned_account_id": "uuid",
      "assigned_account_name": "John Smith",
      "created_at": "2026-06-27T21:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

#### L3 · **GetLead** · `GET /api/v1/leads/{lead_id}` — Lead detail (internal)

**Permission:** `read_leads`

**Archived (D3):** Returns `200` even when `archived_at` is set. Only unknown `lead_id` → 404.

**Response `200` — `LeadRead`:**

```json
{
  "id": "uuid",
  "prospect_id": "uuid",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "state": "PENDING",
  "source": null,
  "custom_fields": null,
  "assigned_account_id": "uuid",
  "assigned_account": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Smith",
    "work_email": "john@firm.com"
  },
  "resume": {
    "id": "uuid",
    "original_filename": "cv.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 12345,
    "download_url": "/api/v1/leads/{lead_id}/resume"
  },
  "prospect": {
    "id": "uuid",
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "archived_at": null,
  "created_at": "2026-06-27T21:00:00Z",
  "updated_at": "2026-06-27T21:00:00Z"
}
```

`custom_fields` populated asynchronously when F7.1 runs.

---

#### L4 · `PATCH /api/v1/leads/{lead_id}` — Update lead (internal)

**Permission:** `write_lead`; `assign_lead` required if `assigned_account_id` present.

**Body — `LeadUpdate` (all optional, ≥1 field):**

```json
{
  "state": "REACHED_OUT",
  "assigned_account_id": "uuid"
}
```

**Response `200` — `LeadRead`**

**Validation:** State transition rules — see lifecycle above. Invalid → 400.

**Side effects:** S6 `record_transition` when `state` changes.

**Note:** Prefer **L10** for state-only changes (optional transition note). Use L4 for assignment and other field updates.

---

#### L5 · `GET /api/v1/leads/{lead_id}/resume` — Download resume

**Full spec:** [resume-file.md](resume-file.md#L5). Permission: `read_leads`. Streams CV binary.

---

#### L6 · `GET /api/v1/leads/{lead_id}/emails` — List emails for this lead

**Full spec:** [email-notification.md](email-notification.md#L6). Permission: `read_emails`.

Returns all `email_notifications` for the lead (auto S7 sends + staff E2 sends). Optional `?conversation_id=` filter.

---

#### L7 · `GET /api/v1/leads/{lead_id}/state-history` — State change audit

**Full spec:** [lead-state-history.md](lead-state-history.md#L7). Permission: `read_leads`.

Returns append-only history: who changed state, when, from → to, optional `note` (from L10).

---

#### L10 · `POST /api/v1/leads/{lead_id}/transitions` — State transition

**Permission:** `write_lead`

**Body — `LeadTransitionRequest`:**

```json
{
  "to_state": "REACHED_OUT",
  "note": "Left voicemail, emailed follow-up"
}
```

`note` optional — stored on `lead_state_history.note` (not a separate lead notes field).

**Response `200` — `LeadRead`**

**Validation:** Transition matrix in lifecycle section. Invalid → 400.

**Side effects:** S6 `record_transition` with optional note.

---

#### L13 · `GET /api/v1/leads/export` — CSV export

**Permission:** `export_leads`

**Query:** Same filters as L2 (`state`, `assigned_account_id`, `mine`, `include_archived`).

**Response `200`:** `text/csv` stream; `Content-Disposition: attachment; filename="leads.csv"`.

Columns: id, names, email, state, source, assignee, created_at (minimum).

---

#### L14 · **ArchiveLead** · `DELETE /api/v1/leads/{lead_id}` — Archive lead

**Permission:** `write_lead` (admin may always; attorney scoped to assigned)

**Response `204`** No content.

**Behavior:** Soft-delete — set `archived_at=now()`. Excluded from L2 unless `include_archived=true`. **D3:** direct GET/L5/L6/L7 remain allowed after archive. Not purged from DB.

---

### Service — enrichment (F7.1, optional)

```python
# api/src/domains/lead/enrichment.py

def schedule_lead_enrichment(lead_id: UUID) -> None:
    """Queued via FastAPI BackgroundTasks after L1b response."""

def extract_custom_fields_dummy(*, lead_id: UUID) -> dict:
    """Placeholder LLM output until real resume extraction is wired."""
```

**Called by:** L1b verify routes when `settings.enable_llm_enrichment=true` — **S8** (background, non-blocking).

---

### Service — `LeadService`

```python
# api/src/domains/lead/service.py

def request_verification(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    resume: UploadFile,
    source: str | None = None,
) -> LeadVerificationRequestResponse:
    """L1a — pending row + temp file + verification email; no lead."""

def verify_and_create_lead(
    db: Session,
    *,
    token: str,
) -> Lead:
    """L1b — validate token; orchestrate S1–S7; return Lead ORM."""

def create_lead(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    resume_path: str,
    resume_metadata: ResumeMetadata,
    source: str | None = None,
) -> Lead:
    """Internal orchestrator after resume promoted (called by verify_and_create_lead)."""

def get_lead(db: Session, lead_id: UUID) -> Lead | None:
    """Eager-load prospect, resume_file, assigned_account."""

def list_leads(
    db: Session,
    *,
    params: LeadListParams,
) -> tuple[list[Lead], int]:
    """Returns (items, total_count)."""

def update_lead(
    db: Session,
    *,
    lead_id: UUID,
    update: LeadUpdate,
    actor: Account,
) -> Lead:
    """Applies PATCH; enforces transition + permission scope."""
```

---

## Deferred / out of scope


| ID      | Action                     | Decision                                                                 |
| ------- | -------------------------- | ------------------------------------------------------------------------ |
| **L8**  | `GET /leads/mine`          | **Rejected** — redundant with L2 `?mine=true` or `?assigned_account_id=` |
| **L9**  | `GET /leads/stats`         | **Out of scope** v1                                                      |
| **L11** | `GET /leads/{id}/timeline` | **Pending** — unified feed (see below)                                   |
| **L12** | `PATCH /leads/{id}/notes`  | **Pending** — no `internal_notes` column today (see below)               |


### What is L11?

Single endpoint returning a **merged activity feed** for one lead, sorted by time:


| Event type           | Source                               |
| -------------------- | ------------------------------------ |
| State change         | `lead_state_history`                 |
| Email sent/failed    | `email_notifications`                |
| Enrichment completed | `leads.custom_fields` updated (F7.1) |


Alternative v1: client calls L7 + L6 separately — L11 is UI sugar only. Approve if you want one round-trip for detail page.

### Internal notes (L12)

**Not tracked today.** We have:


| Mechanism                | What it stores                                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| **L10 `note`**           | Optional comment on a **state transition** → `lead_state_history.note`                                |
| **L12 `internal_notes`** | Would be a freeform scratchpad on the **lead row** (always visible on detail) — **not in schema yet** |


If you want a persistent lead-level notepad (not tied to a transition), say yes and we add `internal_notes TEXT` + L12.

**Approved:** L10, L13, L14.

---

## Implementation checklist

- SQLAlchemy model + enums for state + `archived_at`
- `lead_intake_pending` model + Alembic migration
- `preconditions.py` rules (state matrix, token, D3 list filter)
- `POST /api/v1/leads/verification-requests` (L1a)
- `GET` + `POST /api/v1/leads/verify` (L1b)
- `GET` / `PATCH` internal routes (L2–L4)
- L10 transitions, L13 export, L14 archive
- `LeadService.request_verification` + `verify_and_create_lead`
- Assignment service hook (F6.1) on L1b only
- State history writer on PATCH + L10 (F2.1)
- Verification email template + send path

