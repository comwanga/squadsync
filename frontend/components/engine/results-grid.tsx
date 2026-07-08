"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, Download, Link2, CheckCircle2, RefreshCw, Sparkles } from "lucide-react";
import { TeamCard } from "./team-card";
import { PayoutModal } from "./payout-modal";
import { publishAllocation, moveMember, regenerateAllocation, generateRationales } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import type { Allocation, Team } from "@/hooks/use-allocation";
import { normalizationNote } from "@/lib/allocation-notes";

function pct(value?: number) {
  return value == null ? "—" : `${value.toFixed(0)}%`;
}

function teamSizeBalance(teams: Team[]) {
  if (teams.length === 0) return "—";
  const sizes = teams.map(team => team.members.length);
  const min = Math.min(...sizes);
  const max = Math.max(...sizes);
  return max - min <= 1 ? "Balanced" : `${min}-${max} members`;
}

function averageMetric(teams: Team[], key: "skill_score" | "role_balance_score" | "fairness_score") {
  const values = teams.map(team => team[key]).filter((value): value is number => typeof value === "number");
  if (values.length === 0) return undefined;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

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
  const [payoutTeam, setPayoutTeam] = useState<Team | null>(null);
  const [explaining, setExplaining] = useState(false);
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

  const handleExplain = async () => {
    if (!session?.accessToken || explaining) return;
    setExplaining(true);
    try {
      const map = await generateRationales(session.accessToken, allocation.id);
      const teams = allocation.teams.map(t => ({ ...t, rationale: map[t.id] ?? t.rationale }));
      onChanged({ ...allocation, teams });
      toast.success("Teams explained");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Could not explain teams");
    } finally {
      setExplaining(false);
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
      <div className="rounded-lg border border-slate-700 bg-slate-900/70 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-100">
              {isDraft ? "Draft preview" : "Published teams"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Same participants and settings produce the same teams. Allocation ID {allocation.id.slice(0, 8)} uses participant snapshot {allocation.snapshot_hash.slice(0, 10)}.
            </p>
          </div>
          {isDraft && (
            <p className="text-xs text-muted-foreground max-w-sm">
              Review team sizes, experience balance, and strength coverage before publishing the public results link.
            </p>
          )}
        </div>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: "Team size balance", value: teamSizeBalance(allocation.teams) },
            { label: "Experience balance", value: pct(averageMetric(allocation.teams, "skill_score")) },
            { label: "Strength balance", value: pct(averageMetric(allocation.teams, "role_balance_score")) },
          ].map(item => (
            <div key={item.label} className="rounded-md border border-slate-700 bg-slate-950/35 px-3 py-2">
              <p className="text-xs text-muted-foreground">{item.label}</p>
              <p className="text-sm font-semibold text-slate-100">{item.value}</p>
            </div>
          ))}
        </div>
      </div>

      {note && (
        <div className="rounded-lg border border-violet-500/30 bg-violet-950/30 px-4 py-2 text-sm text-violet-100">
          {note}
        </div>
      )}
      {warningEntries.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-950/25 p-4">
          <AlertTriangle className="h-4 w-4 text-amber-300 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-100">Constraint warnings</p>
            <ul className="mt-1 space-y-0.5 text-amber-200">
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
            onPayout={allocation.status === "published" ? () => setPayoutTeam(team) : undefined}
          />
        ))}
      </div>

      {payoutTeam && (
        <PayoutModal
          team={payoutTeam}
          allocationId={allocation.id}
          open={!!payoutTeam}
          onOpenChange={(o) => { if (!o) setPayoutTeam(null); }}
        />
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        <Button variant="outline" onClick={handleExplain} disabled={explaining || working}>
          <Sparkles className="mr-2 h-4 w-4" /> {explaining ? "Explaining…" : "Explain teams"}
        </Button>
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
