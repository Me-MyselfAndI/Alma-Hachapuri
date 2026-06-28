"""Read routes without assignee scope: resume (L5), state history (L7)."""

from __future__ import annotations

import pytest

from src.core.permissions import Role
from tst.rbac.catalog import ROUTE_CATALOG
from tst.rbac.helpers import invoke_as
from tst.rbac.seed import RbacWorld, account_for_role

_READ_ROUTES = tuple(
    s
    for s in ROUTE_CATALOG
    if s.route_id in ("L5", "L7")
)


@pytest.mark.parametrize("spec", _READ_ROUTES, ids=lambda s: s.route_id)
@pytest.mark.parametrize("role", list(Role))
def test_read_subroute_allowed_for_all_staff_roles(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    # L5 may 404 if storage file missing — still must not be 403.
    assert response.status_code != 403


def test_attorney_can_read_other_attorneys_lead_history(
    db_session,
    rbac_world: RbacWorld,
) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "L7")
    response = invoke_as(db_session, rbac_world.other_attorney, spec, rbac_world)
    assert response.status_code == 200
