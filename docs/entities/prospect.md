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

## Preconditions

Guardrails that must hold **before** each operation succeeds. Permission checks (`read_prospect`, etc.) are separate — see [permission.md](permission.md). Readable operation names match [ARCHITECTURE.md](../ARCHITECTURE.md) and [API_CATALOG.md](API_CATALOG.md).

| Operation | Route ID | Must hold |
|-----------|----------|-----------|
| **FindOrCreateProspectByEmail** | S1 | Internal — called from **VerifyEmailAndCreateLead** (L1b). Email **normalized lowercase + trim (D7)** before unique lookup. No matching row → insert prospect with normalized email and submitted names; **`created=true`**. Matching row → **`created=false`**; update `first_name` / `last_name` **last-write-wins**; new lead links to existing prospect id (A2). |
| **GetProspect** | P1 | Valid JWT. Caller has `read_prospect`. Path `prospect_id` valid UUID; prospect row exists → **404 only when missing**. Response includes `lead_count`. **D9 — in v1** (internal read route, not optional). |
| **ListProspectLeads** | P2 | Valid JWT. `read_prospect`. Parent prospect exists (same 404 rule as GetProspect). Returns all linked leads ordered `created_at desc`; **no pagination v1**. **D3:** archived leads (`archived_at` set) **remain included** — archive does not hide rows from this list. **D9 — in v1**. |

Implementation helpers: `api/src/domains/prospect/preconditions.py` (tested by `api/tst/domains/prospect/test_prospect_preconditions.py`).

---

## Actions

> **Agent rule:** List every route/service this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist).

### Assigned API routes (agent checklist)

**Implement in:** `api/src/domains/prospect/router.py`, `api/src/domains/prospect/service.py`, `api/src/domains/prospect/preconditions.py`, `api/src/domains/prospect/models.py`

| ID | Operation | Type | Method | Path | Permission |
|----|-----------|------|--------|------|------------|
| P1 | **GetProspect** | HTTP | GET | `/api/v1/prospects/{prospect_id}` | `read_prospect` |
| P2 | **ListProspectLeads** | HTTP | GET | `/api/v1/prospects/{prospect_id}/leads` | `read_prospect` |
| S1 | **FindOrCreateProspectByEmail** (`find_or_create_by_email`) | Service | — | — | L1b |
| S1 | `get_prospect`, `list_leads_for_prospect` | Service | — | — | P1, P2 |

**No public routes.** S1 required for L1 orchestration.

### HTTP

#### P1 · `GET /api/v1/prospects/{prospect_id}`

**Permission:** `read_prospect`

**Response `200` — `ProspectRead`:**

```json
{
  "id": "uuid",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "lead_count": 2,
  "created_at": "2026-06-27T21:00:00Z",
  "updated_at": "2026-06-27T21:00:00Z"
}
```

---

#### P2 · `GET /api/v1/prospects/{prospect_id}/leads`

**Permission:** `read_prospect`

**Response `200` — `list[LeadListItem]`** (same shape as L2 items, no pagination v1).

---

### Service — `ProspectService`

```python
# api/src/services/prospect.py

def find_or_create_by_email(
    db: Session,
    *,
    email: str,
    first_name: str,
    last_name: str,
) -> tuple[Prospect, bool]:
    """Returns (prospect, created). On match: update first/last name last-write-wins."""

def get_prospect(db: Session, prospect_id: UUID) -> Prospect | None:
    """With lead count."""

def list_leads_for_prospect(db: Session, prospect_id: UUID) -> list[Lead]:
    """Ordered by created_at desc."""
```

**Called by:** L1 (`LeadService.create_lead`) — **S1**. No public prospect routes.

---

## Proposed additions (pending approval)

| ID | Action | Notes |
|----|--------|-------|
| **P3** | `GET /api/v1/prospects` — search/list prospects | Query: `email`, `q`, `page`. Permission: `read_prospect`. |
| **P4** | `PATCH /api/v1/prospects/{prospect_id}` — update contact info | Manual correction by staff; does not retro-edit lead snapshots. |
| **P5** | `GET /api/v1/prospects/by-email/{email}` — lookup by email | For intake desk: "has this person submitted before?" |
| **P6** | `GET /api/v1/prospects/{prospect_id}/timeline` — cross-lead activity | All leads + emails for this person. |
| **P7** | `POST /api/v1/prospects/merge` — merge duplicate prospects | Admin-only; re-link leads. Out of scope unless needed. |

---
- [ ] SQLAlchemy model
- [ ] Unique index on `email`
- [ ] `preconditions.py` rules (D7 email, find-or-create, D3 list)
- [ ] `find_or_create_by_email(...)` service (S1)
- [ ] Pydantic schemas: `ProspectRead`, `ProspectSummary` (embedded in `LeadRead`)
