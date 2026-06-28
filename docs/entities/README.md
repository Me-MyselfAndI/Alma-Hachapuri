# Entity schemas

Design docs for each persisted domain entity — fields, relationships, constraints, and API touchpoints. Implementation lives in `api/src/domains/<entity>/` (see [api/README.md](../../api/README.md)).

**Status:** Entity schemas + API catalog in progress (F2.0). See [API_CATALOG.md](API_CATALOG.md).

---

## Entity index

| Entity | Table | Schema doc | API code |
|--------|-------|------------|--------------|
| [Prospect](prospect.md) | `prospects` | … | `api/src/domains/prospect/` |
| [Lead](lead.md) | `leads` | … | `api/src/domains/lead/` |
| [Resume file](resume-file.md) | `resume_files` | … | `api/src/domains/resume_file/` |
| [Account](account.md) | `accounts` | … | `api/src/domains/account/` |
| [Email notification](email-notification.md) | `email_notifications` | … | `api/src/domains/email/` |
| [Lead state history](lead-state-history.md) | `lead_state_history` | … | `api/src/domains/state_history/` |

**Code-only (no domain folder):** [Role](role.md), [Permission](permission.md) → `api/src/core/permissions.py`, `deps.py`

**Merged / redirect:** [Attorney](attorney.md) → account with `role=attorney`.

**Not separate tables:** feature flags (env), email templates (code).

### Agent doc contract

Every implementable entity doc **must** have:

1. **`## Assigned API routes (agent checklist)`** — every HTTP ID + service method owned by that package
2. **`## Actions`** — full specs for each checklist row
3. **Dependencies** — services this package calls and routes other packages mount

See [WORKING_AGREEMENTS.md](../WORKING_AGREEMENTS.md) · [API_CATALOG.md](API_CATALOG.md).

---

## Relationship diagram

```text
prospects 1 ──────────< N leads
                          │
                          ├── N:1 resume_files (1 file per lead v1)
                          ├── N:1 accounts (assigned_account_id) [F6.1]
                          ├── 1 ──< N lead_state_history
                          └── 1 ──< N email_notifications

accounts.role → permissions via ROLE_PERMISSIONS (code)
accounts 1 ──< N assigned leads (when role assignable)
```

---

## What we need to build (per entity)

| Layer | Deliverable |
|-------|-------------|
| **Docs** | Schema files in this folder |
| **DB** | SQLAlchemy models + Alembic migration(s) |
| **API** | Pydantic + FastAPI — **Assigned API routes** + **Actions** per entity; [API_CATALOG.md](API_CATALOG.md) |
| **Services** | Create/update logic, find-or-create prospect, assignment, email |
| **Frontend** | Types mirroring API; public form + internal UI |

### Cross-cutting rules

| Rule | Applies to |
|------|------------|
| UUID primary keys | All entities |
| `created_at` / `updated_at` | All entities |
| Public API exposes | Lead create only (+ health) |
| Internal API exposes | Leads, accounts, auth |

---

## Open design dependencies

| Blocker | Status |
|---------|--------|
| F2.1 Lead state lifecycle | **Closed** — 7 states in `lead.md` |
| F6.1 Lead assignment | **Closed** — `assigned_account_id` |
| F6.2 Permissions | **Closed** — `ROLE_PERMISSIONS` code |
| F3.1 Notification routing | **Closed** — assigned account email |

---

## Related

- `../ARCHITECTURE.md` — system overview
- `../ASSUMPTIONS.md` — decision log
- `../FEATURES.md` — F2.0 entity schema design
- `../WORKING_AGREEMENTS.md` — coordinator protocol
- [API_CATALOG.md](API_CATALOG.md) — all actions & agent packages
