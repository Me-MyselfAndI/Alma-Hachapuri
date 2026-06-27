# Role

Named access profile assigned to accounts. Permissions attach to roles, not individual accounts (F6.2).

---

## Purpose

- Model `admin`, `attorney`, `intake_coordinator`, `readonly` as data — not a string enum on `accounts`
- Central place to define what each role can do (via [Permission](permission.md) join)
- JWT can include `role` name from joined role row

---

## Table: `roles`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `name` | VARCHAR(50) | yes | **Unique** slug, e.g. `admin`, `attorney` |
| `description` | VARCHAR(255) | no | Human-readable |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

---

## Join table: `role_permissions`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `role_id` | UUID | FK → `roles.id` | |
| `permission_id` | UUID | FK → `permissions.id` | |
| | | PK `(role_id, permission_id)` | |

Exact mappings → F6.2 (deferred). Seed with empty or default sets per role.

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `accounts` | Account | 1 role → N accounts |
| `permissions` | Permission | N roles ↔ N permissions (via `role_permissions`) |

---

## Seed roles (proposed)

| `name` | Typical use |
|--------|-------------|
| `admin` | Full access, manage users |
| `attorney` | Handle assigned leads |
| `intake_coordinator` | Intake / outreach support |
| `readonly` | View-only |

---

## Business rules

| Rule | Detail |
|------|--------|
| One role per account | `accounts.role_id` FK (v1) |
| Auth check | Load account → role → permissions; or embed permission keys in JWT at login |
| Immutable slug | `name` stable for code checks; use `id` in FKs |
| Admin manages roles | Optional v1: seed-only; no CRUD UI required for assessment |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `GET /roles` | Admin | List roles (optional v1) |
| Embedded in `GET /auth/me` | Bearer | Return role name + permission keys |

---

## Implementation checklist

- [ ] SQLAlchemy models: `Role`, `RolePermission`
- [ ] Seed migration with 4 default roles
- [ ] `has_permission(account, "read_leads")` helper
- [ ] JWT claims: `role`, `permissions[]` (optional)
