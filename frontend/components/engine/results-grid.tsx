"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, Download, Link2, CheckCircle2 } from "lucide-react";
import { TeamCard } from "./team-card";
import { publishAllocation } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import type { Allocation } from "@/hooks/use-allocation";
import { normalizationNote } from "@/lib/allocation-notes";

interface ResultsGridProps {
  allocation: Allocation;
  eventId: string;
  onPublished: () => void;
}

export function ResultsGrid({ allocation, eventId, onPublished }: ResultsGridProps) {
  const { data: session } = useSession();
  const [publishing, setPublishing] = useState(false);
  const warningEntries = Object.entries(allocation.constraint_warnings);

  const handlePublish = async () => {
    if (!session?.accessToken) return;
    setPublishing(true);
    try {
      await publishAllocation(session.accessToken, eventId, allocation.id);
      toast.success("Teams published!");
      onPublished();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to publish");
    } finally {
      setPublishing(false);
    }
  };

  const handleCSV = async () => {
    if (!session?.accessToken) return;
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/allocations/${allocation.id}/export/csv`,
        { headers: { Authorization: `Bearer ${session.accessToken}` } }
      );
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `squadsync-${allocation.id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    }
  };

  const handleCopyLink = async () => {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/allocations/${allocation.id}/export/link`,
      { headers: { Authorization: `Bearer ${session?.accessToken}` } }
    );
    const { url } = await res.json();
    await navigator.clipboard.writeText(url);
    toast.success("Share link copied!");
  };

  return (
    <div className="space-y-4">
      {normalizationNote(allocation.ai_normalized, allocation.auto_normalized) && (
        <div className="text-sm text-muted-foreground bg-violet-50 border border-violet-100 rounded-lg px-4 py-2">
          {normalizationNote(allocation.ai_normalized, allocation.auto_normalized)}
        </div>
      )}
      {warningEntries.length > 0 && (
        <div className="flex items-start gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-800">Constraint warnings</p>
            <ul className="mt-1 space-y-0.5 text-amber-700">
              {warningEntries.map(([team, warnings]) =>
                (warnings as string[]).map((w, i) => <li key={`${team}-${i}`}>{team}: {w}</li>)
              )}
            </ul>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {allocation.teams.map(team => <TeamCard key={team.id} team={team} />)}
      </div>

      <div className="flex flex-wrap gap-2 pt-2">
        {allocation.status === "draft" && (
          <Button onClick={handlePublish} disabled={publishing}>
            <CheckCircle2 className="mr-2 h-4 w-4" />
            {publishing ? "Publishing…" : "Publish Teams"}
          </Button>
        )}
        {allocation.status === "published" && (
          <>
            <Button variant="outline" onClick={handleCSV}>
              <Download className="mr-2 h-4 w-4" /> Export CSV
            </Button>
            <Button variant="outline" onClick={handleCopyLink}>
              <Link2 className="mr-2 h-4 w-4" /> Copy Share Link
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
