"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, startTransition } from "react";
import { ArrowLeft } from "lucide-react";

import { useSession } from "@/components/auth/SessionProvider";
import { LeadAssigneePanel } from "@/components/staff/leads/LeadAssigneePanel";
import { LeadDetailCards } from "@/components/staff/leads/LeadDetailCards";
import { LeadDetailHeader } from "@/components/staff/leads/LeadDetailHeader";
import { LeadEmailLogPanel } from "@/components/staff/leads/LeadEmailLogPanel";
import { LeadEmailPanel } from "@/components/staff/leads/LeadEmailPanel";
import { LeadStateHistoryPanel } from "@/components/staff/leads/LeadStateHistoryPanel";
import { LeadTransitionPanel } from "@/components/staff/leads/LeadTransitionPanel";
import { FadeIn } from "@/components/ui/fade-in";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatStaffApiError,
  staffFetch,
} from "@/lib/staff-api";
import {
  getPermissionMessage,
  getTransitionForbiddenMessage,
} from "@/lib/permission-messages";
import type { LeadRead, LeadState } from "@/lib/types";

type LeadDetailPageProps = {
  leadId: string;
};

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-56" />
      </div>
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}

export function LeadDetailPage({ leadId }: LeadDetailPageProps) {
  const router = useRouter();
  const { user } = useSession();
  const [lead, setLead] = useState<LeadRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [transitionError, setTransitionError] = useState<string | null>(null);
  const [transitioning, setTransitioning] = useState(false);

  const loadLead = useCallback(async () => {
    setLoading(true);
    setPageError(null);

    const result = await staffFetch<LeadRead>(`/api/v1/leads/${leadId}`);

    if (result.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(`/leads/${leadId}`)}`);
      return;
    }

    if (result.status === 403) {
      setLead(null);
      setPageError(getPermissionMessage("read_leads"));
      setLoading(false);
      return;
    }

    if (result.status === 404) {
      setLead(null);
      setPageError("not_found");
      setLoading(false);
      return;
    }

    if (!result.ok) {
      setLead(null);
      setPageError(formatStaffApiError(result.status, result.body));
      setLoading(false);
      return;
    }

    setLead(result.data);
    setLoading(false);
  }, [leadId, router]);

  useEffect(() => {
    startTransition(() => {
      void loadLead();
    });
  }, [loadLead]);

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/leads");
  };

  const handleTransition = async (toState: LeadState) => {
    if (!lead || !user) return;

    setTransitionError(null);
    setTransitioning(true);

    const payload: { to_state: LeadState; note?: string } = { to_state: toState };
    const trimmedNote = note.trim();
    if (trimmedNote) {
      payload.note = trimmedNote;
    }

    const result = await staffFetch<LeadRead>(
      `/api/v1/leads/${leadId}/transitions`,
      { method: "POST", json: payload },
    );

    if (result.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(`/leads/${leadId}`)}`);
      return;
    }

    if (result.status === 403) {
      setTransitionError(getTransitionForbiddenMessage(user, lead));
      setTransitioning(false);
      return;
    }

    if (result.status === 400 || !result.ok) {
      setTransitionError(
        formatStaffApiError(
          result.status,
          result.ok ? undefined : result.body,
        ),
      );
      setTransitioning(false);
      return;
    }

    setLead(result.data);
    setNote("");
    setTransitioning(false);
  };

  return (
    <div className="space-y-6">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="-ml-2 gap-1.5"
        onClick={handleBack}
      >
        <ArrowLeft className="size-4" aria-hidden />
        Back to leads
      </Button>

      {loading ? <DetailSkeleton /> : null}

      {!loading && pageError === "not_found" ? (
        <Alert>
          <AlertTitle>Lead not found</AlertTitle>
          <AlertDescription>
            This lead may have been removed or the link is incorrect.{" "}
            <Link href="/leads" className="underline underline-offset-4">
              Return to leads
            </Link>
          </AlertDescription>
        </Alert>
      ) : null}

      {!loading && pageError && pageError !== "not_found" ? (
        <Alert variant="destructive">
          <AlertDescription>{pageError}</AlertDescription>
        </Alert>
      ) : null}

      {!loading && lead && user ? (
        <FadeIn variant="fade">
          <>
            <LeadDetailHeader lead={lead} />
            <LeadDetailCards lead={lead} />
            <LeadAssigneePanel
              lead={lead}
              user={user}
              onLeadUpdated={setLead}
            />
            <div className="grid gap-6 lg:grid-cols-2">
              <LeadEmailPanel lead={lead} user={user} />
              <LeadTransitionPanel
                lead={lead}
                note={note}
                onNoteChange={setNote}
                onTransition={handleTransition}
                transitioning={transitioning}
                error={transitionError}
              />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <LeadStateHistoryPanel
                leadId={lead.id}
                refreshKey={lead.state_changed_at}
              />
              <LeadEmailLogPanel leadId={lead.id} user={user} />
            </div>
          </>
        </FadeIn>
      ) : null}
    </div>
  );
}
