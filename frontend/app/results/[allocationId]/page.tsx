import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Star } from "lucide-react";

interface TeamMember { id: string; name: string; role: string; skill_level: string; }
interface Team {
  id: string;
  name: string;
  fairness_score?: number;
  members: TeamMember[];
}
interface AllocationResult { id: string; status: string; teams: Team[]; }

async function getAllocation(id: string): Promise<AllocationResult | null> {
  try {
    return await fetchAPI<AllocationResult>(`/api/v1/allocations/${id}/teams`);
  } catch {
    return null;
  }
}

export default async function ResultsPage({ params }: { params: { allocationId: string } }) {
  const result = await getAllocation(params.allocationId);

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Results not found or not yet published.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-primary">SquadSync</h1>
          <p className="text-muted-foreground text-sm mt-1">Team Allocation Results</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {result.teams.map(team => (
            <Card key={team.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
                  {team.fairness_score && (
                    <span className="flex items-center gap-1 text-xs text-amber-600 font-medium">
                      <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
                      {team.fairness_score.toFixed(0)}%
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {team.members.map(m => (
                    <li key={m.id} className="flex justify-between text-sm">
                      <span className="font-medium">{m.name}</span>
                      <span className="text-muted-foreground capitalize text-xs">{m.role}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
