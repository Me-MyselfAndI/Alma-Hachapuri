# Domain: Lead

**Slice:** Lead & state history · **Doc:** [docs/entities/lead.md](../../../docs/entities/lead.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `Lead`, state enum |
| `schemas.py` | LeadCreateForm, LeadRead, LeadUpdate, LeadTransitionRequest, … |
| `service.py` | LeadService (S4, S5), EnrichmentService (S8) |
| `router.py` | L1–L4, L10, L13, L14 — mount at `/api/v1/leads` |

## Sub-routers (mounted from other domains in `src/main.py`)

| Route | Import from |
|-------|-------------|
| L5 resume | `domains.resume_file.router` |
| L6 emails | `domains.email.router` (lead-scoped routes) |
| L7 state-history | `domains.state_history.router` |

## L1 orchestration imports

S1 prospect · S2 storage · S3 account · S6 state_history · S7 email

## Depends on

Account & login, Prospect & resume slices
