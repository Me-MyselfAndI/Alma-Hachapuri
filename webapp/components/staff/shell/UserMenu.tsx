"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { redirectAfterAuthChange } from "@/lib/auth-session";
import { roleLabel } from "@/lib/access";
import type { AccountMe } from "@/lib/types";

type UserMenuProps = {
  email: string;
  role: AccountMe["role"];
};

export function UserMenu({ email, role }: UserMenuProps) {
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      redirectAfterAuthChange("/login");
    } catch {
      setLoggingOut(false);
    }
  }

  return (
    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
      <span
        className="hidden max-w-[14rem] truncate text-sm text-muted-foreground sm:inline"
        title={`${email} (${roleLabel(role)})`}
      >
        {email}
        <span className="text-muted-foreground/80"> · {roleLabel(role)}</span>
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-11 min-w-11 sm:min-h-8 sm:min-w-0"
        onClick={handleLogout}
        disabled={loggingOut}
      >
        {loggingOut ? (
          <>
            <Loader2 className="animate-spin" aria-hidden />
            <span className="hidden sm:inline">Signing out…</span>
          </>
        ) : (
          "Log out"
        )}
      </Button>
    </div>
  );
}
