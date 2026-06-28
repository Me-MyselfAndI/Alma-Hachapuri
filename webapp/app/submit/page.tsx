import { PublicShell } from "@/components/public/PublicShell";
import { SubmitForm } from "@/components/public/SubmitForm";

export default function SubmitPage() {
  return (
    <PublicShell
      title="Submit your information"
      description="Fill out the form below (including your resume). We will email you a link to confirm your submission. In local dev, that email appears in Mailpit — not your real inbox."
    >
      <SubmitForm />
    </PublicShell>
  );
}
