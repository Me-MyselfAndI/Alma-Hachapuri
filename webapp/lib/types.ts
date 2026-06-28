/** Types mirroring api/src/domains account and lead schemas. */

export type Role =
  | "admin"
  | "attorney"
  | "intake_coordinator"
  | "readonly";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AccountMe {
  id: string;
  email: string;
  role: Role;
  first_name: string;
  last_name: string;
  work_email: string | null;
  is_default_assignee: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  permissions: string[];
}

export type LeadState =
  | "PENDING"
  | "REACHED_OUT"
  | "QUALIFIED"
  | "DISQUALIFIED"
  | "CLOSED";

export interface LeadVerificationRequestResponse {
  message: string;
  email: string;
}

export interface LeadVerifyRequest {
  token: string;
}

export interface LeadCreateResponse {
  id: string;
  state: LeadState;
  message: string;
}

export interface LeadListItem {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  state: LeadState;
  state_changed_at: string;
  source: string | null;
  assigned_account_id: string | null;
  assigned_account_name: string | null;
  archived_at: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssignedAccountSummary {
  id: string;
  first_name: string;
  last_name: string;
  work_email: string | null;
  email: string;
}

export interface LeadResumeSummary {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  download_url: string;
}

export interface ProspectSummary {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface LeadRead {
  id: string;
  prospect_id: string;
  first_name: string;
  last_name: string;
  email: string;
  state: LeadState;
  state_changed_at: string;
  source: string | null;
  custom_fields: Record<string, unknown> | null;
  assigned_account_id: string | null;
  assigned_account: AssignedAccountSummary | null;
  resume: LeadResumeSummary | null;
  prospect: ProspectSummary | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadStateHistoryRead {
  id: string;
  lead_id: string;
  from_state: LeadState | null;
  to_state: LeadState;
  changed_by_account_id: string | null;
  changed_by_email: string | null;
  note: string | null;
  created_at: string;
}

export interface EmailNotificationRead {
  id: string;
  lead_id: string | null;
  conversation_id: string;
  recipient: string;
  template: string;
  subject: string;
  status: string;
  error_message: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface AccountRead {
  id: string;
  email: string;
  role: Role;
  first_name: string;
  last_name: string;
  work_email: string | null;
  is_default_assignee: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  email: string;
  password: string;
  role: Role;
  first_name: string;
  last_name: string;
  work_email?: string | null;
  is_default_assignee?: boolean;
}

export interface AccountUpdate {
  is_active?: boolean;
  password?: string;
  first_name?: string;
  last_name?: string;
  work_email?: string | null;
  is_default_assignee?: boolean;
}
