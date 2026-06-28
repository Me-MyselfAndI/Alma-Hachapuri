"use client";

import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError, publicFetch } from "@/lib/api-client";
import type { LeadVerificationRequestResponse } from "@/lib/types";

const ACCEPTED_RESUME_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export function SubmitForm() {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<LeadVerificationRequestResponse | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const resume = formData.get("resume");

    if (!(resume instanceof File) || resume.size === 0) {
      setError("Please attach your resume (PDF, DOC, or DOCX).");
      return;
    }

    if (
      resume.type &&
      !ACCEPTED_RESUME_TYPES.includes(resume.type) &&
      !resume.name.match(/\.(pdf|doc|docx)$/i)
    ) {
      setError("Resume must be a PDF, DOC, or DOCX file.");
      return;
    }

    setSubmitting(true);

    const result = await publicFetch<LeadVerificationRequestResponse>(
      "/api/v1/leads/verification-requests",
      { method: "POST", formData },
    );

    setSubmitting(false);

    if (result.ok && result.status === 202) {
      setSuccess(result.data);
      form.reset();
      return;
    }

    if (!result.ok) {
      setError(formatApiError(result.status, result.body));
    }
  }

  if (success) {
    const mailpitUrl =
      process.env.NEXT_PUBLIC_MAILPIT_URL ?? "http://localhost:8025";

    return (
      <Alert>
        <AlertTitle>Check your email</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>
            {success.message} We sent a confirmation link to{" "}
            <strong>{success.email}</strong>.
          </p>
          {process.env.NODE_ENV === "development" ? (
            <p className="text-sm text-muted-foreground">
              <strong>Local dev:</strong> emails are not sent to real inboxes.
              Open{" "}
              <a
                href={mailpitUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline underline-offset-2"
              >
                Mailpit
              </a>{" "}
              to find the verification link.
            </p>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <form className="space-y-5" onSubmit={handleSubmit}>
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Submission failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="first_name">First name</Label>
          <Input
            id="first_name"
            name="first_name"
            required
            autoComplete="given-name"
            maxLength={100}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last name</Label>
          <Input
            id="last_name"
            name="last_name"
            required
            autoComplete="family-name"
            maxLength={100}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          maxLength={255}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="source">How did you hear about us? (optional)</Label>
        <Input id="source" name="source" maxLength={100} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="resume">Resume (PDF, DOC, or DOCX — max 10 MB)</Label>
        <Input
          id="resume"
          name="resume"
          type="file"
          required
          accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        />
      </div>

      <Button type="submit" disabled={submitting} className="w-full sm:w-auto">
        {submitting ? "Submitting…" : "Submit"}
      </Button>
        </form>
      </CardContent>
    </Card>
  );
}
