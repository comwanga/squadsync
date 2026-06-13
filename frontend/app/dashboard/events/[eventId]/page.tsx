"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { useEvent, updateEvent } from "@/hooks/use-events";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Settings, Zap, ArrowRight } from "lucide-react";

export default function EventPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);
  const { event, isLoading } = useEvent(eventId);
  const { data: session } = useSession();
  const [activating, setActivating] = useState(false);

  if (isLoading) return <div className="animate-pulse space-y-4"><div className="h-8 bg-slate-200 rounded w-1/3" /></div>;
  if (!event) return <p className="text-muted-foreground">Event not found</p>;

  const handleActivate = async () => {
    if (!session?.accessToken) return;
    setActivating(true);
    try {
      await updateEvent(session.accessToken, eventId, { status: "active" });
      toast.success("Registration is now open");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to open registration");
    } finally {
      setActivating(false);
    }
  };

  const quickActions = [
    { label: "Attendees", icon: Users, href: "attendees", description: "View participants & QR code" },
    { label: "Configure", icon: Settings, href: "configure", description: "Set allocation weights & rules" },
    { label: "Run Allocation", icon: Zap, href: "engine", description: "Generate balanced teams" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{event.title}</h1>
          {event.description && <p className="text-muted-foreground text-sm mt-1">{event.description}</p>}
        </div>
        <div className="flex items-center gap-3">
          <Badge className="capitalize">{event.status}</Badge>
          {event.status === "draft" && (
            <Button size="sm" onClick={handleActivate} disabled={activating}>
              {activating ? "Opening…" : "Open Registration"}
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {quickActions.map(({ label, icon: Icon, href, description }) => (
          <Card key={href} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Icon className="h-4 w-4 text-primary" /> {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">{description}</p>
              <Button asChild variant="ghost" size="sm" className="p-0 h-auto">
                <Link href={`/dashboard/events/${eventId}/${href}`}>
                  Go <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
