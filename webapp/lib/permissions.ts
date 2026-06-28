/**
 * Expected permission keys per role — must match docs/entities/permission.md
 * and api/src/core/permissions.py ROLE_PERMISSIONS.
 *
 * Used for optional dev-time checks only; the API is the source of truth at runtime.
 */

import type { Role } from "@/lib/types";

export const ROLE_PERMISSIONS: Record<Role, readonly string[]> = {
  admin: [
    "assign_lead",
    "export_leads",
    "manage_users",
    "read_emails",
    "read_leads",
    "read_prospect",
    "send_email",
    "write_lead",
  ],
  attorney: [
    "export_leads",
    "read_emails",
    "read_leads",
    "send_email",
    "write_lead",
  ],
  intake_coordinator: [
    "export_leads",
    "read_emails",
    "read_leads",
    "read_prospect",
    "send_email",
    "write_lead",
  ],
  readonly: ["read_emails", "read_leads", "read_prospect"],
};

export function expectedPermissionsForRole(role: Role): string[] {
  return [...ROLE_PERMISSIONS[role]].sort();
}
