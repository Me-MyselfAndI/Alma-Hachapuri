# Lead

Intake submission — core entity. Holds form data, workflow state, assignment, and optional enrichment.

---

## Purpose

- Persist each prospect form submission
- Track state (`PENDING` → `REACHED_OUT` minimum; full lifecycle F2.1)
- Link to prospect, resume, assigned attorney

---

## Table: `leads`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `prospect_id` | UUID | FK → `prospects.id` | |
| `first_name` | VARCHAR(100) | yes | Denormalized from form at submit time |
| `last_name` | VARCHAR(100) | yes | |
| `email` | VARCHAR(255) | yes | Denormalized — snapshot at submit |
| `resume_file_id` | UUID | FK → `resume_files.id` | |
| `state` | VARCHAR(50) | yes | Default `PENDING`. Enum TBD (F2.1) |
| `source` | VARCHAR(100) | no | Optional attribution (A7) |
| `custom_fields` | JSONB | no | LLM-extracted; null until enriched (F7.1) |
| `assigned_attorney_id` | UUID | FK → `attorneys.id` | Set on create (F6.1) |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

---

## State (minimum from brief)

| State | Meaning |
|-------|---------|
| `PENDING` | Initial — awaiting attorney outreach |
| `REACHED_OUT` | Attorney contacted prospect |

Additional states → F2.1.

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `prospect` | Prospect | N leads → 1 prospect |
| `resume_file` | Resume file | 1 lead → 1 file (v1) |
| `assigned_attorney` | Attorney | N leads → 1 attorney |
| `state_history` | Lead state history | 1 lead → N history rows |
| `email_notifications` | Email notification | 1 lead → N emails |

---

## Business rules

| Rule | Detail |
|------|--------|
| Public create | No auth; validate required fields + resume file |
| State update | Internal only; attorney/admin per F6.2 |
| On create | Find-or-create prospect; store file; auto-assign attorney; send emails; optionally queue LLM job |
| Denormalized names/email | Snapshot at submit — prospect update does not retro-edit old leads |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `POST /leads` | Public | Create lead (+ prospect, file, emails) |
| `GET /leads` | Internal | List with filters (state, assignee) |
| `GET /leads/{id}` | Internal | Detail incl. prospect, resume URL, custom_fields |
| `PATCH /leads/{id}` | Internal | Update state, assignment, notes (TBD) |

---

## Pydantic schemas (proposed)

| Schema | Use |
|--------|-----|
| `LeadCreate` | Public multipart form |
| `LeadRead` | API response |
| `LeadUpdate` | Internal PATCH (state, assigned_attorney_id) |
| `LeadListItem` | Dashboard row |

---

## Implementation checklist

- [ ] SQLAlchemy model + enums for state
- [ ] Alembic migration
- [ ] `POST /leads` multipart handler
- [ ] `GET` / `PATCH` internal routes
- [ ] Assignment service hook (F6.1)
- [ ] State history writer on PATCH (F2.1)
