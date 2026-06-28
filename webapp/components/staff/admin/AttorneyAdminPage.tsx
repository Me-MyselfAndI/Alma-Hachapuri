import {
  ATTORNEY_ADMIN_CONFIG,
  StaffAccountsAdminPage,
} from "@/components/staff/admin/StaffAccountsAdminPage";

export function AttorneyAdminPage() {
  return <StaffAccountsAdminPage key="attorney" config={ATTORNEY_ADMIN_CONFIG} />;
}
