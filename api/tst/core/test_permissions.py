"""Expanded permission matrix tests — docs/entities/permission.md."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    Permission,
    Role,
    account_has_permission,
    permissions_for_role,
)

EXPECTED_MATRIX: dict[Role, frozenset[str]] = {
    Role.ADMIN: frozenset(
        {
            "read_leads",
            "write_lead",
            "assign_lead",
            "read_prospect",
            "manage_users",
            "send_email",
            "read_emails",
            "export_leads",
        }
    ),
    Role.ATTORNEY: frozenset(
        {"read_leads", "write_lead", "send_email", "read_emails", "export_leads"}
    ),
    Role.INTAKE_COORDINATOR: frozenset(
        {
            "read_leads",
            "write_lead",
            "read_prospect",
            "send_email",
            "read_emails",
            "export_leads",
        }
    ),
    Role.READONLY: frozenset({"read_leads", "read_prospect", "read_emails"}),
}

# Keys that must never appear on non-admin staff roles in v1.
ADMIN_ONLY_KEYS = frozenset({"manage_users", "assign_lead"})


def test_all_permissions_contains_eight_keys() -> None:
    assert len(ALL_PERMISSIONS) == 8
    assert ALL_PERMISSIONS == frozenset(EXPECTED_MATRIX[Role.ADMIN])


def test_permission_enum_values_are_unique() -> None:
    values = [p.value for p in Permission]
    assert len(values) == len(set(values))


def test_every_role_has_an_entry() -> None:
    assert set(ROLE_PERMISSIONS.keys()) == set(Role)


def test_admin_has_all_permissions() -> None:
    assert ROLE_PERMISSIONS[Role.ADMIN] == ALL_PERMISSIONS


@pytest.mark.parametrize("role", list(Role))
def test_role_matrix_matches_permission_md(role: Role) -> None:
    assert ROLE_PERMISSIONS[role] == EXPECTED_MATRIX[role]


@pytest.mark.parametrize("role", [Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY])
def test_non_admin_roles_lack_manage_users(role: Role) -> None:
    assert "manage_users" not in permissions_for_role(role)


@pytest.mark.parametrize("role", [Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY])
def test_non_admin_roles_lack_assign_lead(role: Role) -> None:
    assert "assign_lead" not in permissions_for_role(role)


@pytest.mark.parametrize("role", [Role.ATTORNEY])
def test_attorney_lacks_read_prospect(role: Role) -> None:
    assert "read_prospect" not in permissions_for_role(role)


def test_readonly_has_read_prospect() -> None:
    assert "read_prospect" in permissions_for_role(Role.READONLY)


def test_attorney_permissions_count() -> None:
    keys = permissions_for_role("attorney")
    assert keys == frozenset(
        {"read_leads", "write_lead", "send_email", "read_emails", "export_leads"}
    )
    assert len(keys) == 5


def test_intake_has_six_permissions() -> None:
    assert len(permissions_for_role(Role.INTAKE_COORDINATOR)) == 6


def test_readonly_has_three_permissions() -> None:
    assert len(permissions_for_role(Role.READONLY)) == 3


def test_permissions_for_role_accepts_enum_and_string() -> None:
    assert permissions_for_role(Role.READONLY) == permissions_for_role("readonly")


def test_permissions_for_role_unknown_returns_empty() -> None:
    assert permissions_for_role("nonexistent") == frozenset()


@pytest.mark.parametrize(
    ("role", "key", "expected"),
    [
        (Role.ATTORNEY, "read_leads", True),
        (Role.ATTORNEY, "manage_users", False),
        (Role.ATTORNEY, "assign_lead", False),
        (Role.ADMIN, "manage_users", True),
        (Role.ADMIN, "assign_lead", True),
        (Role.INTAKE_COORDINATOR, "read_prospect", True),
        (Role.INTAKE_COORDINATOR, "assign_lead", False),
        (Role.READONLY, "write_lead", False),
        (Role.READONLY, "read_leads", True),
    ],
)
def test_account_has_permission_matrix(role: Role, key: str, expected: bool) -> None:
    account = SimpleNamespace(role=role.value)
    assert account_has_permission(account, key) is expected


def test_account_has_permission_false_for_none_account() -> None:
    assert account_has_permission(None, "read_leads") is False


def test_account_has_permission_false_for_unknown_role() -> None:
    account = SimpleNamespace(role="ghost")
    assert account_has_permission(account, "read_leads") is False


def test_admin_only_keys_disjoint_from_attorney() -> None:
    attorney = permissions_for_role(Role.ATTORNEY)
    assert attorney.isdisjoint(ADMIN_ONLY_KEYS)


def test_matrix_keys_are_valid_permission_enum_values() -> None:
    valid = {p.value for p in Permission}
    for role in Role:
        assert permissions_for_role(role).issubset(valid)
