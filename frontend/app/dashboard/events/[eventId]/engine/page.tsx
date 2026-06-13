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
  const [allocation, setAllocation] = useState<Allocation | null>(null);

  const { data: participants = [] } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/participants`, session.accessToken] : null,
    ([path, token]) => fetchAPI<{ id: string }[]>(path, { token })
  );

  const handlePublished = () => {
    if (allocation) setAllocation({ ...allocation, status: "published" });
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
          onComplete={setAllocation}
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
