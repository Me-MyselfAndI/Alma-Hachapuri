"""Tests for `src.core.permissions`.

Source of truth: docs/entities/permission.md. The expected matrix below is
duplicated from that doc on purpose — if the docs change, this test must
change with them so we never silently drift.
"""

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
            "assign_lead",
            "read_prospect",
            "send_email",
            "read_emails",
            "export_leads",
        }
    ),
    Role.READONLY: frozenset({"read_leads", "read_prospect", "read_emails"}),
}


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


def test_attorney_permissions_count() -> None:
    keys = permissions_for_role("attorney")
    assert keys == frozenset(
        {"read_leads", "write_lead", "send_email", "read_emails", "export_leads"}
    )
    assert len(keys) == 5


def test_permissions_for_role_accepts_enum_and_string() -> None:
    assert permissions_for_role(Role.READONLY) == permissions_for_role("readonly")


def test_permissions_for_role_unknown_returns_empty() -> None:
    assert permissions_for_role("nonexistent") == frozenset()


def test_account_has_permission_true_for_granted_key() -> None:
    account = SimpleNamespace(role="attorney")
    assert account_has_permission(account, "read_leads") is True


def test_account_has_permission_false_for_missing_key() -> None:
    account = SimpleNamespace(role="attorney")
    assert account_has_permission(account, "manage_users") is False


def test_account_has_permission_false_for_unknown_role() -> None:
    account = SimpleNamespace(role="ghost")
    assert account_has_permission(account, "read_leads") is False


def test_account_has_permission_false_for_none_account() -> None:
    assert account_has_permission(None, "read_leads") is False


def test_account_has_permission_accepts_role_enum_value() -> None:
    account = SimpleNamespace(role=Role.ADMIN.value)
    assert account_has_permission(account, "manage_users") is True
