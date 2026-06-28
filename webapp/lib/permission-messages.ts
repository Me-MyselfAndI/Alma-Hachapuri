import type { AccountMe, LeadRead } from "@/lib/types";

export type PermissionKey =
  | "read_leads"
  | "write_lead"
  | "assign_lead"
  | "read_prospect"
  | "send_email"
  | "read_emails"
  | "export_leads"
  | "manage_users";

const PERMISSION_MESSAGES: Record<PermissionKey, string> = {
  read_leads:
    "You don't have permission to view leads. Your role needs the read leads capability.",
  write_lead:
    "You don't have permission to update this lead. Your role needs write lead access.",
  assign_lead:
    "You can't change assignment. Your role needs assign lead access.",
  read_prospect:
    "You can't view prospect details. Your role needs read prospect access.",
  send_email:
    "You can't send email from here. Your role needs send email access.",
  read_emails:
    "You can't view the email log. Your role needs read emails access.",
  export_leads:
    "You can't export leads. Your role needs export leads access.",
  manage_users:
    "You can't manage accounts. Your role needs manage users access.",
};

export function getPermissionMessage(key: PermissionKey): string {
  return PERMISSION_MESSAGES[key];
}

const ATTORNEY_SCOPE_MESSAGE =
  "You can only update leads assigned to you.";

export function getTransitionForbiddenMessage(
  user: AccountMe,
  lead: LeadRead,
): string {
  if (
    user.role === "attorney" &&
    lead.assigned_account_id !== null &&
    lead.assigned_account_id !== user.id
  ) {
    return ATTORNEY_SCOPE_MESSAGE;
  }
  return getPermissionMessage("write_lead");
}
