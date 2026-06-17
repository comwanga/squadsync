import { Users, Star, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Team } from "@/hooks/use-allocation";

const strengthColor: Record<string, string> = {
  technical: "bg-blue-100 text-blue-800",
  design: "bg-pink-100 text-pink-800",
  planning: "bg-indigo-100 text-indigo-800",
  coordination: "bg-green-100 text-green-800",
  communication: "bg-orange-100 text-orange-800",
  research: "bg-purple-100 text-purple-800",
  domain_expert: "bg-teal-100 text-teal-800",
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
                className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 font-medium px-1.5 py-0.5 rounded hover:bg-amber-50 transition-colors"
              >
                <Zap className="h-3 w-3" />
                Pay out
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
              className={`px-1.5 py-0.5 rounded text-xs font-medium capitalize ${strengthColor[strength] ?? "bg-slate-100 text-slate-800"}`}
            >
              {strength.replaceAll("_", " ")} ×{count}
            </span>
          ))}
        </div>

        <div className="space-y-1">
          {[
            { label: "Skill", value: team.skill_score },
            { label: "Role Balance", value: team.role_balance_score },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground w-20">{label}</span>
              <div className="flex-1 bg-slate-100 rounded-full h-1.5">
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
