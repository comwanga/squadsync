import { ConfigForm } from "@/components/configure/config-form";
import { EventBreadcrumbAuto } from "@/components/layout/event-breadcrumb";

export default async function ConfigurePage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = await params;
  return (
    <div className="space-y-6">
      <EventBreadcrumbAuto eventId={eventId} current="Configure" />
      <div>
        <h1 className="text-xl font-bold">Configure Allocation</h1>
        <p className="text-sm text-muted-foreground">Set balancing weights and role constraints</p>
      </div>
      <ConfigForm eventId={eventId} />
    </div>
  );
}
