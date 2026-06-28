"""FastAPI router — L5 (resume download).

Mounted from ``src/main.py`` under ``/api/v1/leads/{lead_id}/resume`` so the
lead-id path parameter is available without this module declaring it twice.
The router has **no prefix** of its own; tests/main wire the mount point.

Permission model (D1/D2): any account holding ``read_leads`` may download
any lead's resume — no assignee scope. Archived leads remain readable (D3)
until the F2.5 retention job removes the binary.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.deps import get_db, require_permission
from src.domains.lead.models import Lead
from src.domains.resume_file import service as storage_service
from src.domains.resume_file.models import ResumeFile

router = APIRouter(tags=["resume"])


@router.get(
    "",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Resume binary stream.",
            "content": {"application/octet-stream": {}},
        },
        404: {"description": "Lead or resume file missing."},
    },
    summary="Download a lead's resume (L5).",
)
def download_lead_resume(
    lead_id: uuid.UUID = Path(..., description="ID of the lead whose resume to download."),
    db: Session = Depends(get_db),
    _account=Depends(require_permission("read_leads")),
) -> StreamingResponse:
    """Stream a lead's resume binary.

    Returns 404 if the lead does not exist or has no resume attached. Per D3
    archived leads are **not** rejected — the archive timestamp is intentionally
    ignored here; only deletion (via F2.5) hides the file.
    """

    lead = db.get(Lead, lead_id)
    if lead is None or lead.resume_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    resume = db.get(ResumeFile, lead.resume_file_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    try:
        iterator, content_type = storage_service.open_stream(resume)
    except storage_service.ResumeDownloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    filename = (resume.original_filename or "resume").replace('"', "")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iterator, media_type=content_type, headers=headers)
