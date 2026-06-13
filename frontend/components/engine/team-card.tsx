import { Users, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Team } from "@/hooks/use-allocation";

const roleColor: Record<string, string> = {
  frontend: "bg-blue-100 text-blue-800",
  backend: "bg-purple-100 text-purple-800",
  fullstack: "bg-indigo-100 text-indigo-800",
  ai_ml: "bg-pink-100 text-pink-800",
  ux: "bg-yellow-100 text-yellow-800",
  devops: "bg-green-100 text-green-800",
  mobile: "bg-orange-100 text-orange-800",
  blockchain: "bg-teal-100 text-teal-800",
  product: "bg-cyan-100 text-cyan-800",
  marketing: "bg-red-100 text-red-800",
};

export function TeamCard({ team }: { team: Team }) {
  const roleCounts = team.members.reduce<Record<string, number>>((acc, m) => {
    acc[m.role] = (acc[m.role] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
          <div className="flex items-center gap-1 text-xs text-amber-600 font-medium">
            <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
            {team.fairness_score?.toFixed(0) ?? "—"}%
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          {team.members.length} member{team.members.length !== 1 ? "s" : ""}
        </div>

        <div className="flex flex-wrap gap-1">
          {Object.entries(roleCounts).map(([role, count]) => (
            <span
              key={role}
              className={`px-1.5 py-0.5 rounded text-xs font-medium capitalize ${roleColor[role] ?? "bg-slate-100 text-slate-800"}`}
            >
              {role} ×{count}
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
              <li key={m.id} className="flex justify-between">
                <span className="font-medium">{m.name}</span>
                <span className="text-muted-foreground capitalize">{m.role} · {m.skill_level}</span>
              </li>
            ))}
          </ul>
        </details>
      </CardContent>
    </Card>
  );
}
