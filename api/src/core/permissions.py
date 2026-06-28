"""Role enum, permission keys, and ROLE_PERMISSIONS matrix.

Spec: docs/entities/role.md, docs/entities/permission.md

Single source of truth for authorization in v1. No `roles`, `permissions`, or
`role_permissions` DB tables — everything lives here as code constants. The
matrix below mirrors permission.md exactly; if you change one, change the
other.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Role(str, Enum):
    """Account role enum (stored as VARCHAR on `accounts.role`, immutable)."""

    ADMIN = "admin"
    ATTORNEY = "attorney"
    INTAKE_COORDINATOR = "intake_coordinator"
    READONLY = "readonly"


class Permission(str, Enum):
    """Capability keys checked by `require_permission(...)`."""

    READ_LEADS = "read_leads"
    WRITE_LEAD = "write_lead"
    ASSIGN_LEAD = "assign_lead"
    READ_PROSPECT = "read_prospect"
    MANAGE_USERS = "manage_users"
    SEND_EMAIL = "send_email"
    READ_EMAILS = "read_emails"
    EXPORT_LEADS = "export_leads"


ALL_PERMISSIONS: frozenset[str] = frozenset(p.value for p in Permission)


ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.ADMIN: ALL_PERMISSIONS,
    Role.ATTORNEY: frozenset(
        {
            Permission.READ_LEADS.value,
            Permission.WRITE_LEAD.value,
            Permission.SEND_EMAIL.value,
            Permission.READ_EMAILS.value,
            Permission.EXPORT_LEADS.value,
        }
    ),
    Role.INTAKE_COORDINATOR: frozenset(
        {
            Permission.READ_LEADS.value,
            Permission.WRITE_LEAD.value,
            Permission.ASSIGN_LEAD.value,
            Permission.READ_PROSPECT.value,
            Permission.SEND_EMAIL.value,
            Permission.READ_EMAILS.value,
            Permission.EXPORT_LEADS.value,
        }
    ),
    Role.READONLY: frozenset(
        {
            Permission.READ_LEADS.value,
            Permission.READ_PROSPECT.value,
            Permission.READ_EMAILS.value,
        }
    ),
}


def permissions_for_role(role: Role | str) -> frozenset[str]:
    """Return the permission keys granted to `role`.

    Accepts a `Role` enum or its string value. Unknown roles get an empty set
    rather than raising — callers express authorization via membership checks,
    and an unknown role simply has no permissions.
    """

    if isinstance(role, Role):
        return ROLE_PERMISSIONS[role]
    try:
        return ROLE_PERMISSIONS[Role(role)]
    except ValueError:
        return frozenset()


def account_has_permission(account: Any, key: str) -> bool:
    """Return True if `account.role` grants `key`.

    `account` is typed loosely (`Any`) so that mocked test doubles and the
    real `Account` ORM model both work without importing the model here
    (keeps `permissions.py` free of DB imports).
    """

    if account is None:
        return False
    role = getattr(account, "role", None)
    if role is None:
        return False
    return key in permissions_for_role(role)
