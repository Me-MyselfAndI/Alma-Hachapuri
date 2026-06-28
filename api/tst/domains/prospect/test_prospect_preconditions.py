"""Precondition tests for prospect domain — data/state rules only (F2.6).

Permission enforcement is bypassed in conftest; these tests do not cover RBAC.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domains.prospect.preconditions import (
    lead_visible_for_prospect_list,
    normalize_email,
    prospect_readable_by_id,
    resolve_find_or_create,
)

UTC = timezone.utc


class TestNormalizeEmail:
    def test_lowercases_and_strips(self) -> None:
        assert normalize_email("  Jane.Doe@Example.COM  ") == "jane.doe@example.com"

    @pytest.mark.parametrize(
        "raw",
        ["user@domain.com", "USER@DOMAIN.COM", "  mixed@Case.Org  "],
    )
    def test_lookup_key_is_stable(self, raw: str) -> None:
        assert normalize_email(raw) == normalize_email(raw.upper())


class TestFindOrCreateProspectByEmail:
    def test_creates_when_no_existing_row(self) -> None:
        email, first, last, created = resolve_find_or_create(
            email="  New.Person@Example.COM ",
            first_name="New",
            last_name="Person",
            existing=None,
        )

        assert email == "new.person@example.com"
        assert first == "New"
        assert last == "Person"
        assert created is True

    def test_matches_existing_by_normalized_email(self) -> None:
        email, first, last, created = resolve_find_or_create(
            email="Jane.Doe@Example.COM",
            first_name="Jane",
            last_name="Updated",
            existing=("jane.doe@example.com", "Old", "Name"),
        )

        assert email == "jane.doe@example.com"
        assert created is False

    def test_last_write_wins_on_name_update(self) -> None:
        _, first, last, created = resolve_find_or_create(
            email="jane@example.com",
            first_name="Jane",
            last_name="Smith",
            existing=("jane@example.com", "Jane", "Doe"),
        )

        assert created is False
        assert first == "Jane"
        assert last == "Smith"


class TestGetProspect:
    def test_readable_when_exists(self) -> None:
        assert prospect_readable_by_id(exists=True) is True

    def test_not_found_when_missing(self) -> None:
        assert prospect_readable_by_id(exists=False) is False


class TestListProspectLeads:
    """D3 — archived leads remain listed under their prospect."""

    def test_active_lead_always_listed(self) -> None:
        assert lead_visible_for_prospect_list(archived_at=None) is True

    def test_archived_lead_listed_by_default(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert lead_visible_for_prospect_list(archived_at=archived_at) is True

    def test_archived_lead_hidden_when_opted_out(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert (
            lead_visible_for_prospect_list(
                archived_at=archived_at,
                include_archived=False,
            )
            is False
        )


class TestProspectRouteFailures:
    """P1/P2 HTTP — docs/entities/prospect.md Preconditions."""

    def test_get_prospect_404_when_missing(self, role_client) -> None:
        import uuid

        from src.core.permissions import Role

        client, _ = role_client(Role.INTAKE_COORDINATOR, email="intake-prospect@firm.com")
        response = client.get(f"/api/v1/prospects/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_list_prospect_leads_404_when_missing(self, role_client) -> None:
        import uuid

        from src.core.permissions import Role

        client, _ = role_client(Role.INTAKE_COORDINATOR, email="intake-p2@firm.com")
        response = client.get(f"/api/v1/prospects/{uuid.uuid4()}/leads")
        assert response.status_code == 404

    def test_get_prospect_200_with_lead_count(self, role_client, db_session) -> None:
        from src.core.permissions import Role
        from tst.shared.doc_fixtures import seed_lead

        client, _ = role_client(Role.ADMIN, email="admin-prospect@firm.com")
        lead = seed_lead(db_session)
        response = client.get(f"/api/v1/prospects/{lead.prospect_id}")
        assert response.status_code == 200
        assert response.json()["lead_count"] >= 1

    def test_list_prospect_leads_includes_archived(self, role_client, db_session) -> None:
        from src.core.permissions import Role
        from tst.shared.doc_fixtures import seed_lead

        client, _ = role_client(Role.READONLY, email="readonly-prospect@firm.com")
        lead = seed_lead(db_session, archived=True)
        response = client.get(f"/api/v1/prospects/{lead.prospect_id}/leads")
        assert response.status_code == 200
        ids = {item["id"] for item in response.json()}
        assert str(lead.id) in ids
