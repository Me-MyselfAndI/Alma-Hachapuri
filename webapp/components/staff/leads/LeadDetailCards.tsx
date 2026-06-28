import type { ReactNode } from "react";

import type { LeadRead } from "@/lib/types";
import { formatFileSize } from "@/lib/format";

import { ResumeDownloadLink } from "@/components/staff/leads/ResumeDownloadLink";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type LeadDetailCardsProps = {
  lead: LeadRead;
};

function assigneeName(lead: LeadRead): string {
  if (lead.assigned_account) {
    return `${lead.assigned_account.first_name} ${lead.assigned_account.last_name}`.trim();
  }
  return "—";
}

export function LeadDetailCards({ lead }: LeadDetailCardsProps) {
  return (
    <div className="space-y-4">
      {lead.archived_at ? (
        <Alert>
          <AlertTitle>Archived</AlertTitle>
          <AlertDescription>
            This lead was archived on {new Date(lead.archived_at).toLocaleString()}.
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <DetailRow label="Assignee" value={assigneeName(lead)} />
          <DetailRow label="Source" value={lead.source ?? "—"} />
          <DetailRow
            label="Prospect ID"
            value={
              <span className="font-mono text-xs">{lead.prospect_id}</span>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Resume</CardTitle>
        </CardHeader>
        <CardContent>
          {lead.resume ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                {lead.resume.original_filename} ·{" "}
                {formatFileSize(lead.resume.size_bytes)}
              </p>
              <ResumeDownloadLink leadId={lead.id} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No resume attached.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="grid gap-1 sm:grid-cols-[8rem_1fr] sm:gap-4">
      <span className="font-medium text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}
