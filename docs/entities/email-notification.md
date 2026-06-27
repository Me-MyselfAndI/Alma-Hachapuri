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

---

## Templates (config/code, not DB)

| Template key | Trigger | Recipient |
|--------------|---------|-----------|
| `prospect_confirmation` | Lead created | Prospect email |
| `attorney_new_lead` | Lead created | Assigned attorney `work_email` (F3.1) |

---

## Business rules

| Rule | Detail |
|------|--------|
| On lead create | Insert 2 rows (prospect + attorney); send async or sync TBD |
| Failure | Lead create still succeeds if email fails (log `failed`) |
| No PII in logs | Do not log resume body (A17) |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `GET /leads/{id}/emails` | Internal | List notifications for lead (optional v1) |

---

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Email service adapter (Mailpit local / Resend)
- [ ] Template renderer (Jinja2 or simple strings)
- [ ] Hook in lead create service
- [ ] Status update after send attempt
