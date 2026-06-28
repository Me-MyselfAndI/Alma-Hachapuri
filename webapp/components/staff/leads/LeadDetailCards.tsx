import type { ReactNode } from "react";

import type { LeadRead } from "@/lib/types";
import { formatDate, formatFileSize } from "@/lib/format";

import { ResumeDownloadLink } from "@/components/staff/leads/ResumeDownloadLink";
import { LeadStateBadge } from "@/components/staff/leads/LeadStateBadge";
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

function formatCustomFields(
  customFields: Record<string, unknown> | null,
): ReactNode {
  if (!customFields || Object.keys(customFields).length === 0) {
    return "—";
  }

  return (
    <dl className="space-y-2">
      {Object.entries(customFields).map(([key, value]) => (
        <div key={key} className="grid gap-1 sm:grid-cols-[8rem_1fr] sm:gap-4">
          <dt className="font-medium text-muted-foreground">{key}</dt>
          <dd className="break-words">
            {typeof value === "string" || typeof value === "number"
              ? String(value)
              : JSON.stringify(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function LeadDetailCards({ lead }: LeadDetailCardsProps) {
  const fullName = `${lead.first_name} ${lead.last_name}`.trim();

  return (
    <div className="space-y-6">
      {lead.archived_at ? (
        <Alert>
          <AlertTitle>Archived</AlertTitle>
          <AlertDescription>
            This lead was archived on {formatDate(lead.archived_at)}.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Lead record</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow
              label="Lead ID"
              value={<span className="font-mono text-xs">{lead.id}</span>}
            />
            <DetailRow label="Name" value={fullName} />
            <DetailRow label="Email" value={lead.email} />
            <DetailRow
              label="Status"
              value={<LeadStateBadge state={lead.state} />}
            />
            <DetailRow
              label="Status since"
              value={formatDate(lead.state_changed_at)}
            />
            <DetailRow label="Source" value={lead.source ?? "—"} />
            <DetailRow label="Created" value={formatDate(lead.created_at)} />
            <DetailRow
              label="Last updated"
              value={formatDate(lead.updated_at)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Assignment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow label="Assignee" value={assigneeName(lead)} />
            <DetailRow
              label="Assignee ID"
              value={
                lead.assigned_account_id ? (
                  <span className="font-mono text-xs">
                    {lead.assigned_account_id}
                  </span>
                ) : (
                  "—"
                )
              }
            />
            {lead.assigned_account ? (
              <>
                <DetailRow
                  label="Assignee email"
                  value={lead.assigned_account.email}
                />
                <DetailRow
                  label="Work email"
                  value={lead.assigned_account.work_email ?? "—"}
                />
              </>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Prospect</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow
              label="Prospect ID"
              value={
                <span className="font-mono text-xs">{lead.prospect_id}</span>
              }
            />
            {lead.prospect ? (
              <>
                <DetailRow
                  label="Prospect name"
                  value={`${lead.prospect.first_name} ${lead.prospect.last_name}`.trim()}
                />
                <DetailRow label="Prospect email" value={lead.prospect.email} />
              </>
            ) : (
              <p className="text-muted-foreground">
                Prospect profile not loaded for this lead.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Custom fields</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {formatCustomFields(lead.custom_fields)}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Resume</CardTitle>
        </CardHeader>
        <CardContent>
          {lead.resume ? (
            <div className="space-y-3 text-sm">
              <DetailRow label="Filename" value={lead.resume.original_filename} />
              <DetailRow label="Type" value={lead.resume.mime_type} />
              <DetailRow
                label="Size"
                value={formatFileSize(lead.resume.size_bytes)}
              />
              <DetailRow
                label="File ID"
                value={
                  <span className="font-mono text-xs">{lead.resume.id}</span>
                }
              />
              <div className="pt-1">
                <ResumeDownloadLink leadId={lead.id} />
              </div>
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
