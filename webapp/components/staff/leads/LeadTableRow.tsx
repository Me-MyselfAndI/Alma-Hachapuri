"use client";

import { useRouter } from "next/navigation";

import {
  TableCell,
  TableRow,
} from "@/components/ui/table";
import { formatLocaleDate, formatRelativeTime } from "@/lib/format-date";
import type { LeadListItem } from "@/lib/types";

import { LeadStateBadge } from "./LeadStateBadge";

type LeadTableRowProps = {
  lead: LeadListItem;
};

export function LeadTableRow({ lead }: LeadTableRowProps) {
  const router = useRouter();
  const fullName = `${lead.first_name} ${lead.last_name}`.trim();

  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => router.push(`/leads/${lead.id}`)}
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          router.push(`/leads/${lead.id}`);
        }
      }}
    >
      <TableCell className="font-medium">{fullName}</TableCell>
      <TableCell className="max-w-[200px] truncate" title={lead.email}>
        {lead.email}
      </TableCell>
      <TableCell>
        <LeadStateBadge state={lead.state} />
      </TableCell>
      <TableCell>{lead.assigned_account_name ?? "—"}</TableCell>
      <TableCell>{formatLocaleDate(lead.created_at)}</TableCell>
      <TableCell>{formatRelativeTime(lead.state_changed_at)}</TableCell>
    </TableRow>
  );
}
