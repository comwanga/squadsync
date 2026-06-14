"use client";

import { useState } from "react";
import { use } from "react";
import useSWR from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";
import { RunPanel } from "@/components/engine/run-panel";
import { ResultsGrid } from "@/components/engine/results-grid";
import type { Allocation } from "@/hooks/use-allocation";

export default function EnginePage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);
  const { data: session } = useSession();
  // Locally-created/updated allocation takes precedence over the server copy so
  // the just-run or just-published result shows immediately.
  const [fresh, setFresh] = useState<Allocation | null>(null);

  const { data: participants = [] } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/participants`, session.accessToken] : null,
    ([path, token]) => fetchAPI<{ id: string }[]>(path, { token })
  );

  // Restore the most recent allocation so results survive a page refresh (latest first).
  const { data: allocations = [], mutate: mutateAllocations } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/allocations`, session.accessToken] : null,
    ([path, token]) => fetchAPI<Allocation[]>(path, { token })
  );

  const allocation = fresh ?? allocations[0] ?? null;

  const handlePublished = () => {
    if (allocation) setFresh({ ...allocation, status: "published" });
    mutateAllocations();
  };

  const handleComplete = (a: Allocation) => {
    setFresh(a);
    mutateAllocations();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Allocation Engine</h1>
        <p className="text-sm text-muted-foreground">Generate balanced teams from registered participants</p>
      </div>

      {!allocation ? (
        <RunPanel
          eventId={eventId}
          participantCount={participants.length}
          onComplete={handleComplete}
        />
      ) : (
        <ResultsGrid
          allocation={allocation}
          eventId={eventId}
          onPublished={handlePublished}
        />
      )}
    </div>
  );
}
