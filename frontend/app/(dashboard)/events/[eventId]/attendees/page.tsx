"use client";

import { use } from "react";
import { useEvent } from "@/hooks/use-events";
import { AttendeesTable } from "@/components/attendees/attendees-table";
import { QRDisplay } from "@/components/attendees/qr-display";

export default function AttendeesPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);
  const { event } = useEvent(eventId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Attendees</h1>
        <p className="text-sm text-muted-foreground">Manage participants and share the registration QR code</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <AttendeesTable eventId={eventId} />
        </div>
        <div>
          {event && <QRDisplay slug={event.registration_slug} />}
        </div>
      </div>
    </div>
  );
}
