"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { roleLabel } from "@/lib/access";
import type { AccountMe } from "@/lib/types";

export function LoginSessionBanner() {
  const [user, setUser] = useState<AccountMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      const res = await fetch("/api/auth/me", { credentials: "include" });
      if (cancelled) {
        return;
      }
      if (res.ok) {
        setUser((await res.json()) as AccountMe);
      } else {
        setUser(null);
      }
      setLoading(false);
    }

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || !user) {
    return null;
  }

  return (
    <Alert className="mb-4">
      <AlertTitle>Already signed in</AlertTitle>
      <AlertDescription className="space-y-3">
        <p>
          You are signed in as{" "}
          <strong>{user.email}</strong> ({roleLabel(user.role)}).
          Signing in below replaces your session everywhere in this browser.
          Use <strong>Log out</strong> first if you want a clean switch.
        </p>
        <Link href="/leads">
          <Button size="sm" variant="outline" type="button">
            Continue to leads
          </Button>
        </Link>
      </AlertDescription>
    </Alert>
  );
}
