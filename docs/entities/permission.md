# Permission (code constants — not a DB table)

> **Status: simplified — 2026-06-27.** Permission keys live in `src/core/permissions.py`; no `permissions` table.

---

## Purpose

- Define capability **keys** checked by `require_permission("key")`
- Map keys → roles via `ROLE_PERMISSIONS` dict (replaces `role_permissions` join)

Exact matrix finalized here (F6.2 closed for v1).

---

## Permission keys

| `key` | Meaning |
|-------|---------|
| `read_leads` | View lead list and detail |
| `write_lead` | Update lead fields / state |
| `assign_lead` | Change `assigned_account_id` |
| `read_prospect` | View prospect and linked leads |
| `manage_users` | Create/disable accounts |
| `send_email` | Staff-initiated email to prospect (E2) |
| `read_emails` | View email notification audit log |
| `export_leads` | CSV export (L13) |

Assignment-scoped `write_lead`: attorneys may only PATCH leads where `assigned_account_id` = their account id — enforced in `LeadService`, not a separate key.

---

## Role → permission matrix (v1)

| Role | Permissions |
|------|-------------|
| `admin` | all keys |
| `attorney` | `read_leads`, `write_lead`, `read_emails`, `export_leads` |
| `intake_coordinator` | `read_leads`, `write_lead`, `assign_lead`, `read_prospect`, `send_email`, `read_emails`, `export_leads` |
| `readonly` | `read_leads`, `read_prospect`, `read_emails` |

---

## Authorization helpers

```python
# api/src/core/permissions.py

def permissions_for_role(role: Role) -> set[str]:
    return ROLE_PERMISSIONS[role]

def account_has_permission(account: Account, key: str) -> bool:
    return key in permissions_for_role(account.role)

# api/src/core/deps.py
def require_permission(key: str):
    """FastAPI dependency; 403 if missing."""
```

JWT embeds `permissions[]` at login (from matrix above).

---

## Actions

> **Agent rule:** No HTTP routes. Implement code consumed by all protected routes.

### Assigned API routes (agent checklist)

**Implement in:** `api/src/core/permissions.py`, `api/src/core/deps.py` (`require_permission`)

| ID | Type | Deliverable |
|----|------|-------------|
| — | Code | Permission key constants (table below) |
| — | Code | `ROLE_PERMISSIONS` dict |
| — | Code | `permissions_for_role`, `account_has_permission` |
| — | Code | `require_permission(key)` FastAPI dependency |

**Routes that use this package (reference only):**

| Permission | Used by |
|------------|---------|
| `read_leads` | L2, L3, L5, L7 |
| `write_lead` | L4, L10, L14 |
| `assign_lead` | L4 (assignee field) |
| `read_prospect` | P1, P2 |
| `manage_users` | A3–A6 |
| `send_email` | E2, E3 |
| `read_emails` | L6, E1, E4, E6 |
| `export_leads` | L13 |

---

## Proposed additions (still pending)

| ID | Notes |
|----|-------|
| PER3 | Custom permission keys for plugins — defer |

---

## Implementation checklist

- [ ] `src/core/permissions.py` with keys + `ROLE_PERMISSIONS`
- [ ] `require_permission` dependency
- [ ] JWT claims include permissions at login
