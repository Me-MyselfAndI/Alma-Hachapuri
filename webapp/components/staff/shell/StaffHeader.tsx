"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/components/auth/SessionProvider";
import { UserMenu } from "@/components/staff/shell/UserMenu";
import { cn } from "@/lib/utils";

export function StaffHeader() {
  const pathname = usePathname();
  const { user } = useSession();
  const leadsActive = pathname.startsWith("/leads");

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
        <div className="flex min-w-0 items-center gap-6">
          <Link
            href="/leads"
            className="shrink-0 text-lg font-semibold tracking-tight"
          >
            Hachapuri
          </Link>
          <nav className="hidden md:block">
            <Link
              href="/leads"
              className={cn(
                "inline-flex h-11 items-center rounded-lg px-3 text-sm font-medium transition-colors hover:bg-muted",
                leadsActive && "bg-muted text-foreground",
              )}
              aria-current={leadsActive ? "page" : undefined}
            >
              Leads
            </Link>
          </nav>
        </div>

        <div className="flex min-w-0 items-center gap-3">
          <Link
            href="/leads"
            className={cn(
              "inline-flex h-11 items-center rounded-lg px-3 text-sm font-medium transition-colors hover:bg-muted md:hidden",
              leadsActive && "bg-muted text-foreground",
            )}
            aria-current={leadsActive ? "page" : undefined}
          >
            Leads
          </Link>
          <UserMenu email={user.email} />
        </div>
      </div>
    </header>
  );
}
