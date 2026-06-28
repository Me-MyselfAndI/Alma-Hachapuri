"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { FadeIn } from "@/components/ui/fade-in";
import { PageLoader } from "@/components/ui/page-loader";
import { formatVerifyError, publicFetch } from "@/lib/api-client";
import type { LeadCreateResponse } from "@/lib/types";

type VerifyState =
  | { kind: "loading" }
  | { kind: "success"; data: LeadCreateResponse }
  | { kind: "error"; message: string }
  | { kind: "missing-token" };

type VerifyClientProps = {
  token: string | null;
};

async function verifyWithPost(token: string) {
  return publicFetch<LeadCreateResponse>("/api/v1/leads/verify", {
    method: "POST",
    json: { token },
  });
}

async function verifyWithGet(token: string) {
  const params = new URLSearchParams({ token });
  return publicFetch<LeadCreateResponse>(
    `/api/v1/leads/verify?${params.toString()}`,
  );
}

export function VerifyClient({ token }: VerifyClientProps) {
  const [state, setState] = useState<VerifyState>(() =>
    token ? { kind: "loading" } : { kind: "missing-token" },
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function run() {
      const postResult = await verifyWithPost(token!);

      if (cancelled) return;

      if (postResult.ok && postResult.status === 201) {
        setState({ kind: "success", data: postResult.data });
        return;
      }

      const getResult = await verifyWithGet(token!);

      if (cancelled) return;

      if (getResult.ok && getResult.status === 201) {
        setState({ kind: "success", data: getResult.data });
        return;
      }

      const failed = !postResult.ok ? postResult : getResult;
      if (!failed.ok) {
        setState({
          kind: "error",
          message: formatVerifyError(failed.status, failed.body),
        });
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (state.kind === "loading") {
    return <PageLoader label="Verifying your email…" />;
  }

  if (state.kind === "missing-token") {
    return (
      <FadeIn variant="scale">
        <Alert variant="destructive">
          <AlertTitle>Invalid link</AlertTitle>
          <AlertDescription>
            Verification link is missing or invalid. Open the link from your email,
            or submit the form again.
          </AlertDescription>
        </Alert>
      </FadeIn>
    );
  }

  if (state.kind === "success") {
    return (
      <FadeIn variant="scale">
        <Alert>
          <AlertTitle>Thank you</AlertTitle>
          <AlertDescription>
            {state.data.message} Your reference id is{" "}
            <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-sm">
              {state.data.id}
            </code>
            .
          </AlertDescription>
        </Alert>
      </FadeIn>
    );
  }

  return (
    <FadeIn variant="scale">
      <Alert variant="destructive">
        <AlertTitle>Verification failed</AlertTitle>
        <AlertDescription>{state.message}</AlertDescription>
      </Alert>
    </FadeIn>
  );
}
