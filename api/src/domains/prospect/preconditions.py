"""Pure precondition rules for the prospect domain (F2.3 / F2.6).

No permission checks — those live in route deps. These functions encode
data/state rules documented in docs/entities/prospect.md.
"""

from __future__ import annotations

from datetime import datetime


def normalize_email(email: str) -> str:
    """D7 — lowercase normalized on write."""
    return email.strip().lower()


def prospect_readable_by_id(*, exists: bool) -> bool:
    """GetProspect / ListProspectLeads — 404 only when prospect_id is missing."""
    return exists


def resolve_find_or_create(
    *,
    email: str,
    first_name: str,
    last_name: str,
    existing: tuple[str, str, str] | None,
) -> tuple[str, str, str, bool]:
    """FindOrCreateProspectByEmail — pure decision for match vs insert.

    ``existing`` is ``(normalized_email, first_name, last_name)`` when a row
    matches the lookup key, else ``None``.

    Returns ``(normalized_email, first_name, last_name, created)``.
    On match, names follow last-write-wins (incoming values win).
    """
    normalized = normalize_email(email)
    if existing is None:
        return normalized, first_name, last_name, True
    return normalized, first_name, last_name, False


def lead_visible_for_prospect_list(
    *, archived_at: datetime | None, include_archived: bool = True
) -> bool:
    """ListProspectLeads — D3: archived leads remain visible (default include all)."""
    if archived_at is None:
        return True
    return include_archived
