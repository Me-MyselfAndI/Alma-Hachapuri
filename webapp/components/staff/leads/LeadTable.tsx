import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import type { LeadListItem } from "@/lib/types";

import { LeadTableRow } from "./LeadTableRow";

type LeadTableProps = {
  items: LeadListItem[];
  loading: boolean;
};

function LoadingRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, index) => (
        <TableRow key={index}>
          {Array.from({ length: 6 }).map((__, cellIndex) => (
            <TableCell key={cellIndex}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export function LeadTable({ items, loading }: LeadTableProps) {
  return (
    <div className="surface-card overflow-hidden rounded-xl">
      <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>State</TableHead>
          <TableHead>Assignee</TableHead>
          <TableHead>Submitted</TableHead>
          <TableHead>Waiting since</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          <LoadingRows />
        ) : (
          items.map((lead) => <LeadTableRow key={lead.id} lead={lead} />)
        )}
      </TableBody>
    </Table>
    </div>
  );
}
