# Attorney (merged into Account)

> **Status: merged — 2026-06-27.** There is no `attorneys` table. An “attorney” is an **account** with `role=attorney`.

All schema, API actions, and assignment logic live in **[account.md](account.md)**.

---

## Assigned API routes (agent checklist)

**No separate agent.** Use [account.md](account.md) assigned routes. Former attorney routes map as:

| Old ID | Replacement |
|--------|-------------|
| T1 `GET /attorneys` | A4 `GET /accounts?role=attorney` |
| T2 `GET /attorneys/{id}` | A5 `GET /accounts/{id}` |
| T3 `POST /attorneys` | A3 `POST /accounts` with `"role": "attorney"` |
| T4 `PATCH /attorneys/{id}` | A6 `PATCH /accounts/{id}` |

---

## Domain language

The brief still says “an attorney inside the company” — that maps to:

| Concept | Implementation |
|---------|----------------|
| Attorney logs in | `accounts` row, any role |
| Attorney handles leads | `role=attorney` (or `intake_coordinator`) |
| Assigned on lead | `leads.assigned_account_id` → `accounts.id` |
| New-lead notification | `work_email` or `email` on assigned account |
| Default assignee | `is_default_assignee=true` on one `role=attorney` account |

---

## Related

- [account.md](account.md) — canonical
- [lead.md](lead.md) — `assigned_account_id`
