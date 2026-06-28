# Resume file storage

Local disk storage for uploaded resume files (PDF/DOC/DOCX). The API is the only writer.

## Layout

```text
storage/
└── uploads/          # Resume binaries (gitignored except .gitkeep)
    └── temp/         # Pending intake files (Flow A1) until verified
```

## Configuration

In the **repo root** `.env`:

```text
UPLOADS_DIR=storage/uploads
```

Paths are resolved from the monorepo root (see `api/src/core/paths.py`), not from the
current working directory. Override with an absolute path if needed.

## Who uses this

Only the **API service** (`api/`) reads and writes files here. The webapp uploads via multipart to the API.
