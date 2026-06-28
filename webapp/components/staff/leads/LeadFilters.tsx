"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LeadState } from "@/lib/types";

import { LEAD_STATE_OPTIONS } from "./LeadStateBadge";

type LeadFiltersProps = {
  state: LeadState | "";
  mine: boolean;
  onStateChange: (state: LeadState | "") => void;
  onMineChange: (mine: boolean) => void;
};

export function LeadFilters({
  state,
  mine,
  onStateChange,
  onMineChange,
}: LeadFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <Label htmlFor="state-filter" className="sr-only">
          State
        </Label>
        <Select
          value={state || "ALL"}
          onValueChange={(value) =>
            onStateChange(value === "ALL" ? "" : (value as LeadState))
          }
        >
          <SelectTrigger id="state-filter" className="w-[180px]">
            <SelectValue placeholder="All states">
              {(value) =>
                value === "ALL"
                  ? "All states"
                  : value != null
                    ? LEAD_STATE_OPTIONS.find((o) => o.value === value)?.label ??
                      String(value)
                    : null
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All states</SelectItem>
            {LEAD_STATE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="mine-filter"
          checked={mine}
          onCheckedChange={(checked) => onMineChange(checked === true)}
        />
        <Label htmlFor="mine-filter" className="cursor-pointer font-normal">
          My leads only
        </Label>
      </div>
    </div>
  );
}
