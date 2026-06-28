import Link from "next/link";
import { Suspense } from "react";

import { BrandLogo } from "@/components/brand/BrandLogo";
import { LoginForm } from "@/components/staff/login/LoginForm";
import { LoginSessionBanner } from "@/components/staff/login/LoginSessionBanner";
import { ThemeControls } from "@/components/theme/ThemeControls";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FadeIn } from "@/components/ui/fade-in";
import { PageLoader } from "@/components/ui/page-loader";

function LoginFormFallback() {
  return <PageLoader label="Loading sign in…" />;
}

export default function LoginPage() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-background px-4 py-12">
      <div className="absolute right-4 top-4">
        <ThemeControls />
      </div>
      <FadeIn variant="scale" className="w-full max-w-sm">
        <Card>
          <CardHeader className="space-y-4 text-center">
            <div className="flex justify-center">
              <BrandLogo href="/" showWordmark={false} size="compact" />
            </div>
            <CardTitle className="font-heading text-2xl">Staff sign in</CardTitle>
          </CardHeader>
          <CardContent>
            <Suspense fallback={null}>
              <LoginSessionBanner />
            </Suspense>
            <Suspense fallback={<LoginFormFallback />}>
              <LoginForm />
            </Suspense>
          </CardContent>
        </Card>
      </FadeIn>
      <FadeIn delay={1} variant="fade">
        <Link
          href="/"
          className="mt-6 text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          ← Back to home
        </Link>
      </FadeIn>
    </div>
  );
}
