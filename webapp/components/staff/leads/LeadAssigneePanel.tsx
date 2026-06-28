"use client";

import { Check, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState, startTransition } from "react";

import type { AccountMe, AssignedAccountSummary, LeadRead } from "@/lib/types";
import { formatStaffApiError, staffFetch } from "@/lib/staff-api";
import { getPermissionMessage } from "@/lib/permission-messages";
import { cn } from "@/lib/utils";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type LeadAssigneePanelProps = {
  lead: LeadRead;
  user: AccountMe;
  onLeadUpdated: (lead: LeadRead) => void;
};

function assigneeLabel(account: AssignedAccountSummary): string {
  return `${account.first_name} ${account.last_name}`.trim();
}

function LoadingRows() {
  return (
    <>
      {Array.from({ length: 3 }).map((_, index) => (
        <TableRow key={index}>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-48" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

export function LeadAssigneePanel({
  lead,
  user,
  onLeadUpdated,
}: LeadAssigneePanelProps) {
  const canAssign = user.permissions.includes("assign_lead");

  const [assignees, setAssignees] = useState<AssignedAccountSummary[]>([]);
  const [loadingAssignees, setLoadingAssignees] = useState(true);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAssignees = useCallback(async () => {
    if (!canAssign) {
      setLoadingAssignees(false);
      return;
    }

    setLoadingAssignees(true);
    setError(null);

    const result = await staffFetch<AssignedAccountSummary[]>(
      "/api/v1/accounts/assignable",
    );

    setLoadingAssignees(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setAssignees(result.data);
  }, [canAssign]);

  useEffect(() => {
    startTransition(() => {
      void loadAssignees();
    });
  }, [loadAssignees]);

  const handleAssign = async (assigneeId: string) => {
    if (assigneeId === lead.assigned_account_id || assigningId) {
      return;
    }

    setAssigningId(assigneeId);
    setError(null);

    const result = await staffFetch<LeadRead>(`/api/v1/leads/${lead.id}`, {
      method: "PATCH",
      json: { assigned_account_id: assigneeId },
    });

    setAssigningId(null);

    if (!result.ok) {
      if (result.status === 403) {
        setError(getPermissionMessage("assign_lead"));
        return;
      }
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    onLeadUpdated(result.data);
  };

  if (!canAssign) {
    return null;
  }

  const currentName = lead.assigned_account
    ? assigneeLabel(lead.assigned_account)
    : "Unassigned";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reassign lead</CardTitle>
        <CardDescription>
          Current assignee: <strong>{currentName}</strong>. Click an attorney
          to assign this lead.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="surface-card overflow-hidden rounded-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-[100px]">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingAssignees ? (
                <LoadingRows />
              ) : assignees.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    className="py-8 text-center text-muted-foreground"
                  >
                    No assignable attorneys found.
                  </TableCell>
                </TableRow>
              ) : (
                assignees.map((assignee) => {
                  const isCurrent = assignee.id === lead.assigned_account_id;
                  const isAssigning = assigningId === assignee.id;

                  return (
                    <TableRow
                      key={assignee.id}
                      className={cn(
                        "transition-colors",
                        isCurrent
                          ? "bg-accent/40"
                          : "cursor-pointer hover:bg-accent/50",
                        assigningId !== null && !isAssigning && "opacity-60",
                      )}
                      tabIndex={isCurrent ? undefined : 0}
                      aria-current={isCurrent ? "true" : undefined}
                      onClick={() => {
                        if (!isCurrent && !assigningId) {
                          void handleAssign(assignee.id);
                        }
                      }}
                      onKeyDown={(event) => {
                        if (
                          !isCurrent &&
                          !assigningId &&
                          (event.key === "Enter" || event.key === " ")
                        ) {
                          event.preventDefault();
                          void handleAssign(assignee.id);
                        }
                      }}
                    >
                      <TableCell className="font-medium">
                        {assigneeLabel(assignee)}
                      </TableCell>
                      <TableCell>{assignee.email}</TableCell>
                      <TableCell>
                        {isAssigning ? (
                          <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
                            <Loader2 className="size-3.5 animate-spin" aria-hidden />
                            Assigning…
                          </span>
                        ) : isCurrent ? (
                          <Badge variant="secondary" className="gap-1">
                            <Check className="size-3" aria-hidden />
                            Current
                          </Badge>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
