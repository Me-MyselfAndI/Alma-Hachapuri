"use client";

import { useCallback, useEffect, useState, startTransition } from "react";

import type { AccountMe, EmailNotificationRead } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { getPermissionMessage } from "@/lib/permission-messages";
import { formatStaffApiError, staffFetch } from "@/lib/staff-api";

import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const TEMPLATE_LABELS: Record<string, string> = {
  prospect_confirmation: "Submission confirmation",
  prospect_follow_up: "Follow-up to prospect",
  attorney_new_lead: "New lead (attorney)",
  email_verification: "Email verification",
};

type LeadEmailLogPanelProps = {
  leadId: string;
  user: AccountMe;
};

export function LeadEmailLogPanel({ leadId, user }: LeadEmailLogPanelProps) {
  const canRead = user.permissions.includes("read_emails");
  const [emails, setEmails] = useState<EmailNotificationRead[]>([]);
  const [loading, setLoading] = useState(canRead);
  const [error, setError] = useState<string | null>(null);

  const loadEmails = useCallback(async () => {
    if (!canRead) {
      return;
    }

    setLoading(true);
    setError(null);

    const result = await staffFetch<EmailNotificationRead[]>(
      `/api/v1/leads/${leadId}/emails`,
    );

    setLoading(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setEmails(result.data);
  }, [canRead, leadId]);

  useEffect(() => {
    startTransition(() => {
      void loadEmails();
    });
  }, [loadEmails]);

  if (!canRead) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Email log</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {getPermissionMessage("read_emails")}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Email log</CardTitle>
        <CardDescription>
          Outbound messages tied to this lead, newest first.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : null}

        {!loading && error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {!loading && !error && emails.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No emails have been sent for this lead yet.
          </p>
        ) : null}

        {!loading && !error && emails.length > 0 ? (
          <ul className="space-y-3">
            {[...emails].reverse().map((email) => (
              <li
                key={email.id}
                className="rounded-lg border border-border px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium">{email.subject}</p>
                  <time
                    className="text-xs text-muted-foreground"
                    dateTime={email.sent_at ?? email.created_at}
                  >
                    {formatDate(email.sent_at ?? email.created_at)}
                  </time>
                </div>
                <p className="mt-1 text-muted-foreground">
                  To {email.recipient} ·{" "}
                  {TEMPLATE_LABELS[email.template] ?? email.template} ·{" "}
                  {email.status}
                </p>
                {email.error_message ? (
                  <p className="mt-2 text-destructive">{email.error_message}</p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
