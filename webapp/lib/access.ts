import type { AccountMe } from "@/lib/types";

export function hasPermission(user: AccountMe, key: string): boolean {
  return user.permissions.includes(key);
}

/** Admin UI (nav + /admin routes). Requires `manage_users`. */
export function canAccessAdmin(user: AccountMe): boolean {
  return hasPermission(user, "manage_users");
}

/** Reassign-lead panel on lead detail. Requires `assign_lead`. */
export function canReassignLeads(user: AccountMe): boolean {
  return hasPermission(user, "assign_lead");
}

type LeadAssigneeRef = { assigned_account_id: string | null };

/** Attorneys may only mutate or send email on leads assigned to them (F6.2). */
export function canWriteLeadScope(user: AccountMe, lead: LeadAssigneeRef): boolean {
  if (user.role !== "attorney") {
    return true;
  }
  return lead.assigned_account_id === user.id;
}

type JwtPayload = {
  role?: string;
  permissions?: string[];
};

/** Decode JWT payload for middleware routing (API still enforces auth). */
export function parseJwtPayload(token: string): JwtPayload | null {
  const segments = token.split(".");
  if (segments.length !== 3) {
    return null;
  }

  try {
    const base64 = segments[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    const json = atob(padded);
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

export function tokenHasPermission(token: string, permission: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload?.permissions) {
    return false;
  }
  return payload.permissions.includes(permission);
}

export function roleLabel(role: AccountMe["role"]): string {
  switch (role) {
    case "admin":
      return "Admin";
    case "attorney":
      return "Attorney";
    case "intake_coordinator":
      return "Intake coordinator";
    case "readonly":
      return "Read-only";
    default:
      return role;
  }
}
