import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ResumeDownloadLinkProps = {
  leadId: string;
  className?: string;
};

export function ResumeDownloadLink({
  leadId,
  className,
}: ResumeDownloadLinkProps) {
  return (
    <a
      href={`/api/leads/${leadId}/resume`}
      className={cn(buttonVariants({ variant: "default" }), className)}
      download
    >
      Download resume
    </a>
  );
}
