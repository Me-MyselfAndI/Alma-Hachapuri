# Domain: Prospect

**Slice:** Prospect & resume · **Doc:** [docs/entities/prospect.md](../../../docs/entities/prospect.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `Prospect` |
| `schemas.py` | ProspectRead, ProspectSummary |
| `preconditions.py` | D7 email normalize, find-or-create rules |
| `service.py` | ProspectService (S1 find_or_create_by_email) |
| `router.py` | P1 GetProspect, P2 ListProspectLeads — mount at `/api/v1/prospects` |

## Depends on

Database foundation

## Consumed by

`domains.lead` L1 (S1)
