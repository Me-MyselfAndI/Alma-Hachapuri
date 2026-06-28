# Lead state history

Append-only audit of lead state changes.

---

## Purpose

- Record who changed state, when, and from → to
- Support internal UI accountability

---

## Table: `lead_state_history`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `lead_id` | UUID | FK → `leads.id` | |
| `from_state` | VARCHAR(50) | no | Null on initial create |
| `to_state` | VARCHAR(50) | yes | |
| `changed_by_account_id` | UUID | FK → `accounts.id` | Who triggered change |
| `note` | TEXT | no | Optional reason (L10 transition note) |
| `created_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `lead` | Lead | N history → 1 lead |
| `changed_by` | Account | N history → 1 account |

---

## Business rules

| Rule | Detail |
|------|--------|
| On lead create | Insert row: `from_state=null`, `to_state=PENDING` |
| On PATCH state | Insert row with previous and new state |
| Immutable | No updates or deletes |
| States | Valid values follow F2.1 lifecycle |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| Embedded in `GET /leads/{id}` | Internal | Return history array (optional v1) |

---

## Preconditions

Readable operation names for data/state rules (F2.3). Route IDs (L7, S6, …) appear only in [Assigned API routes](#assigned-api-routes-agent-checklist). Permission checks are documented here but **out of scope** for F2.6 precondition unit tests.

| Operation | Who | Data / state rules | On failure |
|-----------|-----|-------------------|------------|
| **GetLeadStateHistory** | Internal — any account with `read_leads` | Path `lead_id` must resolve to existing lead. **Archived leads allowed (D3)** — `archived_at` does not block read; **404** only when lead id missing. Results ordered by `created_at` ascending. | **404** — lead not found |
| **RecordInitialState** | Internal (service S6) — called from **VerifyEmailAndCreateLead** (L1b) | Parent lead row exists (same transaction). `from_state` must be **null**. `to_state` defaults to `PENDING`; must be a valid lifecycle state. `changed_by_account_id` must be **null** (system create). Append-only insert. | Service error rolls back lead txn |
| **RecordStateChange** | Internal (service S6) — called from **UpdateLead** (L4) / **TransitionLead** (L10) when state changes | Parent lead exists. `from_state` and `to_state` required; must differ. Both must be valid lifecycle states; transition must match [F2.1 matrix](lead.md#state-lifecycle). `changed_by_account_id` required (staff account that triggered change). Optional `note` stored on row. Append-only — no updates/deletes. **D3:** allowed for archived leads. | Service error / **400** at HTTP boundary when transition invalid |

**GetLeadStateHistory — archived leads (D3):** Do **not** reject when `leads.archived_at` is set. Archive is list-filter only; audit history remains fully readable.

Implementation helpers: `api/src/domains/state_history/preconditions.py` (tested by `api/tst/domains/state_history/test_state_history_preconditions.py`).

---

## Actions

> **Agent rule:** List every route/service this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist).

### Assigned API routes (agent checklist)

**Implement in:** `api/src/api/leads_state_history.py` (L7 mount), `api/src/services/state_history.py`, `api/src/models/lead_state_history.py`

| ID | Type | Method | Path | Permission |
|----|------|--------|------|------------|
| L7 | HTTP | GET | `/api/v1/leads/{lead_id}/state-history` | `read_leads` |
| S6 | Service | `record_initial`, `record_transition`, `list_for_lead` | — | L1, L4, L10 |

**Called by:** L1 (initial row), L4/L10 (transitions with optional `note`).

### HTTP

#### L7 · `GET /api/v1/leads/{lead_id}/state-history`

**Permission:** `read_leads`

**Response `200` — `list[LeadStateHistoryRead]`:**

```json
[
  {
    "id": "uuid",
    "lead_id": "uuid",
    "from_state": null,
    "to_state": "PENDING",
    "changed_by_account_id": null,
    "changed_by_email": null,
    "created_at": "2026-06-27T21:00:00Z"
  },
  {
    "id": "uuid",
    "lead_id": "uuid",
    "from_state": "PENDING",
    "to_state": "REACHED_OUT",
    "changed_by_account_id": "uuid",
    "changed_by_email": "attorney@firm.com",
    "note": "Left voicemail",
    "created_at": "2026-06-27T22:00:00Z"
  }
]
```

Also embeddable inline on L3 `LeadRead` as `state_history[]` (implementer choice — at least one path required).

---

### Service — `LeadStateHistoryService`

```python
# api/src/services/state_history.py

def record_initial(db: Session, *, lead_id: UUID, to_state: str = "PENDING") -> LeadStateHistory:
    """On lead create: from_state=null, changed_by_account_id=null."""

def record_transition(
    db: Session,
    *,
    lead_id: UUID,
    from_state: str,
    to_state: str,
    changed_by: Account,
    note: str | None = None,
) -> LeadStateHistory:
    """On PATCH when state changes. Immutable append."""

def list_for_lead(db: Session, lead_id: UUID) -> list[LeadStateHistory]:
    """Ordered by created_at asc."""
```

**Called by:** L1 (initial), L4 (transition) — **S6**.

---

## Proposed additions (pending approval)

| ID | Action | Notes |
|----|--------|-------|
| **H1** | `GET /api/v1/state-history/{history_id}` — single entry | Permission: `read_leads` + parent lead access. |
| **H2** | `GET /api/v1/leads/{lead_id}/state-history/latest` — most recent | Convenience for UI badge. |
| **H3** | `GET /api/v1/state-history` — global audit feed | Admin; filter by `changed_by_account_id`, date range. |
| **H4** | Add `note` column + capture on transition | Optional reason text on L10 transitions. |
| **H5** | `GET /api/v1/accounts/{account_id}/state-changes` — by actor | "What did this attorney change?" audit view. |

---
- [ ] SQLAlchemy model
- [ ] `record_initial` + `record_transition` (S6)
- [ ] Route L7 and/or embed in L3
