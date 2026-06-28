import {
  INTAKE_COORDINATOR_ADMIN_CONFIG,
  StaffAccountsAdminPage,
} from "@/components/staff/admin/StaffAccountsAdminPage";

export function IntakeCoordinatorAdminPage() {
  return (
    <StaffAccountsAdminPage
      key="intake_coordinator"
      config={INTAKE_COORDINATOR_ADMIN_CONFIG}
    />
  );
}
