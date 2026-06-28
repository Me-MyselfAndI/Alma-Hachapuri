# Domain: Resume file

**Slice:** Prospect & resume · **Doc:** [docs/entities/resume-file.md](../../../docs/entities/resume-file.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `ResumeFile` |
| `schemas.py` | ResumeFileRead (no storage_key in public responses) |
| `service.py` | StorageService (S2) — local `storage/uploads/` |
| `router.py` | L5 — mount under leads: `/api/v1/leads/{lead_id}/resume` |

## Depends on

Database foundation, `settings.uploads_dir`

## Consumed by

`domains.lead` L1 (save), L5 (download)
