"""Ensure api/src/core/permissions.py stays aligned with docs/entities/permission.md."""

from __future__ import annotations

from src.core.permissions import ALL_PERMISSIONS, Role, permissions_for_role

# Copied from docs/entities/permission.md — role → permission keys table.
DOC_MATRIX: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "attorney": frozenset(
        {"read_leads", "write_lead", "send_email", "read_emails", "export_leads"}
    ),
    "intake_coordinator": frozenset(
        {
            "read_leads",
            "write_lead",
            "read_prospect",
            "send_email",
            "read_emails",
            "export_leads",
        }
    ),
    "readonly": frozenset({"read_leads", "read_prospect", "read_emails"}),
}


def test_code_matrix_matches_permission_md() -> None:
    for role in Role:
        assert permissions_for_role(role) == DOC_MATRIX[role.value]


def test_doc_assign_lead_is_admin_only() -> None:
    """assign_lead is in the key table but only granted to admin in v1."""
    assert "assign_lead" in permissions_for_role(Role.ADMIN)
    assert "assign_lead" not in permissions_for_role(Role.ATTORNEY)
    assert "assign_lead" not in permissions_for_role(Role.INTAKE_COORDINATOR)
    assert "assign_lead" not in permissions_for_role(Role.READONLY)
