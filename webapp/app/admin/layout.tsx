import { Suspense } from "react";

import { SessionProvider } from "@/components/auth/SessionProvider";
import { StaffShell } from "@/components/staff/shell/StaffShell";
import { PageLoader } from "@/components/ui/page-loader";

function SessionFallback() {
  return <PageLoader label="Loading admin…" fullScreen />;
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<SessionFallback />}>
      <SessionProvider>
        <StaffShell>{children}</StaffShell>
      </SessionProvider>
    </Suspense>
  );
}
