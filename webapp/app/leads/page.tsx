import { Suspense } from "react";
import { Loader2 } from "lucide-react";

import { LeadListPage } from "@/components/staff/leads/LeadListPage";

function LeadsFallback() {
  return (
    <div className="flex min-h-48 items-center justify-center">
      <Loader2
        className="size-8 animate-spin text-muted-foreground"
        aria-label="Loading leads"
      />
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<LeadsFallback />}>
      <LeadListPage />
    </Suspense>
  );
}
