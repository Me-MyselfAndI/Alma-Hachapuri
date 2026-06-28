import type { LeadState } from "@/lib/types";

/** Allowed next states per current state — must match API (plan §5.1). */
export const ALLOWED_TRANSITIONS: Record<LeadState, LeadState[]> = {
  PENDING: ["REACHED_OUT", "QUALIFIED", "DISQUALIFIED"],
  REACHED_OUT: ["PENDING", "QUALIFIED", "DISQUALIFIED"],
  QUALIFIED: ["CLOSED"],
  DISQUALIFIED: ["CLOSED"],
  CLOSED: [],
};

export const STATE_LABELS: Record<LeadState, string> = {
  PENDING: "Pending",
  REACHED_OUT: "Reached out",
  QUALIFIED: "Qualified",
  DISQUALIFIED: "Disqualified",
  CLOSED: "Closed",
};

export function getStateLabel(state: LeadState): string {
  return STATE_LABELS[state];
}

export function getTransitionButtonLabel(toState: LeadState): string {
  return STATE_LABELS[toState];
}

export function getAllowedTransitions(state: LeadState): LeadState[] {
  return ALLOWED_TRANSITIONS[state] ?? [];
}
