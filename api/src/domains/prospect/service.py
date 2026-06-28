"""ProspectService — S1, plus reads for P1/P2.

Spec: docs/entities/prospect.md.

* ``find_or_create_by_email`` — internal helper called by ``LeadService`` (L1b).
  Normalizes the lookup email per D7 and applies last-write-wins to names.
* ``get_prospect`` / ``list_leads_for_prospect`` — back the P1/P2 routes.
  Per D3, archived leads remain visible in the prospect lead list.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domains.lead.models import Lead
from src.domains.prospect.models import Prospect
from src.domains.prospect.preconditions import normalize_email


class ProspectService:
    """Stateless namespace for prospect operations.

    Methods are ``@staticmethod`` so callers can use the class as a typed
    namespace (``ProspectService.find_or_create_by_email(...)``) without
    threading an instance through the DI graph. Sessions are always passed
    in by the caller so transaction boundaries stay at the route layer.
    """

    @staticmethod
    def find_or_create_by_email(
        db: Session,
        *,
        email: str,
        first_name: str,
        last_name: str,
    ) -> tuple[Prospect, bool]:
        """Look up by normalized email; insert on miss.

        Returns ``(prospect, created)``. On match (`created=False`) the
        existing row's ``first_name`` / ``last_name`` are overwritten with
        the incoming values (last-write-wins per spec). The flush happens
        here so the caller sees a row with ``id`` populated before commit.
        """

        normalized = normalize_email(email)
        existing = db.scalar(select(Prospect).where(Prospect.email == normalized))

        if existing is not None:
            existing.first_name = first_name
            existing.last_name = last_name
            db.flush()
            return existing, False

        prospect = Prospect(
            email=normalized,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(prospect)
        db.flush()
        return prospect, True

    @staticmethod
    def get_prospect(db: Session, prospect_id: UUID) -> Prospect | None:
        """Return the prospect row or ``None`` if no such id."""

        return db.get(Prospect, prospect_id)

    @staticmethod
    def list_leads_for_prospect(db: Session, prospect_id: UUID) -> list[Lead]:
        """All leads for the prospect, newest first (D3: archived included)."""

        stmt = (
            select(Lead)
            .where(Lead.prospect_id == prospect_id)
            .order_by(Lead.created_at.desc())
        )
        return list(db.scalars(stmt))
