# Account

Internal user who logs into the system. Handles authentication, role-based access, and (for attorney-role accounts) lead assignment and notifications.

> Named **Account** in docs; maps to `accounts` table. Replaces the former separate **Attorney** entity — see [Decision: merged model](#decision-merged-model).

---

## Purpose

- Login for all internal users (admin, attorney, intake, readonly)
- JWT subject; `role` enum drives permissions via code (`src/core/permissions.py`)
- Attorney-role accounts: assignable lead owners + new-lead email recipient

---

## Table: `accounts`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `email` | VARCHAR(255) | yes | **Unique** — login identifier |
| `password_hash` | VARCHAR(255) | yes | bcrypt/argon2; never expose |
| `role` | VARCHAR(50) | yes | **Immutable after create.** Enum: `admin`, `attorney`, `intake_coordinator`, `readonly` |
| `first_name` | VARCHAR(100) | yes | Display name |
| `last_name` | VARCHAR(100) | yes | Display name |
| `work_email` | VARCHAR(255) | no | Notification recipient; defaults to `email` if null |
| `is_default_assignee` | BOOLEAN | yes | Default false; at most one `true` among `role=attorney` (F6.1) |
| `is_active` | BOOLEAN | yes | Default true |
| `created_at` | TIMESTAMPTZ | yes | |
| `updated_at` | TIMESTAMPTZ | yes | |

No `role_id` FK — no `roles` / `permissions` tables. See [permission.md](permission.md).

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `assigned_leads` | Lead | 1 account → N leads (via `leads.assigned_account_id`) |
| `state_changes` | Lead state history | 1 account → N history rows |

---

## Decision: merged model

**2026-06-27 — confirmed.** Account and Attorney are one table.

| Before | After |
|--------|-------|
| `accounts` + `attorneys` | Single `accounts` |
| `leads.assigned_attorney_id` | `leads.assigned_account_id` |
| Admin without attorney profile | `role=admin` — no assignment, no `is_default_assignee` |
| “Attorney inside the company” | Account with `role=attorney` |

**Why merge is fine here:** v1 has no non-attorney staff beyond admin/intake/readonly — all modeled as `role`. Different access = different role, not a second entity. `work_email` stays as optional column when notification address ≠ login email.

**When split would matter again:** paralegals who log in but are never assignees *and* need different identity from attorneys — out of scope v1.

---

## Role enum (immutable)

Set on create; **not** changeable via PATCH (admin must create a new account to change role).

| `role` | Assignable | Typical permissions |
|--------|------------|---------------------|
| `admin` | no | all |
| `attorney` | yes | `read_leads`, `write_lead` (assigned leads), `read_emails`, `export_leads` |
| `intake_coordinator` | yes | `read_leads`, `write_lead`, `assign_lead`, `read_prospect`, `send_email`, `read_emails`, `export_leads` |
| `readonly` | no | `read_leads`, `read_prospect`, `read_emails` |

Full matrix in [permission.md](permission.md) → `ROLE_PERMISSIONS`.

---

## Business rules

| Rule | Detail |
|------|--------|
| Auth | `POST /auth/token` → JWT with `sub`, `role`, `permissions[]` |
| `role` immutable | Reject PATCH that tries to change `role` |
| Auto-assign (F6.1) | On lead create → `assigned_account_id` = account where `role=attorney` AND `is_default_assignee=true` |
| Notifications (F3.1) | New-lead email → assigned account's `work_email` or `email` |
| Seed | At least one `admin` + one `attorney` (`is_default_assignee=true`) |

---

## Actions

> **Agent rule:** Every entity doc must list **all** HTTP routes and service methods this package owns in [Assigned API routes](#assigned-api-routes-agent-checklist) below. Full specs follow in order.

### Assigned API routes (agent checklist)

**Implement in:** `api/src/api/auth.py`, `api/src/api/accounts.py`, `api/src/services/auth.py`, `api/src/services/account.py`, `api/src/core/security.py`

| ID | Type | Method | Path | Permission |
|----|------|--------|------|------------|
| A1 | HTTP | POST | `/api/v1/auth/token` | public |
| A2 | HTTP | GET | `/api/v1/auth/me` | Bearer |
| A3 | HTTP | POST | `/api/v1/accounts` | `manage_users` |
| A4 | HTTP | GET | `/api/v1/accounts` | `manage_users` |
| A5 | HTTP | GET | `/api/v1/accounts/{account_id}` | `manage_users` |
| A6 | HTTP | PATCH | `/api/v1/accounts/{account_id}` | `manage_users` |
| A7 | HTTP | PATCH | `/api/v1/auth/me` | Bearer (self) |
| A8 | HTTP | PATCH | `/api/v1/auth/me/password` | Bearer (self) |
| A9 | HTTP | POST | `/api/v1/auth/logout` | Bearer (optional) |
| S3 | Service | `AccountService.resolve_default_assignee()` | — | called by L1 |
| S9 | Service | `AuthService.authenticate`, `create_access_token` | — | called by A1 |
| S10 | Service | `SeedService.seed_demo_accounts()` | — | CLI / startup |

**Depends on:** [permission.md](permission.md) (`ROLE_PERMISSIONS`, `require_permission`). **Consumed by:** [lead.md](lead.md) L1 (S3).

## Preconditions

Readable operation names for data/state rules. Route IDs (A1, S3, …) stay in the checklist above for implementers.

| Operation | Who can call | What must be true | If not |
|-----------|--------------|-------------------|--------|
| **Login** | Public | OAuth2 form: `username` (= email) and `password` present; email looked up after **lowercase normalization (D7)**; password verifies against `password_hash`; account **`is_active=true`** | **401** — wrong email/password (same message, no enumeration); **403** — account inactive; **422** — missing/invalid form fields |
| **GetCurrentAccount** | Signed in (Bearer) | Valid JWT; `sub` resolves to existing account; **`is_active=true`** | **401** — missing/invalid/expired token or account deleted; **403** — deactivated account |
| **CreateAccount** | Admin (`manage_users`) | Body: valid `email` (unique; **stored lowercase — D7**), `password` ≥ 8 chars, `role` ∈ enum, `first_name` / `last_name` required; optional `work_email`; **`is_default_assignee=true` only when `role=attorney` (D6)** — otherwise reject | **422** — validation (bad role, short password, `is_default_assignee` on non-attorney); **409** — duplicate email (case-insensitive after D7) |
| **ListAccounts** | Admin (`manage_users`) | Optional query: `page` ≥ 1, `page_size` 1–100, optional `role` filter ∈ enum | **422** — invalid pagination or role filter |
| **GetAccount** | Admin (`manage_users`) | Path `account_id` is valid UUID; target account row exists | **422** — malformed UUID; **404** — account not found |
| **UpdateAccount** | Admin (`manage_users`) | Target account exists; body omits **`role`** (immutable); optional fields valid; **`is_default_assignee=true` only when target `role=attorney` (D6)** | **404** — not found; **422** — validation (`role` in body, short password, `is_default_assignee` on non-attorney) |
| **ChangeOwnEmail** | Signed in (self) | `current_password` verifies; new `email` valid and unique; **stored lowercase (D7)** | **401** / **400** — wrong `current_password`; **409** — duplicate email; **422** — invalid email |
| **ChangeOwnPassword** | Signed in (self) | `current_password` verifies; `new_password` ≥ 8 chars | **401** / **400** — wrong `current_password`; **422** — password too short |
| **Logout** | Signed in (optional) | Stateless JWT v1 — no server-side revoke list | **204** always (idempotent); client discards token |
| **ResolveDefaultAssignee** *(background)* | Internal — called from **VerifyEmailAndCreateLead** / lead create orchestration | Exactly **one** account: `role=attorney` **AND** `is_default_assignee=true` **AND** `is_active=true` **(D5)**; return value becomes `leads.assigned_account_id` | Service error rolls back lead txn — HTTP mapping **TBD (D4)** |
| **SeedDemoAccounts** *(background)* | CLI / startup (no HTTP auth) | DB migrated; creates ≥1 `admin` and ≥1 **`role=attorney`** with **`is_default_assignee=true`** and **`is_active=true`** | **500** / log on DB failure; incomplete seed breaks **ResolveDefaultAssignee** on first lead create |

**Side effects (not preconditions):** When **CreateAccount** or **UpdateAccount** sets `is_default_assignee=true` on an attorney, clear the flag on all other attorney rows (transactional; at most one default).

> **Missing default assignee (D4 — decision pending):** If **ResolveDefaultAssignee** finds zero or multiple qualifying rows, three options remain open — pick one at implementation time:
> 1. **Block lead verification/create** — return **503** (or **500**) to the public caller with a generic message.
> 2. **Accept with null assignee** — create the lead with `assigned_account_id=null`; staff must assign manually.
> 3. **Fail health check** — `/health` (or startup) reports not-ready until seed/admin configures a default assignee.

### HTTP

#### A1 · `POST /api/v1/auth/token` — Login (public)

**Content-Type:** `application/x-www-form-urlencoded` (OAuth2 password flow)

| Field | Value |
|-------|-------|
| `username` | Account email |
| `password` | Plain password |

**Response `200` — `TokenResponse`:**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** 401 invalid credentials; 403 if `is_active=false`.

**JWT claims:** `sub` (account_id), `role`, `permissions` (computed from `ROLE_PERMISSIONS` at login), `exp`.

**Authorization note:** Protected routes use `require_permission`, which loads the account from the DB and checks **`account.role`** against `ROLE_PERMISSIONS`. JWT `permissions[]` is included for **frontend convenience** (`GET /auth/me`, UI gating) — stale permissions in an old token do **not** grant extra API access after a role change.

---

#### A2 · `GET /api/v1/auth/me` — Current account

**Auth:** Bearer JWT

**Response `200` — `AccountMe`:**

```json
{
  "id": "uuid",
  "email": "attorney@firm.com",
  "role": "attorney",
  "permissions": ["export_leads", "read_emails", "read_leads", "write_lead"],
  "first_name": "John",
  "last_name": "Smith",
  "work_email": "john@firm.com",
  "is_default_assignee": true,
  "is_active": true
}
```

---

#### A3 · `POST /api/v1/accounts` — Create account

**Permission:** `manage_users`

**Body — `AccountCreate`:**

```json
{
  "email": "new@firm.com",
  "password": "min-8-chars",
  "role": "attorney",
  "first_name": "Jane",
  "last_name": "Doe",
  "work_email": "jane@firm.com",
  "is_default_assignee": false
}
```

**Response `201` — `AccountRead`** (no password_hash).

**Side effect:** If `is_default_assignee=true`, clear flag on other attorney accounts.

**Guards (D4):**

- `is_default_assignee=true` is only valid when `role=attorney` (D6 — else 422).
- Cannot clear `is_default_assignee` on the only remaining active default attorney (set another in the same request).
- Cannot deactivate (`is_active=false`) the only remaining active default attorney.

---

#### A4 · `GET /api/v1/accounts` — List accounts

**Permission:** `manage_users`

**Query:** `page`, `page_size`, `role` (optional filter)

**Response `200` — `Paginated[AccountRead]`**

---

#### A5 · `GET /api/v1/accounts/{account_id}`

**Permission:** `manage_users`

**Response `200` — `AccountRead`**

---

#### A6 · `PATCH /api/v1/accounts/{account_id}` — Admin update

**Permission:** `manage_users`

**Body — `AccountUpdate` (optional fields; `role` NOT allowed):**

```json
{
  "is_active": false,
  "password": "new-password",
  "first_name": "Jane",
  "last_name": "Doe",
  "work_email": "jane@firm.com",
  "is_default_assignee": true
}
```

**Response `200` — `AccountRead`**

---

#### A7 · `PATCH /api/v1/auth/me` — Change own email

**Auth:** Bearer JWT (self only)

**Body — `AccountEmailUpdate`:**

```json
{
  "email": "new@firm.com",
  "current_password": "existing-password"
}
```

**Response `200` — `AccountMe`**

**Validation:** Verify `current_password`; reject duplicate email (409).

**Optional:** Return new JWT in response header or body field `access_token`.

---

#### A8 · `PATCH /api/v1/auth/me/password` — Change own password

**Auth:** Bearer JWT (self only)

**Body — `AccountPasswordUpdate`:**

```json
{
  "current_password": "existing-password",
  "new_password": "min-8-chars"
}
```

**Response `204`** No content.

**Validation:** Verify `current_password`; enforce password policy.

---

#### A9 · `POST /api/v1/auth/logout` — Logout

**Auth:** Bearer JWT (optional — idempotent)

**Response `204`** No content.

**Behavior:** Stateless JWT — server has nothing to revoke v1. Client **must** discard token. Endpoint exists for API symmetry and future denylist.

---

### Service — `AuthService`

```python
# api/src/services/auth.py

def authenticate(db: Session, *, email: str, password: str) -> Account | None:
    """Verify credentials; return None if invalid/inactive."""

def create_access_token(account: Account) -> str:
    """Build JWT: sub, role, permissions from ROLE_PERMISSIONS."""

def hash_password(plain: str) -> str:
def verify_password(plain: str, hashed: str) -> bool:
```

### Service — `AccountService`

```python
def create_account(db: Session, data: AccountCreate) -> Account:
def list_accounts(db: Session, *, page: int, page_size: int, role: str | None) -> tuple[list[Account], int]:
def get_account(db: Session, account_id: UUID) -> Account | None:
def update_account(db: Session, account_id: UUID, data: AccountUpdate) -> Account:
def update_own_email(db: Session, account: Account, data: AccountEmailUpdate) -> Account:
def update_own_password(db: Session, account: Account, data: AccountPasswordUpdate) -> None:
def resolve_default_assignee(db: Session) -> Account:
    """Account with role=attorney and is_default_assignee=true."""
def list_assignable_accounts(db: Session) -> list[Account]:
    """Accounts with role in (attorney, intake_coordinator) for dropdown."""
```

---

## Proposed additions (still pending)

| ID | Action | Notes |
|----|--------|-------|
| A10 | `POST /auth/refresh` | Only if refresh tokens added |
| A11 | `POST /accounts/{id}/reset-password` | Admin reset |
| A12 | `DELETE /accounts/{id}` | Soft-deactivate alias |

---

## Implementation checklist

- [ ] SQLAlchemy model with `role` enum column (no role_id FK)
- [ ] `src/core/permissions.py` — `ROLE_PERMISSIONS`
- [ ] Password hashing + JWT (A1, A2, A7–A9)
- [ ] Account CRUD routes (A3–A6)
- [ ] `get_current_account` + `require_permission` deps
- [ ] Seed: admin + default attorney account
