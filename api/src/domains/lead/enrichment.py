"""F7.1 optional lead enrichment (S8) — dummy LLM placeholder + background queue.

Real OpenAI/resume parsing replaces ``extract_custom_fields_dummy`` later.
Runs via FastAPI ``BackgroundTasks`` so L1b returns before enrichment finishes.
"""

from __future__ import annotations

import logging
from uuid import UUID

from src.core.config import settings
from src.core.database import SessionLocal
from src.domains.lead.models import Lead

logger = logging.getLogger(__name__)


def extract_custom_fields_dummy(*, lead_id: UUID) -> dict:
    """Placeholder LLM output until F7.1 real extraction is wired."""

    return {
        "_source": "dummy_llm_v1",
        "years_experience": 5,
        "primary_skills": ["communication", "project_management"],
        "education_level": "bachelors",
        "lead_id": str(lead_id),
    }


def run_lead_enrichment(lead_id: UUID) -> None:
    """Background worker: write dummy ``custom_fields`` on the lead row."""

    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if lead is None:
            logger.warning("Enrichment skipped: lead %s not found", lead_id)
            return

        lead.custom_fields = extract_custom_fields_dummy(lead_id=lead_id)
        db.commit()
        logger.info("Enrichment complete for lead %s (dummy LLM)", lead_id)
    except Exception:
        logger.exception("Enrichment failed for lead %s", lead_id)
        db.rollback()
    finally:
        db.close()


def schedule_lead_enrichment(lead_id: UUID) -> None:
    """Entry point for ``BackgroundTasks.add_task`` — no-op when flag is off."""

    if not settings.enable_llm_enrichment:
        return
    run_lead_enrichment(lead_id)
