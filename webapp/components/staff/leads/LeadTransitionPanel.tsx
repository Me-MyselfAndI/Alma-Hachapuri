"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";

import type { LeadRead, LeadState } from "@/lib/types";
import {
  getAllowedTransitions,
  getStateLabel,
} from "@/lib/lead-transitions";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

type LeadTransitionPanelProps = {
  lead: LeadRead;
  note: string;
  onNoteChange: (value: string) => void;
  onTransition: (toState: LeadState) => void;
  transitioning: boolean;
  error: string | null;
};

export function LeadTransitionPanel({
  lead,
  note,
  onNoteChange,
  onTransition,
  transitioning,
  error,
}: LeadTransitionPanelProps) {
  const allowed = getAllowedTransitions(lead.state);
  const [selectedState, setSelectedState] = useState<LeadState | null>(null);

  if (allowed.length === 0) {
    return null;
  }

  const handleChangeStatus = () => {
    if (!selectedState) {
      return;
    }
    onTransition(selectedState);
    setSelectedState(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change status</CardTitle>
        <CardDescription>
          Current status: <strong>{getStateLabel(lead.state)}</strong>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="transition-state">New status</Label>
          <Select
            value={selectedState}
            onValueChange={(value) => setSelectedState(value as LeadState)}
            disabled={transitioning}
          >
            <SelectTrigger id="transition-state" className="w-full sm:w-[240px]">
              <SelectValue placeholder="Select new status…">
                {(value) =>
                  value != null ? getStateLabel(value as LeadState) : null
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {allowed.map((toState) => (
                <SelectItem key={toState} value={toState}>
                  {getStateLabel(toState)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="transition-note">Optional note</Label>
          <Textarea
            id="transition-note"
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            placeholder="Add context for this status change…"
            disabled={transitioning}
            rows={3}
          />
        </div>

        <Button
          type="button"
          disabled={!selectedState || transitioning}
          onClick={handleChangeStatus}
        >
          {transitioning ? (
            <>
              <Loader2 className="animate-spin" aria-hidden />
              Changing status…
            </>
          ) : (
            "Change status"
          )}
        </Button>

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
