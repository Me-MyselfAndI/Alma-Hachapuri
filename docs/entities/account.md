# Account

Internal user who logs into the system. Handles authentication and role-based access.

> Named **Account** in docs (user-facing: "account"); maps to `accounts` table. Same concept as "User" in architecture overview.

---

## Purpose

- Login for attorneys, admins, intake staff
- JWT subject; [Role](role.md) drives [Permission](permission.md) checks (F6.2)

---

## Table: `accounts`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `email` | VARCHAR(255) | yes | **Unique** — login identifier |
| `password_hash` | VARCHAR(255) | yes | bcrypt/argon2; never expose |
| `role_id` | UUID | FK → `roles.id` | One role per account (v1) |
| `is_active` | BOOLEAN | yes | Default true |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `role` | Role | N accounts → 1 role |
| `attorney_profile` | Attorney | 1 account → 0..1 attorney |

Not every account has an attorney profile (e.g. admin-only accounts).

---

## Business rules

| Rule | Detail |
|------|--------|
| Auth | `POST /auth/token` → JWT with `sub=account_id`, `role`, optional `permissions[]` |
| Seed data | At least one admin + one attorney for demo |
| Password | Hash on create/update only |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `POST /auth/token` | Public | Login → JWT |
| `GET /auth/me` | Bearer | Current account + role |
| `POST /accounts` | Admin | Create account (set `role_id`) |
| `GET /accounts` | Admin | List accounts |

---

## Implementation checklist

- [ ] SQLAlchemy model with `role_id` FK
- [ ] Password hashing utility
- [ ] JWT issue/verify in FastAPI
- [ ] `get_current_account` dependency (eager-load role + permissions)
- [ ] Seed script for demo users + roles
