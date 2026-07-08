import { Users, Star, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Team } from "@/hooks/use-allocation";

const strengthColor: Record<string, string> = {
  technical: "bg-blue-500/20 text-blue-100 border-blue-400/30",
  design: "bg-pink-500/20 text-pink-100 border-pink-400/30",
  planning: "bg-indigo-500/20 text-indigo-100 border-indigo-400/30",
  coordination: "bg-green-500/20 text-green-100 border-green-400/30",
  communication: "bg-orange-500/20 text-orange-100 border-orange-400/30",
  research: "bg-purple-500/20 text-purple-100 border-purple-400/30",
  domain_expert: "bg-teal-500/20 text-teal-100 border-teal-400/30",
};

export function TeamCard({
  team,
  otherTeams,
  onMove,
  moving,
  onPayout,
}: {
  team: Team;
  otherTeams?: { id: string; name: string }[];
  onMove?: (participantId: string, teamId: string) => void;
  moving?: boolean;
  onPayout?: () => void;
}) {
  const strengthCounts = team.members.reduce<Record<string, number>>((acc, m) => {
    const key = m.normalized_strength ?? "other";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
  const experienceCounts = team.members.reduce<Record<string, number>>((acc, m) => {
    acc[m.experience_level] = (acc[m.experience_level] ?? 0) + 1;
    return acc;
  }, {});
  const strengthSummary = Object.entries(strengthCounts)
    .map(([strength, count]) => `${count} ${strength.replaceAll("_", " ")}`)
    .join(", ");
  const experienceSummary = Object.entries(experienceCounts)
    .map(([level, count]) => `${count} ${level}`)
    .join(", ");

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-xs text-amber-600 font-medium">
              <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
              {team.fairness_score?.toFixed(0) ?? "—"}%
            </div>
            {onPayout && (
              <button
                onClick={onPayout}
                className="flex items-center gap-1 text-xs text-amber-300 hover:text-amber-200 font-medium px-1.5 py-0.5 rounded hover:bg-amber-400/10 transition-colors"
              >
                <Zap className="h-3 w-3" />
                Rewards
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          {team.members.length} member{team.members.length !== 1 ? "s" : ""}
        </div>

        <div className="flex flex-wrap gap-1">
          {Object.entries(strengthCounts).map(([strength, count]) => (
            <span
              key={strength}
              className={`rounded border px-1.5 py-0.5 text-xs font-medium capitalize ${strengthColor[strength] ?? "bg-slate-500/20 text-slate-100 border-slate-400/30"}`}
            >
              {strength.replaceAll("_", " ")} ×{count}
            </span>
          ))}
        </div>

        {team.rationale && (
          <div className="rounded-md border border-violet-500/30 bg-violet-950/30 p-2 space-y-1">
            <p className="text-xs font-semibold text-violet-100">{team.rationale.title}</p>
            <p className="text-xs text-violet-200">{team.rationale.summary}</p>
            {team.rationale.strengths.length > 0 && (
              <ul className="text-xs text-violet-200 list-disc list-inside">
                {team.rationale.strengths.map((s, i) => <li key={`s-${i}`}>{s}</li>)}
              </ul>
            )}
            {team.rationale.gaps.length > 0 && (
              <ul className="text-xs text-amber-200 list-disc list-inside">
                {team.rationale.gaps.map((g, i) => <li key={`g-${i}`}>{g}</li>)}
              </ul>
            )}
          </div>
        )}

        <div className="rounded-md border border-slate-700 bg-slate-950/35 p-2 text-xs text-muted-foreground">
          <p className="font-medium text-slate-100">Why this team?</p>
          <p className="mt-1">
            This draft keeps {team.members.length} member{team.members.length !== 1 ? "s" : ""} together with {experienceSummary || "mixed experience"} and {strengthSummary || "mixed strengths"}.
          </p>
        </div>

        <div className="space-y-1">
          {[
            { label: "Skill", value: team.skill_score },
            { label: "Role Balance", value: team.role_balance_score },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground w-20">{label}</span>
              <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                <div
                  className="bg-primary rounded-full h-1.5 transition-all"
                  style={{ width: `${value ?? 0}%` }}
                />
              </div>
              <span className="font-mono w-8 text-right">{value?.toFixed(0) ?? "—"}</span>
            </div>
          ))}
        </div>

        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">View members</summary>
          <ul className="mt-2 space-y-1">
            {team.members.map(m => (
              <li key={m.id} className="flex items-center justify-between gap-2">
                <span className="font-medium">{m.name}</span>
                <span className="flex items-center gap-2">
                  <span className="text-muted-foreground capitalize">
                    {(m.normalized_strength ?? "—").replaceAll("_", " ")} · {m.experience_level}
                  </span>
                  {onMove && otherTeams && otherTeams.length > 0 && (
                    <select
                      aria-label={`Move ${m.name} to another team`}
                      value=""
                      disabled={moving}
                      onChange={e => { if (e.target.value) onMove(m.id, e.target.value); }}
                      className="text-xs rounded border border-input bg-background px-1 py-0.5 disabled:opacity-50"
                    >
                      <option value="" disabled>Move…</option>
                      {otherTeams.map(t => <option key={t.id} value={t.id}>→ {t.name}</option>)}
                    </select>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </details>
      </CardContent>
    </Card>
  );
}
