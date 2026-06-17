"use client";

import { useState } from "react";
import { useEvents } from "@/hooks/use-events";
import { EventCard } from "@/components/events/event-card";
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { QuickGuideButton } from "@/components/onboarding/quick-guide-button";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function EventsView({ title, subtitle }: { title: string; subtitle: string }) {
  const [archived, setArchived] = useState(false);
  const { events, isLoading, error } = useEvents(archived);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground text-sm">{subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" aria-pressed={archived} onClick={() => setArchived(a => !a)}>
            {archived ? "Active events" : "Show archived"}
          </Button>
          {!archived && <QuickGuideButton />}
          {!archived && <CreateEventDialog />}
        </div>
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
          <p className="text-lg font-medium">{archived ? "No archived events" : "No events yet"}</p>
          <p className="text-sm mt-1">{archived ? "Archived events will appear here." : "Create your first event to get started"}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map(event => <EventCard key={event.id} event={event} />)}
        </div>
      )}
    </div>
  );
}
