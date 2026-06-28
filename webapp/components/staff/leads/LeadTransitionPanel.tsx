"use client";

import { Loader2 } from "lucide-react";

import type { LeadRead, LeadState } from "@/lib/types";
import {
  getAllowedTransitions,
  getTransitionButtonLabel,
} from "@/lib/lead-transitions";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type LeadTransitionPanelProps = {
  lead: LeadRead;
  note: string;
  onNoteChange: (value: string) => void;
  onTransition: (toState: LeadState) => void;
  transitioningTo: LeadState | null;
  error: string | null;
};

export function LeadTransitionPanel({
  lead,
  note,
  onNoteChange,
  onTransition,
  transitioningTo,
  error,
}: LeadTransitionPanelProps) {
  const allowed = getAllowedTransitions(lead.state);

  if (allowed.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Update status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {allowed.map((toState) => {
            const isLoading = transitioningTo === toState;
            return (
              <Button
                key={toState}
                type="button"
                variant="outline"
                disabled={transitioningTo !== null}
                onClick={() => onTransition(toState)}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden />
                    Updating…
                  </>
                ) : (
                  getTransitionButtonLabel(toState)
                )}
              </Button>
            );
          })}
        </div>

        <div className="space-y-2">
          <label
            htmlFor="transition-note"
            className="text-sm font-medium text-muted-foreground"
          >
            Optional note
          </label>
          <Textarea
            id="transition-note"
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            placeholder="Add context for this status change…"
            disabled={transitioningTo !== null}
            rows={3}
          />
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
