"""403 violations for account routes (A3–A6, A4 assignee list)."""

from __future__ import annotations

import pytest

from src.core.permissions import Role
from tst.rbac.catalog import L4_REASSIGN_DENIED, ROUTE_CATALOG
from tst.rbac.helpers import invoke_as
from tst.rbac.seed import RbacWorld, account_for_role

_ACCOUNT_ROUTES = tuple(s for s in ROUTE_CATALOG if s.entity == "account" and s.denied_roles)


def _denial_cases():
    for spec in _ACCOUNT_ROUTES:
        for role in spec.denied_roles:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-403")


@pytest.mark.parametrize(("spec", "role"), list(_denial_cases()))
def test_account_route_denied_for_role(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role) if role != Role.ATTORNEY else rbac_world.other_attorney
    if spec.route_id in ("A3", "A4", "A4_ASSIGN", "A5", "A6"):
        account = account_for_role(rbac_world, role)

    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 403


def test_admin_can_list_accounts(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "A4")
    response = invoke_as(db_session, rbac_world.admin, spec, rbac_world)
    assert response.status_code == 200


def test_admin_can_list_for_assignment(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "A4_ASSIGN")
    response = invoke_as(db_session, rbac_world.admin, spec, rbac_world)
    assert response.status_code == 200


@pytest.mark.parametrize("role", list(L4_REASSIGN_DENIED))
def test_reassign_lead_denied_without_assign_lead(
    db_session,
    rbac_world: RbacWorld,
    role: Role,
) -> None:
    from tst.rbac.helpers import client_as

    account = account_for_role(rbac_world, role)
    if role == Role.ATTORNEY:
        account = rbac_world.owner_attorney

    with client_as(db_session, account) as client:
        response = client.patch(
            f"/api/v1/leads/{rbac_world.lead.id}",
            json={"assigned_account_id": str(rbac_world.other_attorney.id)},
        )

    assert response.status_code == 403
