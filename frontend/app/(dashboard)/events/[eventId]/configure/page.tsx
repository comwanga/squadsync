import { ConfigForm } from "@/components/configure/config-form";

export default async function ConfigurePage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = await params;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Configure Allocation</h1>
        <p className="text-sm text-muted-foreground">Set balancing weights and role constraints</p>
      </div>
      <ConfigForm eventId={eventId} />
    </div>
  );
}
