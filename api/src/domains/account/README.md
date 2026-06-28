# Domain: Account (+ auth)

**Slice:** Account & login · **Doc:** [docs/entities/account.md](../../../docs/entities/account.md)

Merged attorney model — no separate `attorneys` table.

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `Account` (`accounts` table) |
| `schemas.py` | Pydantic: AccountCreate, AccountRead, TokenResponse, AccountMe, … |
| `service.py` | AccountService, AuthService, SeedService (S3, S9, S10) |
| `router.py` | Routes A1–A9 — mount at `/api/v1/auth`, `/api/v1/accounts` |

## Routes owned

A1–A9 — see entity doc **Assigned API routes**.

## Depends on

`app.core.permissions`, `app.core.security`, `app.core.deps`

## Consumed by

`domains.lead` (S3 on L1)
