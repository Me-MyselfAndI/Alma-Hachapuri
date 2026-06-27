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

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Write helper called from lead create + state PATCH
- [ ] Include in lead detail response
