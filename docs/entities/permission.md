# Permission

Atomic capability that can be granted to a [Role](role.md). Supports varying access without hard-coding enums in application code (F6.2).

---

## Purpose

- Define permission **types** as rows (not only code constants)
- Many-to-many with roles via `role_permissions`
- Exact role→permission matrix decided later (F6.2)

---

## Table: `permissions`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `key` | VARCHAR(50) | yes | **Unique** machine key, e.g. `read_leads` |
| `description` | VARCHAR(255) | no | Human-readable |
| `created_at` | TIMESTAMPTZ | yes | |

---

## Seed permissions (proposed — from ARCHITECTURE draft)

| `key` | Meaning |
|-------|---------|
| `read_leads` | View lead list and detail |
| `write_lead` | Update lead fields / state |
| `assign_lead` | Change `assigned_attorney_id` |
| `read_prospect` | View prospect and linked leads |
| `manage_users` | Create/disable accounts |
| `manage_attorneys` | Manage attorney profiles |

Assignment-scoped `write_lead` (assigned leads only) is **authorization logic**, not a separate permission key — enforced in service layer using `assigned_attorney_id` + role.

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `roles` | Role | N permissions ↔ N roles (via `role_permissions`) |

---

## Business rules

| Rule | Detail |
|------|--------|
| Stable keys | Code references `permission.key`; seed data is source of truth |
| Check | `permission.key in account.role.permissions` or cached set on JWT |
| F6.2 | Populate `role_permissions` when matrix is agreed |

---

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Seed migration with permission keys
- [ ] Link to roles in seed data (when F6.2 closes)
