import type { LeadRead } from "@/lib/types";
import { formatDate, formatRelativeTime } from "@/lib/format";

import { LeadStateBadge } from "@/components/staff/leads/LeadStateBadge";

type LeadDetailHeaderProps = {
  lead: LeadRead;
};

export function LeadDetailHeader({ lead }: LeadDetailHeaderProps) {
  const fullName = `${lead.first_name} ${lead.last_name}`.trim();

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{fullName}</h1>
        <LeadStateBadge state={lead.state} />
      </div>
      <p className="text-muted-foreground">{lead.email}</p>
      <p className="text-sm text-muted-foreground">
        Submitted {formatDate(lead.created_at)} · Waiting since{" "}
        {formatRelativeTime(lead.state_changed_at)}
      </p>
    </div>
  );
}
