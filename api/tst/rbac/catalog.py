"""Access-control catalog — maps API route IDs to permission rules.

Source of truth for RBAC tests: docs/entities/API_CATALOG.md + permission.md.
Each ``RouteSpec`` lists roles that must receive 403 when calling the route
(without assignee-scope nuance — scope violations live in test_lead_write_scope).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.core.permissions import Role

# Roles that have every permission key (including assign_lead, manage_users).
ALL_STAFF = frozenset({Role.ADMIN, Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY})


@dataclass(frozen=True)
class RouteSpec:
    route_id: str
    method: str
    """Path template; use ``format_path`` for ``{lead_id}`` placeholders."""
    path: str
    entity: str
    permission: str | None = None
    any_of_permissions: frozenset[str] = frozenset()
    denied_roles: frozenset[Role] = frozenset()
    attorney_assignee_scope: bool = False
    needs_auth: bool = True
    public: bool = False

    def format_path(self, **kwargs: str) -> str:
        return self.path.format(**kwargs)


def _denied(*roles: Role) -> frozenset[Role]:
    return frozenset(roles)


# ---------------------------------------------------------------------------
# Protected routes — permission matrix violations (403)
# ---------------------------------------------------------------------------

ROUTE_CATALOG: tuple[RouteSpec, ...] = (
    # --- Account (account.md) ---
    RouteSpec("A2", "GET", "/api/v1/auth/me", "account", denied_roles=frozenset()),
    RouteSpec("A3", "POST", "/api/v1/accounts", "account", permission="manage_users",
              denied_roles=_denied(Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY)),
    RouteSpec("A4", "GET", "/api/v1/accounts", "account", permission="manage_users",
              denied_roles=_denied(Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY)),
    RouteSpec("A4_ASSIGN", "GET", "/api/v1/accounts?for_assignment=true", "account",
              permission="assign_lead",
              denied_roles=_denied(Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY)),
    RouteSpec("A5", "GET", "/api/v1/accounts/{account_id}", "account", permission="manage_users",
              denied_roles=_denied(Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY)),
    RouteSpec("A6", "PATCH", "/api/v1/accounts/{account_id}", "account", permission="manage_users",
              denied_roles=_denied(Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY)),
    # --- Lead read (lead.md) ---
    RouteSpec("L2", "GET", "/api/v1/leads", "lead", permission="read_leads", denied_roles=frozenset()),
    RouteSpec("L3", "GET", "/api/v1/leads/{lead_id}", "lead", permission="read_leads", denied_roles=frozenset()),
    RouteSpec("L5", "GET", "/api/v1/leads/{lead_id}/resume", "resume-file", permission="read_leads",
              denied_roles=frozenset()),
    RouteSpec("L7", "GET", "/api/v1/leads/{lead_id}/state-history", "lead-state-history",
              permission="read_leads", denied_roles=frozenset()),
    # --- Lead write (lead.md) — permission only; assignee scope tested separately ---
    RouteSpec("L4", "PATCH", "/api/v1/leads/{lead_id}", "lead", permission="write_lead",
              denied_roles=_denied(Role.READONLY), attorney_assignee_scope=True),
    RouteSpec("L10", "POST", "/api/v1/leads/{lead_id}/transitions", "lead", permission="write_lead",
              denied_roles=_denied(Role.READONLY), attorney_assignee_scope=True),
    RouteSpec("L14", "DELETE", "/api/v1/leads/{lead_id}", "lead", permission="write_lead",
              denied_roles=_denied(Role.READONLY), attorney_assignee_scope=True),
    RouteSpec("L13", "GET", "/api/v1/leads/export", "lead", permission="export_leads",
              denied_roles=_denied(Role.READONLY)),
    # --- Prospect (prospect.md) ---
    RouteSpec("P1", "GET", "/api/v1/prospects/{prospect_id}", "prospect", permission="read_prospect",
              denied_roles=_denied(Role.ATTORNEY)),
    RouteSpec("P2", "GET", "/api/v1/prospects/{prospect_id}/leads", "prospect", permission="read_prospect",
              denied_roles=_denied(Role.ATTORNEY)),
    # --- Email (email-notification.md) ---
    RouteSpec("L6", "GET", "/api/v1/leads/{lead_id}/emails", "email-notification",
              permission="read_emails", denied_roles=frozenset()),
    RouteSpec("E1", "GET", "/api/v1/emails/{email_id}", "email-notification",
              permission="read_emails", denied_roles=frozenset()),
    RouteSpec("E2", "POST", "/api/v1/leads/{lead_id}/emails", "email-notification",
              permission="send_email", denied_roles=_denied(Role.READONLY),
              attorney_assignee_scope=True),
    RouteSpec("E2_PREVIEW", "POST", "/api/v1/leads/{lead_id}/emails/preview", "email-notification",
              permission="send_email", denied_roles=_denied(Role.READONLY),
              attorney_assignee_scope=True),
    RouteSpec("E3", "POST", "/api/v1/emails/{email_id}/retry", "email-notification",
              permission="send_email", denied_roles=_denied(Role.READONLY),
              attorney_assignee_scope=True),
    RouteSpec("E4", "GET", "/api/v1/emails", "email-notification",
              any_of_permissions=frozenset({"read_emails", "manage_users"}),
              denied_roles=frozenset()),
    RouteSpec("E6", "GET", "/api/v1/emails/templates", "email-notification",
              any_of_permissions=frozenset({"send_email", "read_emails"}),
              denied_roles=frozenset()),
)

ROUTES_BY_ENTITY: dict[str, tuple[RouteSpec, ...]] = {}
for _spec in ROUTE_CATALOG:
    ROUTES_BY_ENTITY.setdefault(_spec.entity, (*ROUTES_BY_ENTITY.get(_spec.entity, ()), _spec))

# Public routes — must NOT require auth (no 401 for missing token on happy path).
PUBLIC_ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec("A1", "POST", "/api/v1/auth/token", "account", public=True, needs_auth=False),
    RouteSpec("L1a", "POST", "/api/v1/leads/verification-requests", "lead", public=True, needs_auth=False),
    RouteSpec("L1b_GET", "GET", "/api/v1/leads/verify", "lead", public=True, needs_auth=False),
    RouteSpec("L1b_POST", "POST", "/api/v1/leads/verify", "lead", public=True, needs_auth=False),
)

# Every protected route that must 401 without a token.
PROTECTED_FOR_UNAUTH: tuple[RouteSpec, ...] = ROUTE_CATALOG

# Assignee-scope routes: attorney blocked when lead assigned to someone else.
ASSIGNEE_SCOPED_ROUTES: tuple[RouteSpec, ...] = tuple(
    s for s in ROUTE_CATALOG if s.attorney_assignee_scope
)

# Special violation: assign_lead required for reassignment body field.
L4_REASSIGN_DENIED: frozenset[Role] = frozenset(
    {Role.ATTORNEY, Role.INTAKE_COORDINATOR, Role.READONLY}
)

RequestBuilder = Callable[..., tuple[str, dict | None, dict | None]]
