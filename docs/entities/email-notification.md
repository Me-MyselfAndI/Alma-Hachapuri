# Email notification

Audit log for outbound transactional email tied to a lead.

---

## Purpose

- Record what was sent, to whom, and whether it succeeded
- Debug failed sends; support retries (v1: log only, manual retry optional)

---

## Table: `email_notifications`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `lead_id` | UUID | FK → `leads.id` | |
| `conversation_id` | UUID | yes | Groups emails in one thread (see below) |
| `recipient` | VARCHAR(255) | yes | To address |
| `template` | VARCHAR(100) | yes | e.g. `prospect_confirmation`, `attorney_new_lead` |
| `subject` | VARCHAR(500) | yes | Rendered subject |
| `status` | VARCHAR(50) | yes | `pending`, `sent`, `failed` |
| `error_message` | TEXT | no | If failed |
| `provider_message_id` | VARCHAR(255) | no | SES/Resend id |
| `sent_at` | TIMESTAMPTZ | no | When provider accepted |
| `created_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `lead` | Lead | N notifications → 1 lead |

**Conversation threading:** All rows with the same `conversation_id` belong to one email thread (e.g. prospect follow-ups on a lead). Index `(conversation_id, created_at)` for timeline queries.

---

## Conversation ID rules

| Rule | Detail |
|------|--------|
| Scope | One conversation = one `lead_id` + one `recipient` thread |
| On first send | If no active thread exists for `(lead_id, recipient)`, generate new `conversation_id` |
| On continue | Reuse existing `conversation_id` for same `(lead_id, recipient)` |
| S7 on create | `prospect_confirmation` → new conversation with prospect email; `attorney_new_lead` → separate conversation with staff recipient |
| E2 staff send | Optional body field `conversation_id` to reply in a specific thread; if omitted, resolve via `(lead_id, recipient)` find-or-create |
| SMTP | Set `In-Reply-To` / `References` from prior message in same conversation when provider supports it (v1: store id; headers best-effort) |

**Query:** L6 and E4 accept optional `?conversation_id=` filter. List endpoints return `conversation_id` on every row.

---

## Templates (config/code, not DB)

| Template key | Trigger | Recipient |
|--------------|---------|-----------|
| `email_verification` | **RequestLeadVerification** (Flow A1) | Prospect email (pending intake) |
| `prospect_confirmation` | **VerifyEmailAndCreateLead** (Flow A2 / S7) | Prospect email |
| `attorney_new_lead` | **VerifyEmailAndCreateLead** (Flow A2 / S7) | Assigned account `work_email` or `email` (F3.1) |

---

## Three send paths (important)

| Path | ID | Trigger | Who initiates | Templates |
|------|-----|---------|---------------|-----------|
| **Verification (pre-lead)** | **S7a** | **RequestLeadVerification** (L1a / Flow A1) | System | `email_verification` |
| **Automatic (post-verify)** | **S7** | **VerifyEmailAndCreateLead** (L1b / Flow A2) succeeds | System | `prospect_confirmation`, `attorney_new_lead` |
| **Staff-initiated** | **E2** | Attorney/coordinator from internal UI | Logged-in staff | Any allowed template (e.g. follow-up) |

**SendVerificationEmail** (S7a) runs during L1a — **no lead row yet**. If verification email fails, pending intake is rolled back (unlike S7).

**SendLeadCreatedEmails** (S7) runs **only after** email verification and lead create (L1b) — not on form submit. Called inside `LeadService.verify_and_create_lead` / `create_lead` orchestration.

E2 is **not** a duplicate of S7 — it is for **later** emails (follow-up, resend custom message) after the lead exists.

---

## Business rules

| Rule | Detail |
|------|--------|
| On verify + create (L1b) | S7 inserts 2 rows (prospect + staff); send async or sync TBD |
| On verification request (L1a) | S7a sends one row (no `lead_id` FK until verified — store on pending or omit FK v1 TBD); **must succeed** or L1a rolls back |
| S7 failure after lead saved | Lead create still succeeds if notification emails fail (log `failed`) |
| S7a failure | Pending intake + temp file rolled back; prospect sees error |
| No PII in logs | Do not log resume body (A17) |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `GET /leads/{id}/emails` | Internal | List notifications for lead (optional v1) |

---

## Preconditions

Readable operation names for data/state rules (F2.3). Route IDs (L6, E3, S7, …) stay in the [Assigned API routes](#assigned-api-routes-agent-checklist) checklist. Permission checks are documented here but **out of scope** for F2.6 precondition unit tests.

| Operation | Who can call | What must be true | If not |
|-----------|--------------|-------------------|--------|
| **SendVerificationEmail** *(Flow A1)* | Internal — called from **RequestLeadVerification** | Pending intake row + temp resume saved. Recipient email **lowercase normalized (D7)**. Template `email_verification` with single-use token link. SMTP **must succeed** — on failure, rollback pending row + temp file; **no lead row**. Distinct from **SendLeadCreatedEmails** (S7). | **502/503** to prospect; pending rolled back |
| **SendLeadCreatedEmails** *(Flow A2 / S7)* | Internal — called from **VerifyEmailAndCreateLead** only | Lead row exists (verification succeeded). Assigned account resolved. Sends `prospect_confirmation` + `attorney_new_lead`; **separate `conversation_id` per recipient** (prospect vs staff). Failures logged; **lead create still succeeds**. | Lead remains; rows marked `failed` |
| **ListLeadEmails** | Internal (`read_emails`) | Lead exists. **D3:** archived lead OK — archive does not block. **D1:** any holder of `read_emails` may list emails for **any** lead (not assignee-scoped). Optional `?conversation_id=` filter. | **404** — lead not found |
| **GetEmailNotification** | Internal (`read_emails`) | Notification row exists. Parent lead exists. **D3:** archived lead OK. **D1:** read scope = all leads. | **404** |
| **SendStaffEmail** | Internal (`send_email`) | Lead exists. Template allowed. Recipient valid (body or template default). **D3:** archived lead OK. Resolve conversation: use provided `conversation_id` or find-or-create for `(lead_id, recipient)`. | **404** / **422** |
| **RetryFailedEmail** | Internal (`send_email`) | Row exists. **`status=failed` only** — reject retry when `pending` or `sent`. Re-render from stored template; reuse same `conversation_id`; SMTP retry. | **404**; **409** or **400** if not `failed` |
| **ListAllEmails** | Internal (`read_emails` or `manage_users`) | Valid pagination/filter params. **D1:** global list not assignee-scoped. | **422** |
| **ListEmailTemplates** | Internal (`send_email` or `read_emails`) | — | — |

**Conversation threading (all send paths):** One thread = one `(lead_id, recipient)` pair. First message generates `conversation_id`; later messages reuse it. Explicit `conversation_id` on **SendStaffEmail** overrides find-or-create.

Implementation helpers: `api/src/domains/email/preconditions.py` (tested by `api/tst/domains/email/test_email_preconditions.py`).

---

## Actions

> **Agent rule:** List every route/service this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist).

### Assigned API routes (agent checklist)

**Implement in:** `api/src/domains/email/router.py`, `api/src/domains/email/service.py`, `api/src/domains/email/preconditions.py`, `api/src/domains/email/models.py`

| ID | Operation | Type | Method | Path | Permission |
|----|-----------|------|--------|------|------------|
| L6 | **ListLeadEmails** | HTTP | GET | `/api/v1/leads/{lead_id}/emails` | `read_emails` |
| E1 | **GetEmailNotification** | HTTP | GET | `/api/v1/emails/{email_id}` | `read_emails` |
| E2 | **SendStaffEmail** | HTTP | POST | `/api/v1/leads/{lead_id}/emails` | `send_email` |
| E3 | **RetryFailedEmail** | HTTP | POST | `/api/v1/emails/{email_id}/retry` | `send_email` |
| E4 | **ListAllEmails** | HTTP | GET | `/api/v1/emails` | `read_emails` |
| E6 | **ListEmailTemplates** | HTTP | GET | `/api/v1/emails/templates` | `send_email` or `read_emails` |
| S7a | **SendVerificationEmail** | Service | — | — | called by L1a |
| S7 | **SendLeadCreatedEmails** | Service | `EmailService.send_lead_created_notifications` | — | called by L1b |

**Deferred:** E5 preview, E7 ad hoc follow-up.

**Consumed by:** [lead.md](lead.md) L1a → S7a; L1b → S7.

### HTTP

#### L6 · `GET /api/v1/leads/{lead_id}/emails` — List notifications for lead

**Permission:** `read_emails`

**Query:** `conversation_id` (optional — filter to one thread)

**Response `200` — `list[EmailNotificationRead]`:**

```json
[
  {
    "id": "uuid",
    "lead_id": "uuid",
    "conversation_id": "uuid",
    "recipient": "jane@example.com",
    "template": "prospect_confirmation",
    "subject": "We received your submission",
    "status": "sent",
    "error_message": null,
    "sent_at": "2026-06-27T21:00:01Z",
    "created_at": "2026-06-27T21:00:00Z"
  }
]
```

---

### Service — `EmailService`

```python
# api/src/domains/email/service.py

def send_verification_email(
    db: Session,
    *,
    pending_intake_id: UUID,
    email: str,
    token: str,
) -> EmailNotification:
    """S7a / Flow A1 — email_verification template.
    Must succeed or caller rolls back pending intake. No lead row yet."""

def send_lead_created_notifications(db: Session, *, lead: Lead) -> list[EmailNotification]:
    """S7 / Flow A2 — prospect_confirmation + attorney_new_lead.
    Called only after VerifyEmailAndCreateLead. Insert rows as pending;
    update to sent/failed after SMTP attempt.
    Never raises — logs failures; lead create must succeed."""

def send_template(
    db: Session,
    *,
    lead_id: UUID,
    template: str,
    recipient: str,
    context: dict,
    conversation_id: UUID | None = None,
) -> EmailNotification:
    """Render template, send via SMTP adapter, update status.
    Resolves conversation_id: use provided, else find-or-create for (lead_id, recipient)."""

def resolve_conversation_id(
    db: Session, *, lead_id: UUID, recipient: str, conversation_id: UUID | None = None
) -> UUID:
    """Return existing thread id or create new UUID for first message in thread."""

def list_by_conversation(db: Session, conversation_id: UUID) -> list[EmailNotification]:
    """Ordered by created_at asc — prior emails in thread."""

def render_template(template: str, context: dict) -> tuple[str, str]:
    """Returns (subject, html_body)."""
```

**SMTP adapter:** `smtplib` → `settings.smtp_host:settings.smtp_port` (Mailpit local).

**Templates (code, not DB):**

| Key | Recipient | Context vars |
|-----|-----------|--------------|
| `email_verification` | Pending intake email | `first_name`, `verify_url`, `expires_at` |
| `prospect_confirmation` | Lead email | `first_name`, `lead_id` |
| `attorney_new_lead` | Assigned account `work_email` | `prospect_name`, `lead_id`, `lead_url` |

**Called by:** L1a → **S7a** (verification); L1b → **S7** (post-verify notifications).

---

### HTTP — staff-initiated send

#### E1 · `GET /api/v1/emails/{email_id}` — Get notification by id

**Permission:** `read_emails`

**Response `200` — `EmailNotificationRead`**

---

#### E2 · `POST /api/v1/leads/{lead_id}/emails` — Staff send email

**Permission:** `send_email`

**Not** the same as S7. Use when staff manually sends follow-up or chooses a template after intake.

**Body — `EmailSendRequest`:**

```json
{
  "template": "prospect_follow_up",
  "recipient": "jane@example.com",
  "conversation_id": "uuid"
}
```

`recipient` optional — defaults from template rules (usually lead email).  
`conversation_id` optional — continue existing thread; omit to find-or-create by `(lead_id, recipient)`.

**Response `201` — `EmailNotificationRead`**

**Side effects:** Resolve conversation → insert row → render → SMTP send → update status.

---

#### E3 · **RetryFailedEmail** · `POST /api/v1/emails/{email_id}/retry` — Retry failed send

**Permission:** `send_email`

**Precondition:** Original row `status=failed` only (see [Preconditions](#preconditions)). **Not allowed** for template `email_verification` — verification emails are sent only from the public submission form; if delivery failed, the applicant must submit again (**409**).

**Response `200` — `EmailNotificationRead`** (same row updated, or new attempt row — implementer choice; prefer update in place v1).

**Side effects:** Re-render from stored template/context; reuse same `conversation_id`; SMTP retry. Does not apply to pre-lead verification emails.

---

#### E4 · `GET /api/v1/emails` — List all notifications

**Permission:** `read_emails` (admin/intake) or `manage_users`

**Query:** `status`, `template`, `conversation_id`, `lead_id`, `page`, `page_size`

**Response `200` — `Paginated[EmailNotificationRead]`**

---

#### E6 · `GET /api/v1/emails/templates` — List available templates

**Permission:** `send_email` or `read_emails`

**Response `200` — `list[EmailTemplateInfo]`:**

```json
[
  {
    "key": "prospect_confirmation",
    "description": "Acknowledge lead submission",
    "default_recipient": "prospect"
  },
  {
    "key": "prospect_follow_up",
    "description": "Staff follow-up to prospect",
    "default_recipient": "prospect"
  }
]
```

---

## Deferred (not v1)

| ID | Action | Reason |
|----|--------|--------|
| E5 | Preview render without send | Not needed yet |
| E7 | Ad hoc follow-up body | Not needed yet — use E2 + templates |

**Approved:** E1, E2, E3, E4, E6. **Automatic send:** S7a (L1a) + S7 (L1b only).

---
## Implementation checklist

- [ ] SQLAlchemy model incl. `conversation_id` + index
- [ ] `preconditions.py` — E3 retry gate, conversation resolution helpers
- [ ] `resolve_conversation_id` helper
- [ ] Email service adapter (Mailpit local / Resend) — S7a + S7
- [ ] Template renderer (Jinja2 or simple strings) incl. `email_verification`
- [ ] Hook in `LeadService.request_verification` (S7a) and `verify_and_create_lead` (S7)
- [ ] Route L6 (optional but planned)
- [ ] Status update after send attempt
