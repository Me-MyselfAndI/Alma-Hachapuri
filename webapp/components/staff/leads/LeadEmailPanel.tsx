"use client";

import { Loader2, Mail, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useState, startTransition } from "react";

import type { AccountMe, LeadRead } from "@/lib/types";
import { formatStaffApiError, staffFetch } from "@/lib/staff-api";
import { getPermissionMessage } from "@/lib/permission-messages";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const STAFF_SEND_TEMPLATES = new Set([
  "prospect_confirmation",
  "prospect_follow_up",
]);

const TEMPLATE_LABELS: Record<string, string> = {
  prospect_confirmation: "Submission confirmation",
  prospect_follow_up: "Follow-up to prospect",
};

type EmailTemplateInfo = {
  key: string;
  description: string;
  default_recipient: string;
};

type EmailPreviewResponse = {
  subject: string;
  body: string;
};

type EmailNotificationRead = {
  id: string;
  status: string;
  recipient: string;
  subject: string;
};

type LeadEmailPanelProps = {
  lead: LeadRead;
  user: AccountMe;
};

function renderLocalPreview(
  template: string,
  lead: LeadRead,
): { subject: string; body: string } | null {
  const firstName = lead.first_name.trim() || "there";

  if (template === "prospect_confirmation") {
    return {
      subject: "We received your submission",
      body: `Hi ${firstName},\n\nThank you — we received your submission and will be in touch soon.`,
    };
  }

  if (template === "prospect_follow_up") {
    return {
      subject: "Follow-up on your submission",
      body: `Hi ${firstName},\n\nWe wanted to follow up regarding your recent submission.`,
    };
  }

  return null;
}

function templateLabel(key: string | null): string | null {
  if (!key) {
    return null;
  }
  return TEMPLATE_LABELS[key] ?? key;
}

export function LeadEmailPanel({ lead, user }: LeadEmailPanelProps) {
  const canSend = user.permissions.includes("send_email");
  const mailpitUrl =
    process.env.NEXT_PUBLIC_MAILPIT_URL ?? "http://localhost:8025";

  const [templates, setTemplates] = useState<EmailTemplateInfo[]>([]);
  const [templateKey, setTemplateKey] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSent, setLastSent] = useState<EmailNotificationRead | null>(null);

  const applyTemplate = useCallback(
    async (template: string) => {
      setTemplateKey(template);
      setLoadingPreview(true);
      setError(null);

      const result = await staffFetch<EmailPreviewResponse>(
        `/api/v1/leads/${lead.id}/emails/preview`,
        { method: "POST", json: { template } },
      );

      setLoadingPreview(false);

      if (result.ok) {
        setSubject(result.data.subject);
        setBody(result.data.body);
        return;
      }

      const fallback = renderLocalPreview(template, lead);
      if (fallback) {
        setSubject(fallback.subject);
        setBody(fallback.body);
        return;
      }

      setError(formatStaffApiError(result.status, result.body));
    },
    [lead],
  );

  const loadTemplates = useCallback(async () => {
    setLoadingTemplates(true);
    const result = await staffFetch<EmailTemplateInfo[]>(
      "/api/v1/emails/templates",
    );
    setLoadingTemplates(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    const staffTemplates = result.data.filter((item) =>
      STAFF_SEND_TEMPLATES.has(item.key),
    );
    setTemplates(staffTemplates);

    const defaultKey =
      staffTemplates.find((t) => t.key === "prospect_follow_up")?.key ??
      staffTemplates[0]?.key;

    if (defaultKey) {
      await applyTemplate(defaultKey);
    }
  }, [applyTemplate]);

  useEffect(() => {
    if (!canSend) {
      return;
    }
    startTransition(() => {
      void loadTemplates();
    });
  }, [canSend, loadTemplates]);

  const handleTemplateChange = (value: string | null) => {
    if (value) {
      void applyTemplate(value);
    }
  };

  const handleResetToTemplate = () => {
    if (templateKey) {
      void applyTemplate(templateKey);
    }
  };

  const handleSend = async () => {
    if (!templateKey || !subject.trim() || !body.trim()) {
      return;
    }

    setSending(true);
    setError(null);
    setLastSent(null);

    const result = await staffFetch<EmailNotificationRead>(
      `/api/v1/leads/${lead.id}/emails`,
      {
        method: "POST",
        json: {
          template: templateKey,
          recipient: lead.email,
          subject: subject.trim(),
          body: body.trim(),
        },
      },
    );

    setSending(false);

    if (!result.ok) {
      if (result.status === 403) {
        setError(getPermissionMessage("send_email"));
        return;
      }
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setLastSent(result.data);
  };

  if (!canSend) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Send email</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {getPermissionMessage("send_email")}
          </p>
        </CardContent>
      </Card>
    );
  }

  const formDisabled = loadingTemplates || loadingPreview || sending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Send email</CardTitle>
        <CardDescription>
          Choose a template, edit the message, then send to{" "}
          <strong>{lead.email}</strong>. In local dev, open Mailpit to read it.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email-template">Template</Label>
          <Select
            value={templateKey}
            onValueChange={handleTemplateChange}
            disabled={formDisabled || templates.length === 0}
          >
            <SelectTrigger id="email-template" className="w-full sm:w-[280px]">
              <SelectValue
                placeholder={
                  loadingTemplates ? "Loading templates…" : "Select template…"
                }
              >
                {(value) => templateLabel(value as string | null)}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {templates.map((template) => (
                <SelectItem key={template.key} value={template.key}>
                  {TEMPLATE_LABELS[template.key] ?? template.key}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email-subject">Subject</Label>
          <Input
            id="email-subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={formDisabled || !templateKey}
            maxLength={200}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="email-body">Message</Label>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 px-2"
              disabled={formDisabled || !templateKey}
              onClick={handleResetToTemplate}
            >
              <RotateCcw className="size-3.5" aria-hidden />
              Reset to template
            </Button>
          </div>
          <Textarea
            id="email-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={formDisabled || !templateKey}
            rows={8}
            maxLength={10000}
            className="min-h-[160px] resize-y font-sans"
          />
        </div>

        <Button
          type="button"
          disabled={
            !templateKey ||
            !subject.trim() ||
            !body.trim() ||
            sending ||
            loadingTemplates ||
            loadingPreview
          }
          onClick={() => void handleSend()}
        >
          {sending ? (
            <>
              <Loader2 className="animate-spin" aria-hidden />
              Sending…
            </>
          ) : loadingPreview ? (
            <>
              <Loader2 className="animate-spin" aria-hidden />
              Loading preview…
            </>
          ) : (
            <>
              <Mail className="size-4" aria-hidden />
              Send email
            </>
          )}
        </Button>

        {lastSent ? (
          <Alert>
            <AlertTitle>Email sent</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
                <strong>{lastSent.subject}</strong> → {lastSent.recipient}{" "}
                (status: {lastSent.status})
              </p>
              {process.env.NODE_ENV === "development" ? (
                <p className="text-sm text-muted-foreground">
                  <strong>Local dev:</strong> open{" "}
                  <a
                    href={mailpitUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline underline-offset-2"
                  >
                    Mailpit
                  </a>{" "}
                  and search for {lead.email}.
                </p>
              ) : null}
            </AlertDescription>
          </Alert>
        ) : null}

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
