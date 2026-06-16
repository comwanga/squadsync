"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, Download, Link2, CheckCircle2, RefreshCw } from "lucide-react";
import { TeamCard } from "./team-card";
import { publishAllocation, moveMember, regenerateAllocation } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import type { Allocation } from "@/hooks/use-allocation";
import { normalizationNote } from "@/lib/allocation-notes";

interface ResultsGridProps {
  allocation: Allocation;
  eventId: string;
  onPublished: () => void;
  onChanged: (a: Allocation) => void;
}

export function ResultsGrid({ allocation, eventId, onPublished, onChanged }: ResultsGridProps) {
  const { data: session } = useSession();
  const [publishing, setPublishing] = useState(false);
  const [working, setWorking] = useState(false);  // a move or regenerate is in flight
  const warningEntries = Object.entries(allocation.constraint_warnings);
  const note = normalizationNote(allocation.ai_normalized, allocation.auto_normalized);
  const isDraft = allocation.status === "draft";

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

  const handleMove = async (participantId: string, teamId: string) => {
    if (!session?.accessToken || working) return;
    setWorking(true);
    try {
      const updated = await moveMember(session.accessToken, allocation.id, participantId, teamId);
      onChanged(updated);
      toast.success("Moved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Move failed");
    } finally {
      setWorking(false);
    }
  };

  const handleRegenerate = async () => {
    if (!session?.accessToken || working) return;
    setWorking(true);
    try {
      const a = await regenerateAllocation(session.accessToken, eventId);
      onChanged(a);
      toast.success("Regenerated");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Regenerate failed");
    } finally {
      setWorking(false);
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
      {note && (
        <div className="text-sm text-muted-foreground bg-violet-50 border border-violet-100 rounded-lg px-4 py-2">
          {note}
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
        {allocation.teams.map(team => (
          <TeamCard
            key={team.id}
            team={team}
            otherTeams={isDraft ? allocation.teams.filter(t => t.id !== team.id).map(t => ({ id: t.id, name: t.name })) : undefined}
            onMove={isDraft ? handleMove : undefined}
            moving={working}
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-2 pt-2">
        {isDraft && (
          <Button variant="outline" onClick={handleRegenerate} disabled={working}>
            <RefreshCw className="mr-2 h-4 w-4" /> {working ? "Working…" : "Regenerate"}
          </Button>
        )}
        {isDraft && (
          <Button onClick={handlePublish} disabled={publishing || working}>
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
