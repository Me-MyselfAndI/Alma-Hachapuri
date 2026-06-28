import Link from "next/link";

import { Button } from "@/components/ui/button";

type PublicShellProps = {
  children: React.ReactNode;
  title?: string;
  description?: string;
};

export function PublicShell({
  children,
  title,
  description,
}: PublicShellProps) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            Hachapuri
          </Link>
          <Link href="/login">
            <Button variant="outline" size="sm">
              Staff login
            </Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
        {(title || description) && (
          <div className="space-y-2">
            {title ? (
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            ) : null}
            {description ? (
              <p className="text-muted-foreground">{description}</p>
            ) : null}
          </div>
        )}
        {children}
      </main>

      <footer className="border-t">
        <div className="mx-auto max-w-2xl px-6 py-4 text-sm text-muted-foreground">
          Hachapuri — prospect intake
        </div>
      </footer>
    </div>
  );
}
