"use client";

import { useCallback, useEffect, useState, startTransition } from "react";

import type { LeadStateHistoryRead } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { getStateLabel } from "@/lib/lead-transitions";
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

type LeadStateHistoryPanelProps = {
  leadId: string;
  refreshKey?: string;
};

export function LeadStateHistoryPanel({
  leadId,
  refreshKey,
}: LeadStateHistoryPanelProps) {
  const [history, setHistory] = useState<LeadStateHistoryRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);

    const result = await staffFetch<LeadStateHistoryRead[]>(
      `/api/v1/leads/${leadId}/state-history`,
    );

    setLoading(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setHistory(result.data);
  }, [leadId]);

  useEffect(() => {
    startTransition(() => {
      void loadHistory();
    });
  }, [loadHistory, refreshKey]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status history</CardTitle>
        <CardDescription>
          Every status change recorded for this lead, oldest first.
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

        {!loading && !error && history.length === 0 ? (
          <p className="text-sm text-muted-foreground">No status history yet.</p>
        ) : null}

        {!loading && !error && history.length > 0 ? (
          <ol className="space-y-4">
            {history.map((entry) => (
              <li
                key={entry.id}
                className="rounded-lg border border-border px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium">
                    {entry.from_state
                      ? `${getStateLabel(entry.from_state)} → ${getStateLabel(entry.to_state)}`
                      : getStateLabel(entry.to_state)}
                  </p>
                  <time
                    className="text-xs text-muted-foreground"
                    dateTime={entry.created_at}
                  >
                    {formatDate(entry.created_at)}
                  </time>
                </div>
                {entry.changed_by_email ? (
                  <p className="mt-1 text-muted-foreground">
                    By {entry.changed_by_email}
                  </p>
                ) : null}
                {entry.note ? (
                  <p className="mt-2 whitespace-pre-wrap text-muted-foreground">
                    {entry.note}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        ) : null}
      </CardContent>
    </Card>
  );
}
