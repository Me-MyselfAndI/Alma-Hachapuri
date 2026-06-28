import { LeadDetailPage } from "@/components/staff/leads/LeadDetailPage";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function LeadDetailRoute({ params }: PageProps) {
  const { id } = await params;
  return <LeadDetailPage leadId={id} />;
}
