"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

type UserMenuProps = {
  email: string;
};

export function UserMenu({ email }: UserMenuProps) {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      router.push("/login");
      router.refresh();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
      <span
        className="hidden max-w-[12rem] truncate text-sm text-muted-foreground sm:inline"
        title={email}
      >
        {email}
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
