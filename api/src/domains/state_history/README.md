# Domain: Lead state history

**Slice:** Lead & state history · **Doc:** [docs/entities/lead-state-history.md](../../../docs/entities/lead-state-history.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `LeadStateHistory` |
| `schemas.py` | LeadStateHistoryRead |
| `service.py` | LeadStateHistoryService (S6) |
| `router.py` | L7 — mount under `/api/v1/leads/{lead_id}/state-history` |

## Called by

L1 (record_initial), L4/L10 (record_transition + note)

## Depends on

`domains.lead.models`, `domains.account.models`
