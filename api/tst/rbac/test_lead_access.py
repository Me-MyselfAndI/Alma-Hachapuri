"""403 violations: role lacks permission for lead routes."""

from __future__ import annotations

import pytest

from src.core.permissions import Role
from tst.rbac.catalog import ROUTE_CATALOG
from tst.rbac.helpers import invoke_as
from tst.rbac.seed import RbacWorld, account_for_role

_LEAD_ROUTES = tuple(
    s for s in ROUTE_CATALOG if s.entity == "lead" and s.denied_roles
)


def _denial_cases():
    for spec in _LEAD_ROUTES:
        for role in spec.denied_roles:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-403")


@pytest.mark.parametrize(("spec", "role"), list(_denial_cases()))
def test_lead_route_denied_for_role(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 403


def _allowed_read_cases():
    for spec in ROUTE_CATALOG:
        if spec.entity != "lead" or spec.denied_roles:
            continue
        if spec.route_id not in ("L2", "L3"):
            continue
        for role in Role:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-allowed")


@pytest.mark.parametrize(("spec", "role"), list(_allowed_read_cases()))
def test_lead_read_allowed_for_all_roles(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code != 403


@pytest.mark.parametrize("role", [Role.ADMIN, Role.ATTORNEY, Role.INTAKE_COORDINATOR])
def test_export_allowed_for_roles_with_permission(
    db_session,
    rbac_world: RbacWorld,
    role: Role,
) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "L13")
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 200


def test_readonly_denied_export(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "L13")
    response = invoke_as(db_session, rbac_world.readonly, spec, rbac_world)
    assert response.status_code == 403
