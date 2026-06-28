"""403 violations: prospect routes (P1, P2) — attorney lacks read_prospect."""

from __future__ import annotations

import pytest

from src.core.permissions import Role
from tst.rbac.catalog import ROUTE_CATALOG
from tst.rbac.helpers import invoke_as
from tst.rbac.seed import RbacWorld, account_for_role

_PROSPECT_ROUTES = tuple(s for s in ROUTE_CATALOG if s.entity == "prospect")


def _denial_cases():
    for spec in _PROSPECT_ROUTES:
        for role in spec.denied_roles:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-403")


@pytest.mark.parametrize(("spec", "role"), list(_denial_cases()))
def test_prospect_route_denied_for_role(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.ADMIN, Role.INTAKE_COORDINATOR, Role.READONLY])
@pytest.mark.parametrize("route_id", ["P1", "P2"])
def test_prospect_allowed_for_roles_with_read_prospect(
    db_session,
    rbac_world: RbacWorld,
    role: Role,
    route_id: str,
) -> None:
    spec = next(s for s in _PROSPECT_ROUTES if s.route_id == route_id)
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 200
