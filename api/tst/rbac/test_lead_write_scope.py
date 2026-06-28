"""403 assignee-scope violations (F6.2) — attorney on another attorney's lead."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.domains.lead.preconditions import LeadState
from tst.rbac.catalog import ASSIGNEE_SCOPED_ROUTES
from tst.rbac.helpers import client_as, invoke
from tst.rbac.seed import RbacWorld


@pytest.mark.parametrize("spec", ASSIGNEE_SCOPED_ROUTES, ids=lambda s: s.route_id)
def test_attorney_denied_on_unassigned_lead(
    db_session,
    rbac_world: RbacWorld,
    spec,
) -> None:
    with client_as(db_session, rbac_world.other_attorney) as client:
        response = invoke(client, spec, rbac_world)
    assert response.status_code == 403


@pytest.mark.parametrize("spec", ASSIGNEE_SCOPED_ROUTES, ids=lambda s: s.route_id)
def test_owner_attorney_allowed_on_own_lead(
    db_session,
    rbac_world: RbacWorld,
    spec,
) -> None:
    with client_as(db_session, rbac_world.owner_attorney) as client:
        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = invoke(client, spec, rbac_world)
    assert response.status_code != 403
    if spec.route_id in ("L4", "L10"):
        assert response.status_code in (200, 204)


def test_intake_can_write_unassigned_lead(db_session, rbac_world: RbacWorld) -> None:
    with client_as(db_session, rbac_world.intake) as client:
        response = client.post(
            f"/api/v1/leads/{rbac_world.lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )
    assert response.status_code == 200


def test_admin_can_write_unassigned_lead(db_session, rbac_world: RbacWorld) -> None:
    with client_as(db_session, rbac_world.admin) as client:
        response = client.post(
            f"/api/v1/leads/{rbac_world.lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )
    assert response.status_code == 200


def test_attorney_cannot_reassign_even_on_own_lead(db_session, rbac_world: RbacWorld) -> None:
    with client_as(db_session, rbac_world.owner_attorney) as client:
        response = client.patch(
            f"/api/v1/leads/{rbac_world.lead.id}",
            json={"assigned_account_id": str(rbac_world.other_attorney.id)},
        )
    assert response.status_code == 403
