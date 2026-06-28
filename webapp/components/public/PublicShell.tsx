"use client";

import Link from "next/link";

import { BrandLogo } from "@/components/brand/BrandLogo";
import { ThemeControls } from "@/components/theme/ThemeControls";
import { Button } from "@/components/ui/button";
import { FadeIn } from "@/components/ui/fade-in";

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
    <div className="flex min-h-full flex-col bg-background">
      <header className="site-header">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-6 px-6 py-6">
          <BrandLogo className="min-w-0" />
          <div className="flex shrink-0 items-center gap-2">
            <ThemeControls />
            <Link href="/login">
              <Button variant="outline" size="sm">
                Staff login
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-10">
        {(title || description) && (
          <FadeIn className="space-y-3">
            {title ? (
              <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">
                {title}
              </h1>
            ) : null}
            {description ? (
              <p className="text-base leading-relaxed text-muted-foreground">
                {description}
              </p>
            ) : null}
          </FadeIn>
        )}
        <FadeIn delay={1} variant="scale">
          {children}
        </FadeIn>
      </main>

      <footer className="border-t border-border bg-background">
        <div className="mx-auto max-w-2xl px-6 py-4 text-sm text-muted-foreground">
          Hachapuri — prospect intake
        </div>
      </footer>
    </div>
  );
}
