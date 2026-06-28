import Link from "next/link";

import { PublicShell } from "@/components/public/PublicShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/fade-in";

export default function HomePage() {
  return (
    <PublicShell
      title="Welcome"
      description="Submit your information for review, or sign in if you are staff."
    >
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href="/submit" className="flex-1">
            <Button size="lg" className="h-11 w-full">
              Submit a lead
            </Button>
          </Link>
          <Link href="/login" className="flex-1">
            <Button variant="outline" size="lg" className="h-11 w-full">
              Staff login
            </Button>
          </Link>
        </div>

        <FadeIn delay={2} variant="fade">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardContent className="space-y-2 pt-6">
                <p className="font-heading text-sm font-bold text-foreground">
                  For prospects
                </p>
                <p className="text-sm text-muted-foreground">
                  Share your resume and confirm by email — no account needed.
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="space-y-2 pt-6">
                <p className="font-heading text-sm font-bold text-foreground">
                  For staff
                </p>
                <p className="text-sm text-muted-foreground">
                  Review leads, update status, and send follow-ups from one place.
                </p>
              </CardContent>
            </Card>
          </div>
        </FadeIn>
      </div>
    </PublicShell>
  );
}
