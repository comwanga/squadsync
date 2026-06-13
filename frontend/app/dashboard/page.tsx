"use client";

import { useEvents } from "@/hooks/use-events";
import { EventCard } from "@/components/events/event-card";
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { Skeleton } from "@/components/ui/skeleton";

export default function OverviewPage() {
  const { events, isLoading, error } = useEvents();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground text-sm">Manage your events and team allocations</p>
        </div>
        <CreateEventDialog />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">
          <p className="text-lg font-medium">Failed to load events</p>
          <p className="text-sm mt-1">{error.message ?? "Please try again"}</p>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg font-medium">No events yet</p>
          <p className="text-sm mt-1">Create your first event to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map(event => <EventCard key={event.id} event={event} />)}
        </div>
      )}
    </div>
  );
}
