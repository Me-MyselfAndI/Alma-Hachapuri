import { VerifyClient } from "@/components/public/VerifyClient";
import { PublicShell } from "@/components/public/PublicShell";

type VerifyPageProps = {
  searchParams: Promise<{ token?: string }>;
};

export default async function VerifyPage({ searchParams }: VerifyPageProps) {
  const params = await searchParams;
  const token = params.token ?? null;

  return (
    <PublicShell
      title="Email verification"
      description="Confirming your submission from the link in your email."
    >
      <VerifyClient token={token} />
    </PublicShell>
  );
}
