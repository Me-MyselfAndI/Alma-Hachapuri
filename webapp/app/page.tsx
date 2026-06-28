import Link from "next/link";

import { PublicShell } from "@/components/public/PublicShell";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <PublicShell
      title="Welcome"
      description="Submit your information for review, or sign in if you are staff."
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <Link href="/submit">
          <Button>Submit a lead</Button>
        </Link>
        <Link href="/login">
          <Button variant="outline">Staff login</Button>
        </Link>
      </div>
    </PublicShell>
  );
}
