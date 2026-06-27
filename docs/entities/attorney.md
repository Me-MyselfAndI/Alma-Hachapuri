# Attorney

Staff profile for someone who handles leads — linked to an internal account.

---

## Purpose

- Represent attorneys as assignable lead owners
- Notification target for new-lead emails (F3.1)
- Optional fields beyond login (display name, bar ID, etc.)

---

## Table: `attorneys`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `account_id` | UUID | FK → `accounts.id` | **Unique** — one profile per account |
| `first_name` | VARCHAR(100) | yes | Display |
| `last_name` | VARCHAR(100) | yes | Display |
| `work_email` | VARCHAR(255) | yes | Notification recipient; may differ from login email |
| `is_default_assignee` | BOOLEAN | yes | Default false; one true for auto-assign (F6.1) |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `account` | Account | 1 attorney → 1 account |
| `assigned_leads` | Lead | 1 attorney → N leads |

---

## Business rules

| Rule | Detail |
|------|--------|
| Auto-assign (F6.1) | On lead create, set `assigned_attorney_id` to attorney where `is_default_assignee=true`; fallback TBD |
| Override | Internal PATCH can reassign |
| Create | Admin creates account + attorney profile together (or link existing account) |

---

## API touchpoints

| Endpoint | Auth | Action |
|----------|------|--------|
| `GET /attorneys` | Internal | List for assignment dropdown |
| `POST /attorneys` | Admin | Create profile |
| `PATCH /attorneys/{id}` | Admin | Update incl. default assignee flag |

---

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Constraint: at most one `is_default_assignee=true` (app or DB)
- [ ] Assignment resolver on lead create
- [ ] Include in lead list/detail responses
