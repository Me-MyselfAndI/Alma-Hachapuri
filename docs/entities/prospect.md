# Prospect

External person who may submit one or more leads over time. Identity anchor for communication.

---

## Purpose

- Deduplicate by email across submissions (A2: 1 prospect → N leads)
- Hold durable contact identity separate from a single intake event

---

## Table: `prospects`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `email` | VARCHAR(255) | yes | **Unique** — match key on submit |
| `first_name` | VARCHAR(100) | yes | Updated on re-submit if changed? (TBD: last-write-wins) |
| `last_name` | VARCHAR(100) | yes | Same |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `leads` | Lead | 1 prospect → N leads |

---

## Business rules

| Rule | Detail |
|------|--------|
| Create on first submit | `POST /leads` with new email → insert prospect |
| Re-submit same email | Find existing prospect; create **new** lead linked to same prospect |
| No auth | Prospects never log in (A11) |

---

## API touchpoints

| Endpoint | Action |
|----------|--------|
| `POST /leads` | Find-or-create prospect by email (internal to lead create) |
| `GET /prospects/{id}` | Internal — prospect profile + linked leads (optional v1) |

---

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Unique index on `email`
- [ ] `find_or_create_prospect(email, first_name, last_name)` service
- [ ] Pydantic schemas: `ProspectRead`, embedded in `LeadRead`
