"""403 violations: email routes (E1–E4, E6, L6) + assignee scope on send."""

from __future__ import annotations

import pytest

from src.core.permissions import Role
from tst.rbac.catalog import ROUTE_CATALOG
from tst.rbac.helpers import invoke_as
from tst.rbac.seed import RbacWorld, account_for_role

_EMAIL_ROUTES = tuple(
    s for s in ROUTE_CATALOG if s.entity == "email-notification" and s.denied_roles
)


def _denial_cases():
    for spec in _EMAIL_ROUTES:
        for role in spec.denied_roles:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-403")


@pytest.mark.parametrize(("spec", "role"), list(_denial_cases()))
def test_email_route_denied_for_role(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 403


def _email_allowed_cases():
    for spec in ROUTE_CATALOG:
        if spec.entity != "email-notification" or spec.denied_roles:
            continue
        for role in Role:
            yield pytest.param(spec, role, id=f"{spec.route_id}-{role.value}-allowed")


@pytest.mark.parametrize(("spec", "role"), list(_email_allowed_cases()))
def test_email_route_allowed_when_role_has_permission(
    db_session,
    rbac_world: RbacWorld,
    spec,
    role: Role,
) -> None:
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code != 403


@pytest.mark.parametrize("role", [Role.ADMIN, Role.ATTORNEY, Role.INTAKE_COORDINATOR])
def test_read_roles_can_list_lead_emails(
    db_session,
    rbac_world: RbacWorld,
    role: Role,
) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "L6")
    account = account_for_role(rbac_world, role)
    response = invoke_as(db_session, account, spec, rbac_world)
    assert response.status_code == 200


def test_readonly_can_list_email_templates(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "E6")
    response = invoke_as(db_session, rbac_world.readonly, spec, rbac_world)
    assert response.status_code == 200


def test_readonly_can_read_lead_emails(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "L6")
    response = invoke_as(db_session, rbac_world.readonly, spec, rbac_world)
    assert response.status_code == 200


def test_readonly_can_get_email_notification(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "E1")
    response = invoke_as(db_session, rbac_world.readonly, spec, rbac_world)
    assert response.status_code == 200


def test_readonly_denied_send_preview(db_session, rbac_world: RbacWorld) -> None:
    spec = next(s for s in ROUTE_CATALOG if s.route_id == "E2_PREVIEW")
    response = invoke_as(db_session, rbac_world.readonly, spec, rbac_world)
    assert response.status_code == 403
