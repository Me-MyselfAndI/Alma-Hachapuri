import Link from "next/link";
import { Suspense } from "react";
import { Loader2 } from "lucide-react";

import { LoginForm } from "@/components/staff/login/LoginForm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function LoginFormFallback() {
  return (
    <div className="flex justify-center py-8">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Staff sign in</CardTitle>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<LoginFormFallback />}>
            <LoginForm />
          </Suspense>
        </CardContent>
      </Card>
      <Link
        href="/"
        className="mt-6 text-sm text-muted-foreground underline-offset-4 hover:underline"
      >
        ← Back to home
      </Link>
    </div>
  );
}
