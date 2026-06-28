# Domain: Lead

**Slice:** Lead & state history · **Doc:** [docs/entities/lead.md](../../../docs/entities/lead.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `Lead`, state enum |
| `schemas.py` | LeadCreateForm, LeadRead, LeadUpdate, LeadTransitionRequest, … |
| `service.py` | LeadService (S4, S5) |
| `enrichment.py` | F7.1 dummy LLM + background queue (S8) |
| `tokens.py` | Verification token hash / reissue (L1a, E3 retry) |
| `intake_claim.py` | L1b row lock + idempotent verify claim (S4b) |
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
