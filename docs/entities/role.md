# Role (code enum — not a DB table)

> **Status: simplified — 2026-06-27.** Roles are a **PostgreSQL enum / VARCHAR** on `accounts.role`, not a `roles` table.

---

## Purpose

- Model `admin`, `attorney`, `intake_coordinator`, `readonly` as an **immutable** field on account create
- Permissions computed from `ROLE_PERMISSIONS` in code — see [permission.md](permission.md)
- JWT includes `role` + `permissions[]` at login

This is simplified IAM:

```text
Account  ≈ IAM User
role     ≈ IAM Role (fixed set, stored on user)
permissions ≈ policy actions (code constant → set per role)
```

No `roles`, `permissions`, or `role_permissions` tables.

---

## Enum values

| `role` | Description |
|--------|-------------|
| `admin` | Full access; manage users |
| `attorney` | Handle assigned leads |
| `intake_coordinator` | Intake / outreach + assign |
| `readonly` | View only |

**Immutable:** set at `POST /accounts`; cannot PATCH. To change role, create a new account and deactivate the old one.

---

## Code location (implementation)

```python
# api/src/core/permissions.py

class Role(str, Enum):
    ADMIN = "admin"
    ATTORNEY = "attorney"
    INTAKE_COORDINATOR = "intake_coordinator"
    READONLY = "readonly"

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: { ... all keys ... },
    Role.ATTORNEY: {"read_leads", "write_lead", "read_emails", "export_leads"},
    ...
}
```

Embedded in **A2** `GET /auth/me` as `"role": "attorney"` string.

---

## Actions

> **Agent rule:** No HTTP routes. Co-implement with [permission.md](permission.md) in same file/module.

### Assigned API routes (agent checklist)

**Implement in:** `api/src/core/permissions.py` (shared with permission agent)

| ID | Type | Deliverable |
|----|------|-------------|
| — | Code | `Role` enum (`admin`, `attorney`, `intake_coordinator`, `readonly`) |
| — | Code | `accounts.role` column validation on create |
| — | JWT | `role` claim on A1 |

**No `/roles` HTTP endpoints.**

---

The earlier `roles` + `role_permissions` table design was **superseded** — see `AGENT_CORRECTIONS.md` #16.

---

## Related

- [account.md](account.md) — `accounts.role` column
- [permission.md](permission.md) — permission keys + matrix
