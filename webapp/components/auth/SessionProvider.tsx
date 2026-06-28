"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import type { AccountMe } from "@/lib/types";

type SessionContextValue = {
  user: AccountMe;
  refresh: () => Promise<boolean>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return ctx;
}

type SessionProviderProps = {
  children: React.ReactNode;
};

export function SessionProvider({ children }: SessionProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<AccountMe | null>(null);
  const [loading, setLoading] = useState(true);

  const currentPath = useMemo(() => {
    const query = searchParams.toString();
    return query ? `${pathname}?${query}` : pathname;
  }, [pathname, searchParams]);

  const refresh = useCallback(async (): Promise<boolean> => {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (!res.ok) {
      setUser(null);
      return false;
    }
    const data = (await res.json()) as AccountMe;
    setUser(data);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      const ok = await refresh();
      if (cancelled) return;

      if (!ok) {
        router.replace(
          `/login?next=${encodeURIComponent(currentPath)}`,
        );
      }
      setLoading(false);
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [currentPath, refresh, router]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2
          className="size-8 animate-spin text-muted-foreground"
          aria-label="Loading session"
        />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <SessionContext.Provider value={{ user, refresh }}>
      {children}
    </SessionContext.Provider>
  );
}
