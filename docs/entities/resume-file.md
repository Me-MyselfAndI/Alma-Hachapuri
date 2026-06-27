# Resume file

Metadata for an uploaded CV/resume. Binary stored on disk (`./uploads/`) or S3; this table holds the pointer.

---

## Purpose

- Track original filename, mime type, size, storage location
- Enable secure download via API (never expose raw filesystem path to client)

---

## Table: `resume_files`

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID | PK | |
| `storage_key` | VARCHAR(500) | yes | Relative path or S3 key, e.g. `uploads/{uuid}.pdf` |
| `original_filename` | VARCHAR(255) | yes | As uploaded |
| `mime_type` | VARCHAR(100) | yes | e.g. `application/pdf` |
| `size_bytes` | INTEGER | yes | |
| `created_at` | TIMESTAMPTZ | yes | |

---

## Relationships

| Relation | Target | Cardinality |
|----------|--------|-------------|
| `lead` | Lead | 1 file → 1 lead (v1) |

---

## Business rules

| Rule | Detail |
|------|--------|
| Allowed types | PDF, DOC, DOCX (TBD — validate on upload) |
| Max size | e.g. 10 MB (TBD) |
| Write | FastAPI saves bytes on `POST /leads`; insert row; link from lead |
| Read | `GET /leads/{id}/resume` streams file; auth internal only |
| Delete | Orphan cleanup deferred (v1: retain with lead) |

---

## Storage adapter (implementation)

| Backend | `storage_key` example |
|---------|----------------------|
| Local | `uploads/a1b2c3d4.pdf` |
| S3 | `resumes/a1b2c3d4.pdf` |

Same interface: `save(bytes) → storage_key`, `open(key) → stream`.

---

## Implementation checklist

- [ ] SQLAlchemy model
- [ ] Storage service (local filesystem v1)
- [ ] Upload validation in lead create
- [ ] Download endpoint with content-disposition
