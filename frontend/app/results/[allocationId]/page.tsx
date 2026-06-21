import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Star, Zap } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { FindMyTeam } from "@/components/results/find-my-team";

interface TeamMember { id: string; name: string; normalized_strength?: string; experience_level: string; }
interface Team {
  id: string;
  name: string;
  fairness_score?: number;
  members: TeamMember[];
  rationale?: { title: string; summary: string; strengths: string[]; gaps: string[] } | null;
}
interface PayoutSummary { team_label: string; total_sats: number; status: string; paid_count: number; member_count: number; }
interface AllocationResult { id: string; status: string; teams: Team[]; payouts?: PayoutSummary[]; }

async function getAllocation(id: string): Promise<AllocationResult | null> {
  try {
    return await fetchAPI<AllocationResult>(`/api/v1/public/allocations/${id}`);
  } catch {
    return null;
  }
}

export default async function ResultsPage({ params }: { params: Promise<{ allocationId: string }> }) {
  const { allocationId } = await params;
  const result = await getAllocation(allocationId);

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Results not found or not yet published.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <Logo className="h-9 w-auto mx-auto" />
          <p className="text-muted-foreground text-sm mt-1">Team Allocation Results</p>
        </div>
        <FindMyTeam allocationId={allocationId} />
        {result.payouts && result.payouts.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            {result.payouts.map((p, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-amber-800">
                <Zap className="h-4 w-4 fill-amber-400 stroke-amber-500" />
                <span className="font-medium">⚡ Prize paid — {p.team_label}</span>
                <span className="text-amber-700">{p.total_sats.toLocaleString()} sats → {p.paid_count}/{p.member_count} paid</span>
              </div>
            ))}
          </div>
        )}
        {(() => {
          const paidTeamLabels = new Set((result.payouts ?? []).map(p => p.team_label));
          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {result.teams.map(team => (
                <Card key={team.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
                      <div className="flex items-center gap-2">
                        {paidTeamLabels.has(team.name) && (
                          <span className="flex items-center gap-1 text-xs text-amber-700 font-medium bg-amber-100 border border-amber-200 rounded px-1.5 py-0.5">
                            <Zap className="h-3 w-3 fill-amber-400 stroke-amber-500" />
                            Paid
                          </span>
                        )}
                        {team.fairness_score && (
                          <span className="flex items-center gap-1 text-xs text-amber-600 font-medium">
                            <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
                            {team.fairness_score.toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1.5">
                      {team.members.map(m => (
                        <li key={m.id} className="flex justify-between text-sm">
                          <span className="font-medium">{m.name}</span>
                          <span className="text-muted-foreground capitalize text-xs">{(m.normalized_strength ?? "").replaceAll("_", " ")}</span>
                        </li>
                      ))}
                    </ul>
                    {team.rationale && (
                      <div className="rounded-md bg-violet-50 border border-violet-100 p-3 mt-2 space-y-1">
                        <p className="text-sm font-semibold text-violet-900">{team.rationale.title}</p>
                        <p className="text-sm text-violet-800">{team.rationale.summary}</p>
                        {team.rationale.strengths.length > 0 && (
                          <ul className="text-xs text-violet-700 list-disc list-inside">
                            {team.rationale.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                          </ul>
                        )}
                        {team.rationale.gaps.length > 0 && (
                          <ul className="text-xs text-amber-700 list-disc list-inside">
                            {team.rationale.gaps.map((g: string, i: number) => <li key={i}>{g}</li>)}
                          </ul>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
