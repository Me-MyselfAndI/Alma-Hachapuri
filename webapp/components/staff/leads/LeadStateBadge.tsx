import { Badge } from "@/components/ui/badge";
import type { LeadState } from "@/lib/types";

const STATE_CONFIG: Record<
  LeadState,
  { label: string; variant: "warning" | "secondary" | "success" | "outline" | "muted" }
> = {
  PENDING: { label: "Pending", variant: "warning" },
  REACHED_OUT: { label: "Reached out", variant: "secondary" },
  QUALIFIED: { label: "Qualified", variant: "success" },
  DISQUALIFIED: { label: "Disqualified", variant: "outline" },
  CLOSED: { label: "Closed", variant: "muted" },
};

export function LeadStateBadge({ state }: { state: LeadState }) {
  const config = STATE_CONFIG[state];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export const LEAD_STATE_OPTIONS: { value: LeadState; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "REACHED_OUT", label: "Reached out" },
  { value: "QUALIFIED", label: "Qualified" },
  { value: "DISQUALIFIED", label: "Disqualified" },
  { value: "CLOSED", label: "Closed" },
];
