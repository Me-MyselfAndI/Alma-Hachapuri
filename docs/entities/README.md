# Entity schemas

Design docs for each persisted domain entity — fields, relationships, constraints, and API touchpoints. Implementation maps to SQLAlchemy models in `backend/app/models/` and Pydantic schemas in `backend/app/schemas/`.

**Status:** Planning (F2.0). Exact ACL and full state machine still in PLAN (F6.2, F2.1).

---

## Entity index

| Entity | Table (proposed) | Schema doc | Required for brief |
|--------|------------------|------------|-------------------|
| [Prospect](prospect.md) | `prospects` | External person; 1 → N leads | Yes (implied) |
| [Lead](lead.md) | `leads` | Intake submission | Yes |
| [Resume file](resume-file.md) | `resume_files` | CV binary metadata | Yes |
| [Account](account.md) | `accounts` | Internal login | Yes (auth UI) |
| [Role](role.md) | `roles` | Access profile for accounts | Yes (RBAC) |
| [Permission](permission.md) | `permissions` | Capability granted to roles | Yes (RBAC) |
| [Attorney](attorney.md) | `attorneys` | Staff profile linked to account | Yes (notification + assignment) |
| [Email notification](email-notification.md) | `email_notifications` | Outbound mail audit log | Recommended |
| [Lead state history](lead-state-history.md) | `lead_state_history` | State transition audit | Recommended |

**Not separate tables:** feature flags (env), email templates (code).

**Join tables:** `role_permissions` (see [Role](role.md)).

---

## Relationship diagram

```text
prospects 1 ──────────< N leads
                          │
                          ├── N:1 resume_files (1 file per lead v1)
                          ├── N:1 attorneys (assigned_attorney_id) [planned F6.1]
                          ├── 1 ──< N lead_state_history
                          └── 1 ──< N email_notifications

roles N ──< N permissions  (role_permissions)
  │
  └── 1 ──< N accounts 1 ── 0..1 attorneys (attorney.account_id)
```

---

## What we need to build (per entity)

| Layer | Deliverable |
|-------|-------------|
| **Docs** | Schema files in this folder (this pass) |
| **DB** | SQLAlchemy models + Alembic migration(s) |
| **API** | Pydantic request/response schemas + FastAPI routes |
| **Services** | Create/update logic, find-or-create prospect, assignment, email enqueue |
| **Frontend** | Types mirroring API responses; forms for public lead + internal views |

### Cross-cutting rules

| Rule | Applies to |
|------|------------|
| UUID primary keys | All entities |
| `created_at` / `updated_at` | All entities |
| Soft-delete optional | Accounts only (v1: can defer) |
| Public API exposes | Lead create only (+ health) |
| Internal API exposes | Leads list/detail/update, accounts, attorneys |

---

## Open design dependencies

| Blocker | Entities affected |
|---------|-------------------|
| F2.1 Lead state lifecycle | `leads.state`, `lead_state_history` |
| F6.1 Lead assignment | `leads.assigned_attorney_id` |
| F6.2 Permissions | Route guards; `role_permissions` seed data |
| F3.1 Notification routing | `email_notifications.recipient`, send triggers |

---

## Related docs

- `../ARCHITECTURE.md` — system overview
- `../ASSUMPTIONS.md` — A2 prospect/lead cardinality, etc.
- `../FEATURES.md` — F2.0 entity schema design
