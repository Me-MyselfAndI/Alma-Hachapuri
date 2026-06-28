# File storage — resume uploads

Binary storage for uploaded resume files (PDF, DOC, DOCX). Local disk in development; swappable to S3 in production.

## Layout

```text
storage/
├── uploads/           # Runtime files (.gitignored except .gitkeep)
│   └── .gitkeep
└── README.md
```

## Configuration

Set in root `.env`:

```text
UPLOADS_DIR=../storage/uploads
```

(Path is relative to the `api/` working directory when running uvicorn.)

Metadata (filename, mime type, storage key) lives in Postgres — see `resume_files` table in entity docs.

## Who uses this

Only the **API service** (`../api/`) reads and writes files here. The webapp uploads via multipart to the API.
