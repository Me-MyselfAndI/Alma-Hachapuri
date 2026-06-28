"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/components/auth/SessionProvider";
import { BrandLogo } from "@/components/brand/BrandLogo";
import { ThemeControls } from "@/components/theme/ThemeControls";
import { UserMenu } from "@/components/staff/shell/UserMenu";
import { canAccessAdmin } from "@/lib/access";
import { cn } from "@/lib/utils";

export function StaffHeader() {
  const pathname = usePathname();
  const { user } = useSession();
  const leadsActive = pathname.startsWith("/leads");
  const adminActive = pathname.startsWith("/admin");
  const showAdminNav = canAccessAdmin(user);

  return (
    <header className="site-header">
      <div className="mx-auto flex min-h-52 max-w-7xl items-center justify-between gap-6 px-6 py-4">
        <div className="flex min-w-0 items-center gap-8">
          <BrandLogo href="/leads" className="min-w-0" />
          <nav className="hidden md:flex md:items-center md:gap-1">
            <Link
              href="/leads"
              className={cn(
                "relative inline-flex h-12 items-center rounded-lg px-4 text-base font-medium transition-colors hover:bg-accent",
                leadsActive && "bg-accent text-foreground",
              )}
              aria-current={leadsActive ? "page" : undefined}
            >
              Leads
              {leadsActive ? (
                <span
                  className="absolute inset-x-2 bottom-1 h-0.5 rounded-full bg-gradient-brand"
                  aria-hidden
                />
              ) : null}
            </Link>
            {showAdminNav ? (
              <Link
                href="/admin/attorneys"
                className={cn(
                  "relative inline-flex h-12 items-center rounded-lg px-4 text-base font-medium transition-colors hover:bg-accent",
                  adminActive && "bg-accent text-foreground",
                )}
                aria-current={adminActive ? "page" : undefined}
              >
                Admin
                {adminActive ? (
                  <span
                    className="absolute inset-x-2 bottom-1 h-0.5 rounded-full bg-gradient-brand"
                    aria-hidden
                  />
                ) : null}
              </Link>
            ) : null}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <ThemeControls />
          <Link
            href="/leads"
            className={cn(
              "inline-flex h-12 items-center rounded-lg px-4 text-base font-medium transition-colors hover:bg-accent md:hidden",
              leadsActive && "bg-accent text-foreground",
            )}
            aria-current={leadsActive ? "page" : undefined}
          >
            Leads
          </Link>
          {showAdminNav ? (
            <Link
              href="/admin/attorneys"
              className={cn(
                "inline-flex h-12 items-center rounded-lg px-4 text-base font-medium transition-colors hover:bg-accent md:hidden",
                adminActive && "bg-accent text-foreground",
              )}
              aria-current={adminActive ? "page" : undefined}
            >
              Admin
            </Link>
          ) : null}
          <UserMenu email={user.email} role={user.role} />
        </div>
      </div>
    </header>
  );
}
