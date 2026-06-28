"""Meta-tests: catalog coverage and permission-doc alignment."""

from __future__ import annotations

import pytest

from src.core.permissions import Role, account_has_permission, permissions_for_role
from tst.rbac.catalog import PROTECTED_FOR_UNAUTH, ROUTE_CATALOG


def test_every_denied_role_lacks_required_permission() -> None:
    for spec in ROUTE_CATALOG:
        if not spec.denied_roles:
            continue
        if spec.permission:
            for role in spec.denied_roles:
                assert not account_has_permission(
                    type("A", (), {"role": role.value})(),
                    spec.permission,
                ), f"{spec.route_id}: {role.value} should lack {spec.permission}"
        if spec.any_of_permissions:
            for role in spec.denied_roles:
                perms = permissions_for_role(role)
                assert perms.isdisjoint(spec.any_of_permissions), (
                    f"{spec.route_id}: {role.value} should lack all of {spec.any_of_permissions}"
                )


def test_catalog_route_ids_unique() -> None:
    ids = [s.route_id for s in ROUTE_CATALOG]
    assert len(ids) == len(set(ids)), f"duplicate route ids: {ids}"


def test_protected_route_count_matches_api_catalog_minimum() -> None:
    """Sanity: we test at least 20 protected actions from API_CATALOG."""
    assert len(PROTECTED_FOR_UNAUTH) >= 20


@pytest.mark.parametrize("role", list(Role))
def test_admin_only_keys_not_on_staff_roles(role: Role) -> None:
    perms = permissions_for_role(role)
    if role == Role.ADMIN:
        assert "manage_users" in perms
        assert "assign_lead" in perms
    else:
        assert "manage_users" not in perms
        assert "assign_lead" not in perms
