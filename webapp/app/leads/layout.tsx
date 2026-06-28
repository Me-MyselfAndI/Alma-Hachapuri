import { Suspense } from "react";
import { Loader2 } from "lucide-react";

import { SessionProvider } from "@/components/auth/SessionProvider";
import { StaffShell } from "@/components/staff/shell/StaffShell";

function SessionFallback() {
  return (
    <div className="flex min-h-full items-center justify-center">
      <Loader2
        className="size-8 animate-spin text-muted-foreground"
        aria-label="Loading"
      />
    </div>
  );
}

export default function LeadsLayout({
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
