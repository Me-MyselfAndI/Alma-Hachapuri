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
import { PageLoader } from "@/components/ui/page-loader";

import { AUTH_SESSION_CHANGED_KEY } from "@/lib/auth-session";
import type { AccountMe } from "@/lib/types";

type SessionContextValue = {
  user: AccountMe;
  /** Re-fetch /api/auth/me; returns the latest user or null if signed out. */
  refresh: () => Promise<AccountMe | null>;
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

  const refresh = useCallback(async (): Promise<AccountMe | null> => {
    const res = await fetch("/api/auth/me", {
      credentials: "include",
      cache: "no-store",
    });
    if (!res.ok) {
      setUser(null);
      return null;
    }
    const data = (await res.json()) as AccountMe;
    setUser(data);
    return data;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      setUser(null);
      const me = await refresh();
      if (cancelled) {
        return;
      }

      if (!me) {
        router.replace(`/login?next=${encodeURIComponent(currentPath)}`);
      }
      setLoading(false);
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [currentPath, refresh, router]);

  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === AUTH_SESSION_CHANGED_KEY) {
        void refresh();
      }
    }

    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    }

    window.addEventListener("storage", onStorage);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.removeEventListener("storage", onStorage);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [refresh]);

  if (loading) {
    return <PageLoader label="Loading your session…" fullScreen />;
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
